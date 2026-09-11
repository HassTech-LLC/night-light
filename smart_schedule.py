"""Dated offline schedules: saved coordinates and explicit OS timezone only.

Never use IP address, VPN endpoint, browser locale or network geolocation.
"""
from dataclasses import dataclass
from datetime import timedelta, timezone
from smart_time import resolve_civil
from smart_transition import ChannelTransition, LimitPolicy, MotionSample, bounded, kelvin_to_warmth, warmth_to_kelvin

UTC=timezone.utc


class ScheduleUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class ChannelSchedule:
    start: object
    ready: object
    return_start: object
    neutral: object
    peak: float
    preferred_peak: float
    policy: LimitPolicy
    evening: ChannelTransition
    morning: ChannelTransition

    def sample(self,now):
        if now.tzinfo is None:raise ValueError('An aware time is required.')
        now=now.astimezone(UTC)
        if now<self.start or now>=self.neutral:return MotionSample(0.,0.,0.)
        if now<self.ready:return self.evening.sample((now-self.start).total_seconds())
        if now<self.return_start:return MotionSample(self.peak,0.,0.)
        return self.morning.sample((now-self.return_start).total_seconds())


@dataclass(frozen=True)
class ScheduledAppearance:
    kelvin: float
    brightness: float


@dataclass(frozen=True)
class NightPlan:
    ready: object
    neutral: object
    warmth: ChannelSchedule
    dim: ChannelSchedule
    source: str
    time_resolution: tuple
    occurrence_id: str

    @property
    def reduced_peak(self):
        return any(c.peak<c.preferred_peak-1e-8 for c in (self.warmth,self.dim))

    def sample(self,now):
        return ScheduledAppearance(warmth_to_kelvin(self.warmth.sample(now).position),
                                   .2+.8*(1-self.dim.sample(now).position))


def _channel(peak,previous,ready,neutral,lead,policy):
    up=max(0.,(ready-previous).total_seconds())
    down=max(0.,(neutral-ready).total_seconds())
    def ramps(scale):
        level=peak*scale
        return (ChannelTransition(0,level,policy,preferred_seconds=min(lead,up)),
                ChannelTransition(level,0,policy,preferred_seconds=min(2700,down)))
    def feasible(scale):
        a,b=ramps(scale)
        return a.duration<=up and b.duration<=down
    scale=1.
    if not feasible(scale):
        low,high=0.,1.
        for _ in range(32):
            mid=(low+high)/2
            if feasible(mid):low=mid
            else:high=mid
            if high-low<=1e-4:break
        scale=low
    evening,morning=ramps(scale)
    return ChannelSchedule(ready-timedelta(seconds=evening.duration),ready,
                           neutral-timedelta(seconds=morning.duration),neutral,
                           peak*scale,peak,policy,evening,morning)


def _plan(previous,ready,neutral,*,kelvin,dim_fraction,warmth_lead,dim_lead,slower,source,resolution,identity):
    warmth=kelvin_to_warmth(kelvin)
    dim=bounded(dim_fraction,0,.8)/.8
    lead_w=bounded(warmth_lead,60,240)*60
    lead_d=bounded(dim_lead,15,120)*60
    if not previous<neutral:raise ScheduleUnavailable('No valid morning interval.')
    ready=max(previous,min(neutral,ready))
    w=_channel(warmth,previous,ready,neutral,lead_w,LimitPolicy.channel('warmth',slower=slower))
    d=_channel(dim,previous,ready,neutral,lead_d,LimitPolicy.channel('dim',slower=slower))
    return NightPlan(ready,neutral,w,d,source,tuple(resolution),identity)


def personal_plan(day,zone,ready_time,neutral_time,*,kelvin=4000,dim_fraction=0,
                  warmth_lead=180,dim_lead=60,slower=1.,source='personal'):
    ready=resolve_civil(day,ready_time,zone)
    # Validation occurs before lexicographic comparison of strict HH:MM values.
    resolve_civil(day,neutral_time,zone)
    if ready_time==neutral_time:raise ValueError('Evening and morning times must differ.')
    end_day=day+timedelta(days=1) if neutral_time<ready_time else day
    neutral=resolve_civil(end_day,neutral_time,zone)
    previous=resolve_civil(end_day-timedelta(days=1),neutral_time,zone)
    return _plan(previous.utc,ready.utc,neutral.utc,kelvin=kelvin,dim_fraction=dim_fraction,
                 warmth_lead=warmth_lead,dim_lead=dim_lead,slower=slower,source=source,
                 resolution=(ready.resolution,neutral.resolution),identity=ready.occurrence_id+'|'+neutral.occurrence_id)


def solar_plan(day,zone,latitude,longitude,*,offset_minutes=60,fallback=None,**comfort):
    # Lazy import preserves the existing independently tested NOAA calculator
    # without a module-initialization cycle when SmartController adopts this.
    from smart_mode import solar_event
    lat=bounded(latitude,-90,90);lon=bounded(longitude,-180,180)
    offset=bounded(offset_minutes,-120,180)
    sunsets=[];sunrises=[]
    for delta in range(-3,4):
        event_day=day+timedelta(days=delta)
        setting=solar_event(event_day,lat,lon,False)
        rising=solar_event(event_day,lat,lon,True)
        if setting is not None and setting.astimezone(zone).date()==day:sunsets.append(setting)
        if rising is not None:sunrises.append(rising)
    sunset=min(sunsets) if sunsets else None
    before=[r for r in sunrises if sunset is not None and r<sunset]
    after=[r for r in sunrises if sunset is not None and r>sunset]
    if sunset is None or not before or not after:
        if fallback is not None:
            if not isinstance(fallback,(tuple,list)) or len(fallback)!=2:raise ValueError('Invalid fallback times.')
            return personal_plan(day,zone,*fallback,source='explicit-fallback',**comfort)
        raise ScheduleUnavailable('Solar events unavailable. Choose personal timing or explicit fallback times.')
    values={'kelvin':4000,'dim_fraction':0,'warmth_lead':180,'dim_lead':60,'slower':1.,**comfort}
    return _plan(max(before),sunset+timedelta(minutes=offset),min(after),source='solar',
                 resolution=('solar-approximation',),identity=f'{zone}|{day}|{lat}|{lon}|{offset}',**values)
