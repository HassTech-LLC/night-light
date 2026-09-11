"""Single-thread native adapter for the explicit Smart Comfort owner.

Construction does not enable output or migrate legacy preferences. The app must
select this owner only after its versioned setup/migration has been committed.
Automatic output is proposed immutably and committed only after native acceptance.
No IP lookup, inference, telemetry, file I/O, or GUI timers live in this adapter.
"""
from datetime import datetime, timedelta
from dataclasses import replace

from smart_state import Appearance, ControlState, Event, Override, SmartSettings, commit_saved, reduce, resolve
from smart_time import ClockSource, restored_pause_remaining
from smart_transition import ChannelTransition, TrackingPair, automatic_rgb, kelvin_to_warmth, warmth_to_kelvin


class NativeSmartRuntime:
    def __init__(self, engine, settings, clock_source=None):
        if not isinstance(settings, SmartSettings):
            raise ValueError('Validated Smart settings required.')
        self.engine = engine
        self.clock = clock_source or ClockSource()
        self._state_observers = []
        self.state = ControlState(settings=settings)
        self.tracker = None
        self.last_sample = None
        self.status = 'Off'
        self._engine_generation = None
        self._plan_key = None
        self._plans = ()
        self._pace_brakes = None
        self._pace_elapsed = 0.
        self._reference_changed = False
        self.engine.set_color_policy('smart-v2')

    @classmethod
    def from_config(cls,engine,config,clock_source=None):
        """Restore explicit v2 intent after the resident opens recovery storage.

        Establish neutral/ownership again; saved output is never used as proof
        of current display state. Invalid data stays Off without overwriting it.
        """
        from smart_migration import uses_v2
        if not uses_v2(config):raise ValueError('Explicit v2 setup or migration is required.')
        try:
            settings=SmartSettings.from_dict(config.get('smart_settings_v2'))
            valid_policy=config.get('policy_version')==settings.policy_version
        except (ValueError,TypeError):
            settings=SmartSettings(kind='personal');valid_policy=False
        owner=cls(engine,settings,clock_source)
        engine.reset_to_neutral()
        if config.automatic_output_blocked or not config.session_id:
            config.automatic_output_blocked=True
            config.owner_commit_pending=True
            owner.status='Recovery storage must be initialized before restoring the saved mode'
            return owner
        try:
            if not valid_policy:raise ValueError('Unsupported saved policy.')
            sample=owner.clock.sample()
            owner._availability(sample.elapsed_seconds)
            intent=config.get('intent_v2')
            if not isinstance(intent,dict) or set(intent)-{'mode','manual'}:
                raise ValueError('Invalid saved intent.')
            raw_manual=intent.get('manual')
            if not isinstance(raw_manual,dict):raise ValueError('Missing saved Manual appearance.')
            manual=Appearance(**raw_manual)
            override=owner._restore_override(config.get('override_v2'),sample)
            mode=intent.get('mode')
            owner.state=replace(owner.state,mode=mode,manual=manual,override=override,
                                config_revision=config.get('config_revision',0),
                                manual_resume_required=mode=='manual' and (
                                    owner.state.availability!='available' or owner.state.fault_latched))
            owner.last_sample=sample
            if mode!='off':owner._apply_intent(sample,explicit=True)
            else:owner.status='Off' if engine.is_applied else 'Off requested; display reset unconfirmed'
        except (ValueError,TypeError,OSError,OverflowError,RuntimeError):
            # Parsing happens before any non-neutral intent is applied.
            owner.state=replace(owner.state,mode='off',override=None,preview=None)
            owner._forget_motion()
            owner.status='Saved settings need repair; automatic adjustment remains off'
            config.owner_commit_pending=True
        return owner

    @staticmethod
    def _restore_override(raw,sample):
        if raw is None:return None
        allowed={'kind','original_duration','start_utc','expiry_utc','last_seen_utc','appearance'}
        if not isinstance(raw,dict) or set(raw)!=allowed:
            raise ValueError('Invalid saved override fields.')
        if type(raw['original_duration']) not in (int,float) or raw['original_duration']!=3600:
            raise ValueError('Invalid override duration.')
        stamps=[]
        for name in ('start_utc','expiry_utc','last_seen_utc'):
            value=raw[name]
            if not isinstance(value,str) or len(value)>64:raise ValueError('Invalid override time.')
            parsed=datetime.fromisoformat(value)
            if parsed.utcoffset() is None:raise ValueError('Override time requires a timezone.')
            stamps.append(parsed.timestamp())
        start,expiry,last_seen=stamps
        if expiry-start>3600.001:raise ValueError('Override duration was extended.')
        kind=raw['kind'];appearance=raw['appearance']
        if kind=='manual_hold':
            if not isinstance(appearance,dict):raise ValueError('Missing temporary appearance.')
            appearance=Appearance(**appearance)
        elif kind!='neutral_pause' or appearance is not None:
            raise ValueError('Invalid override kind.')
        remaining=restored_pause_remaining(start=start,expiry=expiry,last_seen=last_seen,
                                            now=sample.utc.timestamp(),duration=3600.)
        return Override(kind,sample.elapsed_seconds+remaining,appearance) if remaining else None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self,value):
        if not isinstance(value,ControlState):
            raise ValueError('Validated owner state required.')
        previous=getattr(self,'_state',None)
        self._state=value
        if previous is not None and (previous.owner_id,previous.generation,previous.config_revision)!=(value.owner_id,value.generation,value.config_revision):
            for observer in tuple(self._state_observers):observer()

    def observe_invalidation(self,callback):
        """Owner-thread subscription; callback must be immediate/nonblocking."""
        self._state_observers.append(callback)
        return lambda:self._state_observers.remove(callback)

    def _availability(self, elapsed):
        self.engine.refresh_output_observation()
        if self.engine.output_fault:
            value = self.engine.output_fault
        elif self.engine.is_suppressed_by_windows_nightlight:
            value = 'windows_on'
        elif not self.engine.backend_available:
            value = 'unsupported'
        else:
            value = 'available'
        self.state = reduce(self.state, Event('availability', elapsed, availability=value))

    def _forget_motion(self):
        self.tracker = None
        self._engine_generation = None
        self._pace_brakes = None
        self._pace_elapsed = 0.
        self._reference_changed = False

    def accept_saved(self, ticket, revision):
        """Commit already-durable preferences; preserve moving output continuity."""
        ending_preview=self.state.preview is not None
        self.state = commit_saved(self.state,ticket,revision)
        self._plan_key = None
        if ending_preview:
            self._forget_motion()
            try:
                sample=self.clock.sample()
                self._availability(sample.elapsed_seconds)
                self.last_sample=sample
            except (ValueError,OSError,RuntimeError):sample=None
            self._restore_preview(sample)
            return
        self._reference_changed = True
        if self.tracker is not None:
            self._engine_generation = self.engine.begin_automatic()
            if self.tracker.slower != self.state.settings.slower:
                # Existing motion cannot instantly satisfy a newly lower rate.
                # Brake under its previous bounds, then adopt the new policy at
                # zero velocity. Do not reset velocity or change the endpoint.
                brakes=[]
                for _,channel in self.tracker.channels():
                    stop=channel.position+.5*channel.velocity*abs(channel.velocity)/channel.policy.acceleration
                    brakes.append(ChannelTransition(channel.position,max(0.,min(1.,stop)),
                                                     channel.policy,velocity=channel.velocity))
                self._pace_brakes=tuple(brakes)
                self._pace_elapsed=0.
            else:
                self._pace_brakes=None
                self._pace_elapsed=0.
                # A changed reference may require catch-up again; rejoin keeps
                # accepted position and velocity instead of restarting a fade.
                self.tracker=replace(self.tracker,matched_seconds=0.)
        self.tick()

    def _propose(self, reference, dt):
        if self._pace_brakes is None:
            tracker=self.tracker.rejoin(reference(0)) if self._reference_changed else self.tracker
            return tracker.advance(reference,dt),False
        elapsed=self._pace_elapsed+dt
        samples=tuple(brake.sample(elapsed) for brake in self._pace_brakes)
        complete=elapsed>=max(brake.duration for brake in self._pace_brakes)
        if complete:
            return TrackingPair.start(*(s.position for s in samples),slower=self.state.settings.slower),True
        channels=[replace(channel,position=s.position,velocity=s.velocity,acceleration=s.acceleration)
                  for (_,channel),s in zip(self.tracker.channels(),samples)]
        return TrackingPair(*channels,self.tracker.catching_up,0.,self.tracker.slower),False

    def command(self, kind, appearance=None, *, token=None):
        # Off remains usable when civil/elapsed clock adapters are unavailable.
        if kind == 'off':
            elapsed = self.last_sample.elapsed_seconds if self.last_sample else 0.
            self.state = reduce(self.state, Event('off', elapsed))
            self._forget_motion()
            accepted = self.engine.reset_to_neutral()
            self.status = 'Off' if accepted else 'Off requested; display reset unconfirmed'
            return accepted
        if kind=='end_preview':
            try:sample=self.clock.sample()
            except (ValueError,OSError,RuntimeError):sample=None
            try:elapsed=sample.elapsed_seconds if sample else self.clock.elapsed_now()
            except (ValueError,OSError,RuntimeError):elapsed=self.last_sample.elapsed_seconds if self.last_sample else 0.
            previous=self.state
            self.state=reduce(self.state,Event('end_preview',elapsed,token=token))
            if self.state==previous:return True
            self._availability(elapsed)
            self._forget_motion()
            if sample is not None:self.last_sample=sample
            self._restore_preview(sample)
            return True
        sample = self.clock.sample()
        self._availability(sample.elapsed_seconds)
        if kind == 'retry':
            if not self.engine.retry_display():
                self._availability(sample.elapsed_seconds)
                return False
            self._availability(sample.elapsed_seconds)
        previous = self.state
        self.state = reduce(self.state, Event(kind, sample.elapsed_seconds, appearance, token))
        if self.state == previous:
            return True
        self._forget_motion()
        self.last_sample = sample
        if previous.preview is not None and self.state.preview is None:
            self._restore_preview(sample)
            return True
        self._apply_intent(sample, explicit=True)
        return True

    def _reference(self, sample):
        day = sample.utc.astimezone(sample.zone).date()
        key = (day, sample.zone, self.state.settings)
        if key != self._plan_key:
            plans = tuple(self.state.settings.plan(day + timedelta(days=offset), sample.zone)
                          for offset in (-1, 0, 1))
            self._plans, self._plan_key = plans, key
        plans = self._plans

        def reference(offset):
            instant = sample.utc + timedelta(seconds=offset)
            active = [plan for plan in plans
                      if min(plan.warmth.start, plan.dim.start) <= instant < plan.neutral]
            plan = max(active, key=lambda p: p.ready) if active else min(
                plans, key=lambda p: abs((p.ready - instant).total_seconds()))
            return plan.warmth.sample(instant), plan.dim.sample(instant)
        return reference

    def scheduled_plan(self,sample):
        """Current or upcoming dated plan, sharing the output reference cache."""
        self._reference(sample)
        active=[plan for plan in self._plans if min(plan.warmth.start,plan.dim.start)<=sample.utc<plan.neutral]
        if active:return max(active,key=lambda plan:plan.ready)
        upcoming=[plan for plan in self._plans if plan.neutral>sample.utc]
        if not upcoming:raise ValueError('No upcoming schedule is available.')
        return min(upcoming,key=lambda plan:plan.ready)

    def _known_start(self):
        observation = self.engine.output_observation()
        rgb = observation['accepted_rgb']
        if not observation['current_confirmed'] or rgb is None:
            return None
        if tuple(rgb) == (1., 1., 1.):
            return 0., 0.
        k, brightness = self.engine.temperature_k, self.engine.brightness
        try:
            expected = automatic_rgb(k, brightness)
        except ValueError:
            # Legacy endpoints outside v2 bounds are not a valid v2 starting
            # coordinate. Preserve uncertainty; do not turn a saved result into
            # a UI exception or silently clamp the user's visible appearance.
            return None
        # Recognize only our own exact accepted endpoint, not an inverse of an
        # arbitrary matrix or a requested target while an animation is running.
        if all(abs(a-b) <= 1e-12 for a, b in zip(rgb, expected)):
            return kelvin_to_warmth(k), (1-brightness)/.8
        return None

    def _apply_intent(self, sample, *, explicit=False, dt=0.):
        intent = resolve(self.state)
        self.status = intent.reason
        if intent.kind == 'none':
            return
        if intent.kind != 'smart':
            if explicit:
                if intent.kind == 'neutral':
                    self.engine.reset_to_neutral()
                else:
                    self.engine.set_state(enabled=True, temperature_k=intent.appearance.warmth_kelvin,
                                          brightness=.2+.8*(1-intent.appearance.dim_fraction/.8), smooth=True)
            return
        try:
            reference = self._reference(sample)
        except (ValueError, OSError) as error:
            self.status = 'Schedule unavailable: ' + str(error)
            self._forget_motion()
            return
        if self.tracker is None:
            start = self._known_start()
            if start is None:
                self.status = 'Waiting for a confirmed starting appearance'
                return
            self.tracker = TrackingPair.start(*start, slower=self.state.settings.slower)
            self._engine_generation = self.engine.begin_automatic()
            return
        if dt <= 0:
            return
        generation = self.state.generation
        try:
            proposed,pace_done = self._propose(lambda offset: reference(offset-dt), dt)
        except ValueError as error:
            self.status = 'Automatic adjustment held: ' + str(error)
            return
        k = warmth_to_kelvin(proposed.warmth.position)
        brightness = .2 + .8*(1-proposed.dim.position)
        accepted = self.engine.apply_automatic_sample(k, brightness, dt, self._engine_generation)
        if generation != self.state.generation:
            return
        if self._engine_generation != self.engine.automatic_generation:
            # A native cancellation can occur without a reducer event. Keep the
            # last committed tracker on failure; rebase only after explicit recovery.
            self.status = 'Display sample invalidated'
            return
        if accepted:
            actual = self.engine.output_observation()['accepted_rgb']
            if actual is not None and all(abs(a-b) <= 1e-12 for a,b in zip(actual, automatic_rgb(k, brightness))):
                self.tracker = proposed
                self._reference_changed = False
                if self._pace_brakes is not None:
                    self._pace_elapsed += dt
                    if pace_done:self._pace_brakes=None
            else:
                self.status = 'Waiting for accepted output alignment'
        else:
            self.status = 'Display sample not accepted'

    def _restore_preview(self,sample):
        """Restore latest effective intent, never a pre-preview captured state."""
        intent=resolve(self.state)
        if intent.kind=='none':return
        if intent.kind=='neutral':
            self.engine.reset_to_neutral()
            return
        appearance=intent.appearance
        if intent.kind=='smart':
            if sample is None:
                self.engine.reset_to_neutral()
                self.status='Preview ended; schedule clock unavailable, holding original colors'
                return
            try:
                warmth,dim=self._reference(sample)(0)
                appearance=Appearance(warmth_to_kelvin(warmth.position),.8*dim.position)
            except (ValueError,OSError):
                self.engine.reset_to_neutral()
                self.status='Preview ended; schedule unavailable, holding original colors'
                return
        self.engine.set_state(enabled=True,temperature_k=appearance.warmth_kelvin,
                              brightness=.2+.8*(1-appearance.dim_fraction/.8),smooth=True,duration=.5)

    def _clockless_watchdog(self):
        previous=self.state
        try:
            elapsed=self.clock.elapsed_now()
            self._availability(elapsed)
            self.state=reduce(self.state,Event('tick',elapsed))
        except (ValueError,OSError,RuntimeError):
            # Losing even the deadline counter ends previews conservatively.
            if self.state.preview is not None:
                elapsed=self.last_sample.elapsed_seconds if self.last_sample else 0.
                self.state=reduce(self.state,Event('end_preview',elapsed,token=self.state.preview.token))
        if previous.preview is not None and self.state.preview is None:
            self._forget_motion()
            self._restore_preview(None)
        elif previous.override is not None and self.state.override is None:
            self._forget_motion()
            self.engine.reset_to_neutral()

    def tick(self):
        try:
            sample = self.clock.sample()
        except (ValueError, OSError, RuntimeError):
            self.status = 'Clock unavailable; automatic adjustment held'
            self._clockless_watchdog()
            return
        previous = self.state
        self._availability(sample.elapsed_seconds)
        self.state = reduce(self.state, Event('tick', sample.elapsed_seconds))
        changed = previous.generation != self.state.generation
        old, self.last_sample = self.last_sample, sample
        dt = 0. if old is None else sample.active_seconds-old.active_seconds
        discontinuity = old is not None and (
            dt < 0 or dt >= 2 or sample.zone != old.zone
            or abs((sample.elapsed_seconds-old.elapsed_seconds)-dt) >= 2
            or abs((sample.utc-old.utc).total_seconds()-(sample.elapsed_seconds-old.elapsed_seconds)) >= 2)
        if changed or discontinuity:
            self._forget_motion()
            dt = 0.
        if previous.preview is not None and self.state.preview is None:
            self._restore_preview(sample)
            return
        self._apply_intent(sample, explicit=changed, dt=dt)
