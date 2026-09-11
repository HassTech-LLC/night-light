"""Private pipe bridge between the embedded UI and the existing Tk-owned engine.

The page never receives the IPC credential and has no HTTP control endpoint.
All display operations execute on the existing GUI owner thread.
"""
from datetime import datetime, timedelta
from collections import OrderedDict
from pathlib import Path
import json
import math
import os
import queue
import secrets
import subprocess
import sys
import threading
import time

from smart_mode import coordinates, solar_event
from smart_learning import clock_minutes
from smart_location import lookup_postal
from smart_desktop import is_v2_controller
from smart_state import Appearance
from smart_state import SmartSettings
from smart_time import ClockSource
from smart_migration import propose_migration, inspect_legacy
from build_identity import running_identity


COMMAND_FIELDS = {
    'state':set(), 'compare':{'enabled'}, 'adjust':{'kelvin','brightness'},
    'power':set(), 'off':set(), 'mode':{'mode'}, 'pause':set(), 'resume':set(),
    'save_smart':{'profile','bedtime','start','end','latitude','longitude','expected_revision'},
    'save_comfort':{'settings','expected_revision'},
    'preview_comfort':{'warmth_kelvin','dim_fraction'},
    'preview_migration':{'settings','expected_revision'},
    'commit_migration':{'review_id','expected_revision'},
    'delete_location':set(), 'learning':{'enabled'}, 'autostart':{'enabled'},
    'reset_learning':set(), 'mark_sleep':set(), 'mark_wake':set(),
    'windows_off':set(), 'retry_display':set(), 'quit':set(), 'hide':set(),
}


def number(value, low, high):
    if isinstance(value, bool):
        raise ValueError('Enter a number.')
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f'Value must be between {low} and {high}.')
    return result


class PremiumActions:
    def __init__(self, app, engine, config):
        self.app, self.engine, self.config = app, engine, config
        self.preview = None
        self.preview_deadline = 0
        self.session_id = secrets.token_hex(16)
        self.snapshot_sequence = 0
        self.recent_saves = OrderedDict()
        self.migration_proposal=None
        self.migration_review=None
        self.build_identity=running_identity()

    def end_preview(self):
        if getattr(self.app,'migration_interlocked',lambda:False)():
            self.preview=None;self.preview_deadline=0
            return
        if is_v2_controller(self.app.smart):
            token=self.preview
            self.preview=None
            if token:self.app.smart.owner.command('end_preview',token=token)
            return
        if self.preview is not None:
            saved, self.preview = self.preview, None
            self.engine.set_state(**saved, smooth=False)

    def turn_off(self):
        # Display recovery must not wait for storage or a stale Save revision.
        self.preview = None
        self.preview_deadline = 0
        if is_v2_controller(self.app.smart):
            self.app.smart.command('off')
            return 'Off requested. Saving your choice…'
        self.app.smart.manual(reset=True)
        try:
            self.config.transactional_update({'enabled':False,'smart_enabled':False,'smart_hold_until':0})
        except OSError:
            return "Off now. Couldn't save this for next startup. Try turning it off again to retry saving."
        return 'Off saved. Automatic adjustments will stay off until you enable them.'

    def dispatch(self, data):
        if not isinstance(data, dict) or not isinstance(data.get('action'), str):
            raise ValueError('Invalid action.')
        action = data['action']
        if action not in COMMAND_FIELDS:
            raise ValueError('Unknown action.')
        allowed = COMMAND_FIELDS[action] | {'action','protocol_version','session_id','request_id'}
        if data.keys() - allowed:
            raise ValueError('Unexpected command fields.')
        if 'protocol_version' in data and (type(data['protocol_version']) is not int or data['protocol_version'] != 2):
            raise ValueError('Unsupported controls protocol. Reopen Night Light.')
        if 'session_id' in data and (not isinstance(data['session_id'],str) or not 1 <= len(data['session_id']) <= 128):
            raise ValueError('Invalid session identity.')
        if action not in {'off','state'} and data.get('session_id',self.session_id) != self.session_id:
            raise ValueError('The app session changed. Reopen the controls before trying again.')
        request_id = data.get('request_id')
        if request_id is not None and (not isinstance(request_id,str) or not 1 <= len(request_id) <= 128):
            raise ValueError('Invalid request identity.')
        key = (data.get('session_id',self.session_id),request_id)
        draft = json.dumps(data,sort_keys=True,allow_nan=False) if action=='save_smart' and request_id else None
        if draft is not None and key in self.recent_saves:
            saved_draft, result = self.recent_saves[key]
            if draft != saved_draft:
                raise ValueError('This request identity was already used for a different draft.')
            return result
        result = self._dispatch(data)
        if draft is not None:
            self.recent_saves[key] = (draft,result)
            while len(self.recent_saves)>128:
                self.recent_saves.popitem(last=False)
        return result

    def _dispatch(self, data):
        action=data['action']; s=self.app.smart; c=self.config; e=self.engine
        if getattr(self.app,'migration_interlocked',lambda:False)():
            if action in {'off','power'}:return self.app.migration_off()
            if action=='state':return
            if action=='hide':return self.app.flyout.hide_flyout()
            if action=='quit':return self.app.quit_app()
            raise ValueError('Finishing the Smart switch. Other controls are paused; Off is still available.')
        if is_v2_controller(s):return self._dispatch_v2(data)
        if action=='preview_migration':return self._preview_migration(data)
        if action=='commit_migration':return self._commit_migration(data)
        if getattr(c,'automatic_output_blocked',False) and (
            action in {'save_smart','resume'} or (action=='mode' and data.get('mode')=='smart')
        ):
            raise ValueError('Smart is unavailable because recovery settings could not be saved. Check storage, then restart Night Light.')
        turning_off = action=='off' or (action=='power' and (s.enabled or e.is_enabled or self.preview is not None))
        if turning_off:
            self.preview = None
            self.preview_deadline = 0
        elif action not in {'state','compare','save_smart'}:
            self.end_preview()
        if action=='state':return
        if action=='compare':
            if type(data.get('enabled')) is not bool:raise ValueError('Invalid compare state.')
            if data['enabled'] and self.preview is None:
                self.preview={'enabled':e.is_enabled,'temperature_k':e.temperature_k,'brightness':e.brightness}
                self.preview_deadline=time.monotonic()+10
                e.set_state(enabled=False,smooth=False)
            elif not data['enabled']:self.end_preview()
            return
        if action=='adjust':
            k=int(number(data.get('kelvin'),1200,6500));b=number(data.get('brightness'),.2,1)
            s.hold();e.set_state(enabled=True,temperature_k=k,brightness=b,smooth=False)
            for key,value in [('temperature_k',k),('brightness',b),('enabled',True),('last_temperature_k',k)]:c.set(key,value,False)
            c.save_debounced();return
        if action=='power':
            if turning_off:return self.turn_off()
            else:
                e.set_state(enabled=True,temperature_k=int(c.get('last_temperature_k',3400)),smooth=True)
                c.set('enabled',True)
        elif action=='off':return self.turn_off()
        elif action=='mode':
            if data.get('mode')=='manual':
                s.manual()
                for key,value in [('enabled',e.is_enabled),('temperature_k',e.temperature_k),('brightness',e.brightness)]:c.set(key,value,False)
                c.save_debounced()
            elif data.get('mode')=='smart':c.set('smart_enabled',True);s.resume()
            else:raise ValueError('Choose Smart or Manual.')
        elif action=='pause':s.hold(pause=True)
        elif action=='resume':s.resume()
        elif action=='retry_display':
            was_enabled=e.is_enabled
            requested={'temperature_k':e.temperature_k,'brightness':e.brightness}
            if not e.retry_display():raise ValueError(e.output_observation()['error'] or 'Display is still unavailable.')
            if s.enabled:
                if getattr(c,'automatic_output_blocked',False):
                    return 'Display connection restored. Smart remains stopped until recovery settings can be saved.'
                try:held=s.clock().timestamp()<float(c.get('smart_hold_until',0))<=s.clock().timestamp()+3600
                except (ValueError,TypeError):held=False
                if held and c.get('smart_hold_kind')=='pause':
                    return 'Display connection restored. Smart remains paused.'
                if held:
                    e.set_state(enabled=True,**requested,smooth=True)
                    return 'Display connection restored. Your temporary adjustment is still in effect.'
                s.rejoin=True;s.fade_until=0;s.tick()
                return 'Display connection restored. Smart is following your schedule.'
            if was_enabled:
                e.set_state(enabled=True,**requested,smooth=True)
                return 'Display connection restored. Your Manual appearance was requested.'
            return 'Display connection restored. Night Light remains off.'
        elif action=='save_smart':
            profile=data.get('profile');bedtime=data.get('bedtime','');start=data.get('start','');end=data.get('end','')
            if profile not in ('balanced','maximum'):raise ValueError('Choose an evening profile.')
            if bedtime:clock_minutes(bedtime)
            quiet=None
            if start or end:
                if clock_minutes(start)==clock_minutes(end):raise ValueError('Quiet times must differ.')
                quiet={'start':start,'end':end}
            lat,lon=data.get('latitude',''),data.get('longitude','')
            location=coordinates(lat,lon) if lat!='' or lon!='' else None
            if location is None and quiet is None:raise ValueError('Enter a location or fallback quiet hours.')
            c.transactional_update({
                'smart_bedtime':bedtime, 'smart_quiet_hours':quiet,
                'smart_profile':profile, 'smart_enabled':True,
                'smart_hold_until':0,
                'smart_location':None if location is None else dict(zip(('latitude','longitude'),location)),
            }, expected_revision=data.get('expected_revision'))
            # Only a committed draft can replace the current display intent.
            self.preview = None
            self.preview_deadline = 0
            s.resume()
            if e.output_fault:
                return 'Saved. Smart is enabled, but display adjustment is unavailable. See Retry display in Quick guide & safety.'
            if e.is_suppressed_by_windows_nightlight:
                return 'Saved. Smart is enabled, but Windows Night Light is blocking this filter. See Quick guide & safety.'
            return 'Saved. Smart Mode is enabled and follows your schedule; warmth may stay neutral during daylight.'
        elif action=='delete_location':
            s.manual(reset=True);c.set('smart_location',None);return 'Location deleted. Smart stopped.'
        elif action in ('learning','autostart'):
            enabled=data.get('enabled')
            if type(enabled) is not bool:raise ValueError('Invalid setting.')
            if action=='autostart':
                if not c.set_autostart(enabled):raise ValueError('Windows startup setting could not be saved.')
            else:
                c.set('smart_learning',enabled);s.learner.last_active=s.learner.pending=None;s.resume()
        elif action=='reset_learning':s.learner.reset();s.resume();return 'Learning history deleted.'
        elif action=='mark_sleep':
            if not c.get('smart_learning',False):raise ValueError('Enable local learning first.')
            s.learner.last_active=datetime.now().astimezone();s.learner.pending=None;return 'Winding-down time noted for this session.'
        elif action=='mark_wake':
            if not c.get('smart_learning',False) or s.learner.last_active is None:raise ValueError('No winding-down time available.')
            s.learner.record(s.learner.last_active,datetime.now().astimezone());s.learner.last_active=s.learner.pending=None;s.tick();return 'Timing recorded if the interval was valid.'
        elif action=='windows_off':self.app.turn_windows_nightlight_off()
        elif action=='quit':self.app.quit_app()
        elif action=='hide':self.app.flyout.hide_flyout()
        else:raise ValueError('Unknown action.')

    def _preview_migration(self,data):
        # A review has no native display or persistent effects. The immutable
        # proposal stays native; clients receive only its safe review fields.
        self.migration_proposal=None;self.migration_review=None
        if type(data.get('expected_revision')) is not int or data['expected_revision']!=self.config.get('config_revision',0):
            raise ValueError('Settings changed. Reload before reviewing migration.')
        sample=ClockSource().sample()
        settings=SmartSettings.from_dict(data.get('settings'))
        proposal=propose_migration(self.config.data,settings,now_utc=sample.utc)
        plans=[settings.plan(sample.utc.astimezone(sample.zone).date()+timedelta(days=offset),sample.zone)
               for offset in (-1,0,1)]
        active=[p for p in plans if min(p.warmth.start,p.dim.start)<=sample.utc<p.neutral]
        plan=max(active,key=lambda p:p.ready) if active else min((p for p in plans if p.neutral>sample.utc),key=lambda p:p.ready)
        current=inspect_legacy(self.config.data)
        review=dict(review_id=secrets.token_hex(16),request_id=data.get('request_id'),
                    config_revision=proposal.source_revision,current=current,settings=settings.to_dict(),
                    start=min(plan.warmth.start,plan.dim.start).astimezone(sample.zone).isoformat(),
                    ready=plan.ready.astimezone(sample.zone).isoformat(),neutral=plan.neutral.astimezone(sample.zone).isoformat(),
                    source=plan.source,reduced_peak=plan.reduced_peak,
                    start_label=min(plan.warmth.start,plan.dim.start).astimezone(sample.zone).strftime('%a %b %d, %I:%M %p %Z'),
                    ready_label=plan.ready.astimezone(sample.zone).strftime('%a %b %d, %I:%M %p %Z'),
                    neutral_label=plan.neutral.astimezone(sample.zone).strftime('%a %b %d, %I:%M %p %Z'),
                    preserved_mode=current['mode'],preserved_override=proposal.override is not None,
                    switch_available=(not getattr(self.config,'automatic_output_blocked',False)
                                      and callable(getattr(self.app,'begin_smart_migration',None))
                                      and Path(sys.executable).is_file()))
        self.migration_proposal=proposal
        self.migration_review=review
        return 'Review ready. Your current schedule and display are unchanged.'

    def _commit_migration(self,data):
        """Approve only the native proposal created by the current review.

        The web view supplies a short review identity, never a binary path,
        source digest, proposal, or preview assertion. The native host binds the
        handoff to the running executable and rechecks the config revision.
        """
        review=self.migration_review
        proposal=self.migration_proposal
        if not review or proposal is None:
            raise ValueError('Review Smart Comfort before switching.')
        if data.get('review_id')!=review['review_id']:
            raise ValueError('This Smart review is no longer current. Review it again.')
        expected=data.get('expected_revision')
        if type(expected) is not int or expected!=review['config_revision'] or expected!=self.config.get('config_revision',0):
            self.migration_review=None;self.migration_proposal=None
            raise ValueError('Settings changed. Review Smart Comfort again before switching.')
        if not review.get('switch_available'):
            raise ValueError('Smart switching is unavailable until recovery storage is ready.')
        begin=getattr(self.app,'begin_smart_migration',None)
        if not callable(begin):raise ValueError('Smart switching is unavailable in this app host.')
        begin(proposal,Path(sys.executable))
        return 'Switching to Smart Comfort. Your current display is being kept safe during the handoff.'

    def _dispatch_v2(self,data):
        action=data['action'];s=self.app.smart
        if action=='state':return
        if action=='preview_comfort':
            appearance=Appearance(data.get('warmth_kelvin'),data.get('dim_fraction'))
            token=secrets.token_hex(16)
            s.owner.command('begin_comfort',appearance,token=token)
            self.preview=token;self.preview_deadline=time.monotonic()+20
            return 'Previewing for 20 seconds. Restore ends it now; only Save and enable commits your settings.'
        if action=='save_comfort':
            s.save(data.get('settings'),data.get('expected_revision'),data.get('request_id'))
            return 'Saving your Smart Comfort settings…'
        if action=='compare':
            if type(data.get('enabled')) is not bool:raise ValueError('Invalid compare state.')
            if data['enabled'] and (s.owner.state.preview is None or s.owner.state.preview.kind!='compare'):
                token=secrets.token_hex(16)
                s.owner.command('begin_compare',token=token)
                self.preview=token;self.preview_deadline=time.monotonic()+10
            elif not data['enabled']:self.end_preview()
            return
        if action=='off' or (action=='power' and (s.owner.state.mode!='off' or s.owner.state.preview is not None)):
            return self.turn_off()
        if action in {'save_smart','learning','reset_learning','mark_sleep','mark_wake','delete_location'}:
            raise ValueError('Use the updated Smart settings controls; legacy setup and learning cannot change Smart Comfort.')
        self.end_preview()
        request_id=data.get('request_id')
        if action=='adjust':
            appearance=Appearance(number(data.get('kelvin'),1200,6500),1-number(data.get('brightness'),.2,1))
            s.command('adjust',appearance,request_id)
        elif action=='power':s.command('manual',s.owner.state.manual,request_id)
        elif action=='mode':
            mode=data.get('mode')
            if mode not in ('smart','manual'):raise ValueError('Choose Smart or Manual.')
            s.command(mode,s.owner.state.manual if mode=='manual' else None,request_id)
        elif action in {'pause','resume'}:s.command(action,request_id=request_id)
        elif action=='retry_display':
            if not s.owner.command('retry'):raise ValueError('Display adjustment is still unavailable.')
            return 'Display retry requested. Check the current output status.'
        elif action=='autostart':
            enabled=data.get('enabled')
            if type(enabled) is not bool:raise ValueError('Invalid setting.')
            if not self.config.set_autostart(enabled):raise ValueError('Windows startup setting could not be saved.')
            return 'Windows startup preference saved.'
        elif action=='windows_off':self.app.turn_windows_nightlight_off();return
        elif action=='quit':self.app.quit_app();return
        elif action=='hide':self.app.flyout.hide_flyout();return
        else:raise ValueError('Unknown action.')
        return 'Choice applied. Saving…'

    def _snapshot_v2(self):
        s=self.app.smart;e=self.engine;c=self.config;state=s.owner.state
        result=s.last_result or {};outcome=result.get('outcome','')
        message={'command_saving':'Saving your choice…','off_saving':'Saving Off…',
                 'command_saved':'Choice saved.','off_saved':'Off saved.',
                 'command_not_saved':'Your current choice could not be saved. Try again before closing.',
                 'off_not_saved':'Off requested, but it could not be saved. Try Off again.',
                 'command_superseded':'An earlier request was replaced by your newer choice.'}.get(outcome,'')
        paused=state.override is not None and state.override.kind=='neutral_pause'
        title='Resting for now' if state.mode=='off' else 'Taking a break' if paused else 'Following your rhythm' if s.enabled else 'Your Manual appearance'
        observation=e.output_observation()
        preview=state.preview
        if preview is not None:title='Previewing your evening' if preview.kind=='comfort' else 'Original colors, briefly'
        try:remaining=max(0,math.ceil(preview.expires_elapsed-s.owner.clock.elapsed_now())) if preview else 0
        except (ValueError,OSError,RuntimeError):remaining=0
        detail=s.status
        if observation.get('error'):detail=observation['error']
        if message:detail+=' · '+message
        return dict(protocol_version=2,session_id=self.session_id,sequence=self.snapshot_sequence,
                    config_revision=state.config_revision,policy_version=state.settings.policy_version,
                    output=observation,output_fault=e.output_fault,smart=s.enabled,enabled=e.is_enabled,
                    power=state.mode!='off' or preview is not None,kelvin=e.temperature_k,brightness=e.brightness,
                    blocked=state.availability!='available',hold=state.override is not None,
                    preview=preview is not None,preview_kind=preview.kind if preview else None,
                    preview_remaining=remaining,title=title,detail=detail,meta='Smart Comfort · '+state.mode,
                    times=s.timeline(),learning_status='Smart Comfort does not collect routine history.',hotkey_status=s.hotkey_status,
                    command_result=result,save_result=s.last_save_result,smart_settings=state.settings.to_dict(),
                    first_run=isinstance(c.get('onboarding_v2'),dict) and c.get('onboarding_v2').get('completed') is False,
                    settings=dict(location=None,profile='balanced',bedtime='',quiet=None,learning=False,
                                  autostart=c.is_autostart_enabled()))

    def snapshot(self):
        state=self._snapshot_current()
        state['build_identity']=self.build_identity
        interlocked=getattr(self.app,'migration_interlocked',lambda:False)()
        state['migration_pending']=interlocked
        switch=getattr(self.app,'_migration',None)
        state['migration_result']=None if switch is None else switch.result
        if interlocked:
            failed=switch is not None and switch.done
            state.update(title='Smart switch needs attention' if failed else 'Switching Smart safely',
                meta='Smart Comfort · settings handoff',
                detail=('Original colors were requested. Restart Night Light before trying again; the settings handoff could not be confirmed.'
                        if failed else 'Saving your choices and keeping a recovery copy. Other controls are paused; Off is still available.'),
                times={})
        return state

    def _snapshot_current(self):
        self.snapshot_sequence += 1
        if is_v2_controller(self.app.smart):return self._snapshot_v2()
        s,e,c=self.app.smart,self.engine,self.config
        hold=c.get('smart_hold_until',0)
        try:hold=number(hold,0,time.time()+3601)>time.time()
        except (ValueError,TypeError):hold=False
        blocked=e.is_suppressed_by_windows_nightlight
        status=self.app._get_display_status()
        detail=s.status if s.enabled else status.detail
        title='Winding down' if s.enabled else 'Just how you like it'
        if s.enabled and 'Daylight' in s.status:title='Daylight, naturally'
        if not s.enabled and not e.is_enabled:title='Resting for now'
        if hold:title='Taking a break' if c.get('smart_hold_kind')=='pause' else 'Your evening, adjusted'
        if blocked:title='Windows has the light'
        if s.enabled and 'needs setup' in s.status:title='Let’s set your rhythm'
        if not e.is_applied and e.is_enabled and not blocked:detail='Display backend has not confirmed the filter. '+detail
        if getattr(c,'automatic_output_blocked',False):
            title='Smart needs attention'
            detail='Recovery settings could not be saved. Smart is stopped. Check storage, then restart Night Light.'
        elif getattr(c,'recovered_unclean_session',False) and not s.enabled and not e.is_enabled:
            title='Safely restarted'
            detail='Night Light did not close cleanly. Automatic adjustments are off; review your settings before enabling them.'
        if not e.is_enabled and e.output_observation()['error']:
            title='Off — display reset unconfirmed'
            detail='Automatic adjustments are off, but Windows has not confirmed the original-color reset. '+e.output_observation()['error']
        if e.output_fault:
            title=('Display transform changed' if e.output_fault=='external_conflict' else 'Display needs attention')
            if not s.enabled and not e.is_enabled:title='Off — '+title[0].lower()+title[1:]
            detail=e.output_observation()['error'] or 'Display adjustment is unavailable. Try Retry display in Quick guide & safety.'
        times={}
        now=datetime.now().astimezone();loc=c.get('smart_location')
        try:
            if isinstance(loc,dict):
                sunset=solar_event(now.date(),loc['latitude'],loc['longitude'],False)
                sunrise=solar_event(now.date()+timedelta(days=1),loc['latitude'],loc['longitude'],True)
                if sunset and sunrise:
                    sunset=sunset.astimezone();sunrise=sunrise.astimezone()
                    start=sunset-timedelta(hours=1);late=sunset+timedelta(hours=3)
                    if s.last_guard is not None:
                        bed=now.replace(hour=s.last_guard//60,minute=s.last_guard%60,second=0,microsecond=0)
                        if bed.hour<12:bed+=timedelta(days=1)
                        adjusted=min(sunset,bed-timedelta(hours=4))
                        start=min(start,bed-timedelta(hours=5));late=adjusted+timedelta(hours=3)
                    times={'start':start.strftime('%I:%M %p').lstrip('0'),'late':late.strftime('%I:%M %p').lstrip('0'),'end':sunrise.strftime('%I:%M %p').lstrip('0'),'kind':'Local solar schedule','note':'Local Windows time. Phase spacing is illustrative.'}
            if not times and isinstance(c.get('smart_quiet_hours'),dict):
                quiet=c.get('smart_quiet_hours');times={'start':quiet['start'],'end':quiet['end'],'kind':'Fallback quiet hours'}
        except (ValueError,TypeError,KeyError,OverflowError):pass
        return {'protocol_version':2,'session_id':self.session_id,'sequence':self.snapshot_sequence,
                'migration_review':self.migration_review if self.migration_review and self.migration_review['config_revision']==c.get('config_revision',0) else None,
                'config_revision':c.get('config_revision',0),
                'output':e.output_observation(),
                'output_fault':e.output_fault,
                'smart':s.enabled,'enabled':e.is_enabled,'power':s.enabled or e.is_enabled,'kelvin':e.temperature_k,'brightness':e.brightness,
                'blocked':blocked,'hold':hold,'preview':self.preview is not None,'title':title,'detail':detail,
                'meta':('Smart' if s.enabled else 'Manual')+' · '+('needs attention' if e.output_fault else 'paused' if blocked or (hold and c.get('smart_hold_kind')=='pause') else 'adjusted' if hold else 'active' if e.is_enabled else 'off'),
                'times':times,'learning_status':s.learning_status,'hotkey_status':getattr(s,'hotkey_status',''),
                'settings':{'location':loc,'profile':c.get('smart_profile','balanced'),'bedtime':c.get('smart_bedtime',''),'quiet':c.get('smart_quiet_hours'),
                            'learning':c.get('smart_learning',False),'autostart':c.is_autostart_enabled()}}


class PremiumFlyout:
    def __init__(self, app, engine, config):
        self.app=app;self.actions=PremiumActions(app,engine,config)
        self.process=None;self.visible=False;self.ready=False;self.messages=queue.Queue(maxsize=256)
        self.closed=False;self.last_state=0;self.lookup_busy=False
        app.root.after(40,self._poll)

    def winfo_viewable(self):return self.visible
    def hide_flyout(self):
        self.actions.end_preview();self.visible=False;self._send({'kind':'hide'})

    def show_flyout_at_tray(self):
        if self.process is None or self.process.poll() is not None:
            base=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'assets/premium'
            profile=self.actions.config.file_path.parent/'WebView2'
            env=os.environ.copy()
            # Do not inherit ambient debugging or browser command-line overrides.
            for key in list(env):
                if key.startswith('WEBVIEW2_'):env.pop(key)
            args=[str(base/'NightLight.Premium.exe'),str(base),str(profile)]
            capture=os.environ.get('NIGHT_LIGHT_PREMIUM_CAPTURE')
            if capture:args.append(capture)
            self.process=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8',creationflags=0x08000000,env=env)
            process=self.process
            def read():
                try:
                    for line in iter(lambda:process.stdout.readline(16386),''):
                        if len(line)>16384:continue
                        try:self.messages.put_nowait(json.loads(line))
                        except (ValueError,queue.Full):continue
                except (OSError,ValueError):pass
            threading.Thread(target=read,daemon=True).start()
            self.ready=False
        else:self._send({'kind':'show'})
        self.visible=True

    def _send(self,data):
        if self.process and self.process.poll() is None:
            try:self.process.stdin.write(json.dumps(data)+'\n');self.process.stdin.flush()
            except (OSError,ValueError):self.visible=False;self.actions.end_preview()

    def update_ui_state(self):
        if self.ready:self._send({'kind':'state','state':self.actions.snapshot()})

    def _lookup(self,data):
        if self.lookup_busy:return
        self.lookup_busy=True
        def work():
            try:result={'kind':'lookup','places':lookup_postal(data.get('country',''),data.get('postal',''))}
            except Exception:result={'kind':'error','message':'Lookup failed. Check the postal code or enter coordinates.'}
            self.messages.put(result)
        threading.Thread(target=work,daemon=True).start()

    def _poll(self):
        if self.closed:return
        if self.actions.preview and time.monotonic()>self.actions.preview_deadline:self.actions.end_preview()
        if self.process and self.process.poll() is not None:
            self.actions.end_preview();self.visible=False;self.ready=False
        for _ in range(32):
            try:data=self.messages.get_nowait()
            except queue.Empty:break
            if not isinstance(data,dict):continue
            kind=data.get('kind')
            if kind=='ready':self.ready=True;self.update_ui_state()
            elif kind in ('hidden','failed'):self.visible=False;self.actions.end_preview()
            elif kind=='shown':self.visible=True
            elif kind in ('lookup','error'):self.lookup_busy=False;self._send(data)
            elif data.get('action')=='lookup':self._lookup(data)
            elif 'action' in data:
                try:
                    message=self.actions.dispatch(data)
                    if data['action'] not in ('state','compare') and getattr(self.app,'tray_icon',None):
                        self.app.tray_icon.icon=self.app._get_current_image()
                        self.app.tray_icon.title=self.app._get_tooltip()
                    if data['action'] not in ('state','compare') and hasattr(self.app,'_ensure_jumplist'):
                        self.app._ensure_jumplist()
                    self._send({'kind':'state','state':self.actions.snapshot(),'message':message,'request_id':data.get('request_id')})
                except (ValueError,TypeError,KeyError,OverflowError,OSError) as error:
                    message=('Could not save your settings. Your previous settings are unchanged.' if data.get('action')=='save_smart'
                             else 'Could not save to disk. Please check the current state and try again.') if isinstance(error,OSError) else str(error)
                    self._send({'kind':'error','message':message,'request_id':data.get('request_id')})
        if self.visible and time.monotonic()-self.last_state>1:
            self.update_ui_state();self.last_state=time.monotonic()
        self.app.root.after(40,self._poll)

    def close(self):
        # Shutdown must never restore a pre-compare filter after emergency reset.
        self.closed=True;self.actions.preview=None;self._send({'kind':'close'})
        if self.process:
            try:self.process.stdin.close()
            except (OSError,ValueError):pass
