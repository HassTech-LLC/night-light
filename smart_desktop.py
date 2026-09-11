"""Desktop routing for explicitly opted-in Smart Comfort installations."""
import secrets
from smart_runtime import NativeSmartRuntime
from smart_store import AsyncSmartStore
from smart_state import Appearance, SmartSettings


class SmartDesktopController:
    is_v2=True

    def __init__(self,engine,config,clock_source=None):
        self.owner=NativeSmartRuntime.from_config(engine,config,clock_source)
        self.store=AsyncSmartStore(self.owner,config)
        self.session_id=secrets.token_hex(16)
        self.last_result=None
        self.last_save_result=None
        self.hotkey_status=''

    @property
    def enabled(self):return self.owner.state.mode=='smart'

    @property
    def status(self):return self.owner.status

    @status.setter
    def status(self,value):self.owner.status=value

    def command(self,kind,appearance=None,request_id=None):
        request_id=request_id or secrets.token_hex(16)
        if kind=='off':result=self.store.submit_off(self.session_id,request_id)
        else:result=self.store.submit_command(kind,self.session_id,request_id,appearance)
        self.last_result=result
        return result

    def manual(self,reset=False):
        return self.command('off' if reset else 'manual',None if reset else self.owner.state.manual)

    def hold(self,pause=False):
        return self.command('pause') if pause else None

    def resume(self):return self.command('resume' if self.enabled else 'smart')

    def toggle(self):
        return self.command('off') if self.owner.state.mode!='off' or self.owner.state.preview else self.command('manual',self.owner.state.manual)

    def adjust(self,kelvin,brightness=1.):
        return self.command('adjust',Appearance(kelvin,1.-brightness))

    def poll(self):
        results=self.store.poll()
        if results:self.last_result=results[-1]
        for result in results:
            if result['outcome'] in ('saved','save_failed','save_superseded'):
                self.last_save_result=result
        return results

    def save(self,settings,expected_revision,request_id):
        result=self.store.submit_save(SmartSettings.from_dict(settings),expected_revision,self.session_id,request_id)
        self.last_save_result=result
        return result

    def tick(self):
        self.owner.tick()
        return self.poll()

    def timeline(self):
        """Scheduled times only; no estimated catch-up or physical-output claim."""
        try:
            sample=self.owner.clock.sample()
            plan=self.owner.scheduled_plan(sample)
            local_day=sample.utc.astimezone(sample.zone).date()
            def label(instant):
                local=instant.astimezone(sample.zone)
                clock=local.strftime('%I:%M %p').lstrip('0')
                return clock if local.date()==local_day else local.strftime('%a ')+clock
            start=min(plan.warmth.start,plan.dim.start)
            zone=str(getattr(sample.zone,'key',sample.zone))
            kind={'personal':'Your schedule','solar':'Sunset schedule','explicit-fallback':'Your fallback schedule'}[plan.source]
            note='Scheduled times, not a catch-up estimate. Markers are not to scale. Windows time zone: '+zone+'.'
            if plan.reduced_peak:note+=' This short night uses a gentler peak to keep changes gradual.'
            return dict(available=True,start=label(start),late=label(plan.ready),end=label(plan.neutral),
                        start_utc=start.isoformat(),ready_utc=plan.ready.isoformat(),neutral_utc=plan.neutral.isoformat(),
                        warmth_start_utc=plan.warmth.start.isoformat(),dim_start_utc=plan.dim.start.isoformat(),
                        kind=kind,note=note,reduced_peak=plan.reduced_peak,timezone=zone,
                        time_resolution=list(plan.time_resolution),occurrence_id=plan.occurrence_id)
        except (ValueError,OSError,RuntimeError):
            return dict(available=False,kind='Schedule unavailable',note='Check your timing, saved location and Windows time zone. No current times can be confirmed.')

    def close(self):
        # Never block the GUI waiting for storage. Pending intent prevents a
        # clean recovery receipt; the serial worker can finish without Tk.
        self.store.close(wait=False)


def is_v2_controller(controller):
    return isinstance(controller,SmartDesktopController)
