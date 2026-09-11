"""Pure, versioned Smart Comfort motion primitives; no display side effects.

Limits are engineering candidates, not proven perceptual or medical thresholds.
Scheduled segments are sampled continuously; replanning is an intent event,
not something that restarts at every output tick.
"""
from dataclasses import dataclass, replace
import math

POLICY_VERSION='smart-comfort-2-candidate-1'
RGB_STEP_PER_SECOND=10/1024
REBASE_GAP_SECONDS=2.0


def bounded(value,low,high):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'Expected a finite number between {low} and {high}.')
    return float(value)


def kelvin_to_warmth(kelvin):
    k=bounded(kelvin,1200,6500)
    return (1/k-1/6500)/(1/1200-1/6500)


def warmth_to_kelvin(warmth):
    w=bounded(warmth,0,1)
    return 1/(1/6500+w*(1/1200-1/6500))


def automatic_rgb(kelvin,brightness):
    """Continuous v2 software factors, not calibrated display temperature.

    Normalize each logarithmic color approximation at 6500 instead of
    special-casing neutral: the legacy approximation otherwise jumps there.
    Clamping the blue floor is continuous. For warmth coordinate w in [0,1],
    each factor is 3-Lipschitz: green's maximum derivative is <1.74 and
    blue's <2.90 (at 6500 K); red is constant. Brightness=1-.8*d therefore
    gives |RGB'| <= 3*|w'| + .8*|d'|, below the final limiter for both policies.
    This is a numerical continuity guarantee, not a perceptual claim.
    """
    k=bounded(kelvin,1200,6500)
    br=bounded(brightness,.2,1)
    green=(99.4708025861*math.log(k/100)-161.1195681661)
    green/=99.4708025861*math.log(65)-161.1195681661
    blue=(138.5177312231*math.log(k/100-10)-305.0447927307)
    blue/=138.5177312231*math.log(55)-305.0447927307
    return (br,br*max(0.,min(1.,green)),br*max(0.,min(1.,blue)))


@dataclass(frozen=True)
class LimitPolicy:
    rate: float
    acceleration: float

    def __post_init__(self):
        bounded(self.rate,1e-12,1)
        bounded(self.acceleration,1e-12,1)

    @classmethod
    def channel(cls,channel,*,catch_up=False,slower=1.0):
        if channel not in ('warmth','dim') or isinstance(slower,bool) or slower not in (.5,1.):
            raise ValueError('Invalid transition policy.')
        seconds={'warmth':1200 if catch_up else 7200,'dim':1800 if catch_up else 10800}[channel]
        rate=slower/seconds
        return cls(rate,rate/30)


@dataclass(frozen=True)
class MotionSample:
    position: float
    velocity: float
    acceleration: float


class ChannelTransition:
    """Brake to a feasible splice, then follow an endpoint-flat quintic curve.

    A changed target preserves instantaneous position/velocity. Deceleration
    has the same hard bound as acceleration, including a direction reversal.
    Duration includes braking; a missed schedule deadline never causes a jump.
    """
    def __init__(self,start,target,policy,*,velocity=0.,preferred_seconds=0.):
        self.start=bounded(start,0,1)
        self.target=bounded(target,0,1)
        self.policy=policy
        self.velocity=bounded(velocity,-policy.rate,policy.rate)
        preferred=bounded(preferred_seconds,0,86400)
        self.braking_seconds=abs(self.velocity)/policy.acceleration
        self.braking_acceleration=-math.copysign(policy.acceleration,self.velocity) if self.velocity else 0.
        self.splice=self.start+.5*self.velocity*self.braking_seconds
        if not -1e-12<=self.splice<=1+1e-12:
            raise ValueError('Initial velocity has no feasible braking path within bounds.')
        self.splice=max(0.,min(1.,self.splice))
        self.distance=self.target-self.splice
        distance=abs(self.distance)
        self.curve_seconds=max(preferred,1.875*distance/policy.rate,
                               math.sqrt((10/math.sqrt(3))*distance/policy.acceleration)) if distance else 0.
        self.duration=self.braking_seconds+self.curve_seconds

    def sample(self,elapsed):
        t=bounded(elapsed,0,1e15)
        if t<self.braking_seconds:
            return MotionSample(self.start+self.velocity*t+.5*self.braking_acceleration*t*t,
                                self.velocity+self.braking_acceleration*t,self.braking_acceleration)
        if not self.curve_seconds or t>=self.duration:
            return MotionSample(self.target,0.,0.)
        u=(t-self.braking_seconds)/self.curve_seconds
        # Polynomial roundoff near u=1 must not produce an out-of-range
        # normalized value which the strict display validator would reject.
        position=max(0.,min(1.,u*u*u*(10+u*(-15+6*u))))
        velocity=30*u*u*(1-u)*(1-u)
        acceleration=60*u*(1-u)*(1-2*u)
        return MotionSample(self.splice+self.distance*position,
                            self.distance*velocity/self.curve_seconds,
                            self.distance*acceleration/self.curve_seconds**2)


def limit_rgb(previous,requested,active_dt):
    if len(previous)!=3 or len(requested)!=3:
        raise ValueError('Expected three RGB factors.')
    old=tuple(bounded(v,0,1) for v in previous)
    desired=tuple(bounded(v,0,1) for v in requested)
    dt=bounded(active_dt,0,1e15)
    if dt>=REBASE_GAP_SECONDS or dt==0:
        return old
    maximum=RGB_STEP_PER_SECOND*dt
    return tuple(a+max(-maximum,min(maximum,b-a)) for a,b in zip(old,desired))


@dataclass(frozen=True)
class ChannelTracker:
    """Immutable moving-reference proposal with bounded acceleration.

    Reference(t) supplies the schedule at t seconds after the accepted frame.
    A damped feedback law follows that path, not a saved nightly endpoint.
    The owner may accept this proposal only after a successful display write.
    Changing the reference does not reset position or velocity.
    """
    position: float
    velocity: float
    policy: LimitPolicy
    acceleration: float=0.

    def __post_init__(self):
        bounded(self.position,0,1)
        bounded(self.velocity,-self.policy.rate,self.policy.rate)
        bounded(self.acceleration,-self.policy.acceleration,self.policy.acceleration)
        if not self.viable():raise ValueError('No bounded braking path from the proposed state.')

    def viable(self):
        distance=self.velocity*self.velocity/(2*self.policy.acceleration)
        return (self.position-distance>=-1e-12 if self.velocity<0 else self.position+distance<=1+1e-12)

    def advance(self,reference,active_dt):
        dt=bounded(active_dt,0,1e15)
        if not dt:return self
        if dt>=REBASE_GAP_SECONDS:
            # A discontinuity starts a new interpolation epoch at held output,
            # with zero velocity; it is not an ordinary bounded-motion step.
            return ChannelTracker(self.position,0.,self.policy)
        count=max(1,math.ceil(dt/.1))
        step=dt/count
        current=self
        for index in range(count):
            target=reference(index*step)
            if not isinstance(target,MotionSample):raise ValueError('Expected a scheduled motion sample.')
            bounded(target.position,0,1);bounded(target.velocity,-1,1);bounded(target.acceleration,-1,1)
            current=current._step(target,step)
        return current

    def _step(self,target,dt):
        x,v=self.position,self.velocity
        r,a=self.policy.rate,self.policy.acceleration
        # A critically damped 30-second error response; saturation supplies
        # the actual engineering ceilings. This gain is a tuning candidate.
        omega=1/30
        wanted=target.acceleration+2*omega*(target.velocity-v)+omega*omega*(target.position-x)
        low=max(-a,(-r-v)/dt)
        high=min(a,(r-v)/dt)

        def envelope(acceleration):
            end_v=v+acceleration*dt
            end_x=x+v*dt+.5*acceleration*dt*dt
            lower=end_x-min(end_v,0.)**2/(2*a)
            upper=end_x+max(end_v,0.)**2/(2*a)
            # An interior direction reversal can be farther out than the
            # final position. Certify that point as well as future braking.
            if acceleration:
                turn=-v/acceleration
                if 0<turn<dt:
                    extreme=x+v*turn+.5*acceleration*turn*turn
                    lower=min(lower,extreme);upper=max(upper,extreme)
            return lower,upper

        def integrate(chosen):
            position=x+v*dt+.5*chosen*dt*dt
            velocity=v+chosen*dt
            return ChannelTracker(max(0.,min(1.,position)),max(-r,min(r,velocity)),self.policy,chosen)

        candidate=max(low,min(high,wanted))
        minimum,maximum=envelope(candidate)
        if minimum>=0 and maximum<=1:return integrate(candidate)

        # Both position envelopes are monotone in acceleration. Their safe
        # intersection is an interval; projection changes acceleration only,
        # never clips an infeasible position or resets velocity. The epsilon
        # is float64 roundoff, not additional allowed comfort motion.
        epsilon=1e-12
        if envelope(low)[0]<0:
            left,right=low,high
            if envelope(right)[0]<0:
                if envelope(right)[0]<-epsilon:raise ValueError('No lower-bound braking solution.')
                # At an exactly saturated boundary, float64 cancellation can
                # put the full-braking solution a few ulps outside. Select
                # full braking, never spend tolerance on weaker braking.
            else:
                for _ in range(48):
                    mid=(left+right)/2
                    if envelope(mid)[0]>=0:right=mid
                    else:left=mid
            low=right
        if envelope(high)[1]>1:
            left,right=low,high
            if envelope(left)[1]>1:
                if envelope(left)[1]>1+epsilon:raise ValueError('No upper-bound braking solution.')
            else:
                for _ in range(48):
                    mid=(left+right)/2
                    if envelope(mid)[1]<=1:left=mid
                    else:right=mid
            high=left
        chosen=max(low,min(high,wanted))
        return integrate(chosen)


MATCH_ERROR=1/1024
MATCH_SECONDS=2.


@dataclass(frozen=True)
class TrackingPair:
    """Coupled phase/handoff; independent channel endpoints and limits."""
    warmth: ChannelTracker
    dim: ChannelTracker
    catching_up: bool=True
    matched_seconds: float=0.
    slower: float=1.

    def __post_init__(self):
        if type(self.catching_up) is not bool:raise ValueError('Invalid tracking phase.')
        bounded(self.matched_seconds,0,MATCH_SECONDS)
        for name,tracker in self.channels():
            if tracker.policy!=LimitPolicy.channel(name,catch_up=self.catching_up,slower=self.slower):
                raise ValueError('Channel policy does not match tracking phase.')

    def channels(self):return (('warmth',self.warmth),('dim',self.dim))

    @classmethod
    def start(cls,warmth,dim,*,catching_up=True,slower=1.):
        return cls(ChannelTracker(warmth,0.,LimitPolicy.channel('warmth',catch_up=catching_up,slower=slower)),
                   ChannelTracker(dim,0.,LimitPolicy.channel('dim',catch_up=catching_up,slower=slower)),
                   catching_up,0.,slower)

    def _reference(self,value):
        if not isinstance(value,(tuple,list)) or len(value)!=2:raise ValueError('Expected two scheduled channels.')
        for (name,_),sample in zip(self.channels(),value):
            if not isinstance(sample,MotionSample):raise ValueError('Expected scheduled motion samples.')
            normal=LimitPolicy.channel(name,slower=self.slower)
            bounded(sample.position,0,1)
            bounded(sample.velocity,-normal.rate*(1+1e-9),normal.rate*(1+1e-9))
            bounded(sample.acceleration,-normal.acceleration*(1+1e-9),normal.acceleration*(1+1e-9))
        return tuple(value)

    def rejoin(self,reference):
        targets=self._reference(reference)
        catch=self.catching_up or any(abs(channel.position-target.position)>MATCH_ERROR
                                     for (_,channel),target in zip(self.channels(),targets))
        return TrackingPair(*(replace(channel,policy=LimitPolicy.channel(name,catch_up=catch,slower=self.slower))
                              for name,channel in self.channels()),catch,0.,self.slower)

    def advance(self,reference,active_dt):
        dt=bounded(active_dt,0,1e15)
        if not dt:return self
        if dt>=REBASE_GAP_SECONDS:
            targets=self._reference(reference(dt))
            catch=self.catching_up or any(abs(c.position-t.position)>MATCH_ERROR
                                         for (_,c),t in zip(self.channels(),targets))
            return TrackingPair.start(self.warmth.position,self.dim.position,catching_up=catch,slower=self.slower)
        count=max(1,math.ceil(dt/.1));step=dt/count
        current=self
        for index in range(count):
            before=current._reference(reference(index*step))
            after=current._reference(reference((index+1)*step))
            trackers=[channel.advance(lambda t,sample=target:sample,step)
                      for (_,channel),target in zip(current.channels(),before)]
            matched=True;normal_trackers=[]
            for (name,old),new,start,end in zip(current.channels(),trackers,before,after):
                normal=LimitPolicy.channel(name,slower=self.slower)
                # A Lipschitz margin certifies the interval between checked
                # endpoints, given the planner's normal-rate reference bound.
                error=max(abs(old.position-start.position),abs(new.position-end.position))
                margin=(max(abs(old.velocity),abs(new.velocity))+normal.rate)*step/2
                if error+margin>MATCH_ERROR:matched=False
                try:
                    replace(old,policy=normal)
                    normal_trackers.append(replace(new,policy=normal))
                except ValueError:matched=False
            seconds=min(MATCH_SECONDS,current.matched_seconds+step) if matched else 0.
            if current.catching_up and seconds>=MATCH_SECONDS-1e-12:
                current=TrackingPair(*normal_trackers,False,0.,self.slower)
            else:
                current=TrackingPair(*trackers,current.catching_up,seconds if current.catching_up else 0.,self.slower)
        return current


@dataclass(frozen=True)
class HandoffForecast:
    seconds: float | None
    reason: str
    simulated_seconds: float


def forecast_handoff(tracker,reference,*,horizon=7200.,cancelled=lambda:False):
    """Predict catch-up completion using the same tracker, not distance/rate.

    This is not a forecast of physical output or the final morning-neutral
    endpoint. Run away from the UI thread; discard if intent/clock/availability
    changes. The one-second reporting granularity should be shown as minutes.
    """
    horizon=bounded(horizon,0,7200)
    if cancelled():return HandoffForecast(None,'cancelled',0.)
    if not tracker.catching_up:return HandoffForecast(0.,'already_following',0.)
    elapsed=0.;current=tracker
    try:
        while elapsed<horizon:
            if cancelled():return HandoffForecast(None,'cancelled',elapsed)
            dt=min(1.,horizon-elapsed)
            current=current.advance(lambda offset:reference(elapsed+offset),dt)
            elapsed+=dt
            if not current.catching_up:return HandoffForecast(elapsed,'estimated',elapsed)
    except ValueError:
        return HandoffForecast(None,'reference_unavailable',elapsed)
    return HandoffForecast(None,'beyond_horizon',elapsed)
