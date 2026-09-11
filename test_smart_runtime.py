from datetime import datetime,timedelta,timezone
import pytest
from smart_time import ClockSample
from smart_state import Appearance,SmartSettings
from smart_runtime import NativeSmartRuntime
from test_smart_conflicts import setup


class Clock:
    def __init__(self):
        self.utc=datetime(2026,9,9,22,tzinfo=timezone.utc)
        self.active=100.;self.elapsed=100.
    def sample(self):return ClockSample(self.utc,self.active,self.elapsed,timezone.utc)
    def elapsed_now(self):return self.elapsed
    def advance(self,seconds,*,sleep=False):
        self.utc+=timedelta(seconds=seconds)
        self.elapsed+=seconds
        if not sleep:self.active+=seconds


def runtime():
    engine,backend=setup()
    assert engine._apply_matrix(1,1,1)
    clock=Clock()
    settings=SmartSettings(kind='personal',evening_ready='22:00',morning_neutral='07:00',warmth_kelvin=3500,dim_fraction=.1)
    return NativeSmartRuntime(engine,settings,clock),engine,backend,clock


def test_native_smart_ticks_use_bounded_samples_not_restarted_animations(monkeypatch):
    owner,e,backend,clock=runtime()
    monkeypatch.setattr(e,'set_state',lambda **kw:pytest.fail('Automatic ticks must not restart set_state'))
    owner.command('smart')
    initial=len(backend.writes)
    for _ in range(30):clock.advance(.1);owner.tick()
    assert owner.tracker.warmth.position>0 and owner.state.mode=='smart'
    assert len(backend.writes)>initial
    for a,b in zip(backend.writes,backend.writes[1:]):
        assert max(abs(x-y) for x,y in zip(a,b))<=1/1024+1e-7


def test_off_invalidates_runtime_and_does_not_depend_on_clock(monkeypatch):
    owner,e,backend,clock=runtime()
    owner.command('smart');clock.advance(.1);owner.tick()
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(OSError('clock unavailable')))
    owner.command('off')
    assert owner.state.mode=='off' and not e.is_enabled
    before=len(backend.writes)
    owner.tick()
    assert len(backend.writes)==before


def test_failed_native_sample_does_not_commit_proposed_position():
    owner,e,backend,clock=runtime()
    owner.command('smart')
    previous=owner.tracker
    backend.write_ok=False;clock.advance(.1);owner.tick()
    assert owner.tracker==previous and e.output_fault=='backend_error'


def test_off_arriving_between_proposal_and_write_wins(monkeypatch):
    owner,e,backend,clock=runtime()
    owner.command('smart')
    write=e.apply_automatic_sample
    def interrupted(*args):
        owner.command('off')
        return write(*args)
    monkeypatch.setattr(e,'apply_automatic_sample',interrupted)
    clock.advance(.1);owner.tick()
    assert owner.state.mode=='off' and owner.tracker is None and not e.is_enabled


def test_pause_counts_sleep_but_output_does_not_jump_on_resume():
    owner,e,backend,clock=runtime()
    owner.command('smart');clock.advance(.1);owner.tick()
    owner.command('pause')
    assert not e.is_enabled
    expiry=owner.state.override.expires_elapsed
    clock.advance(3601,sleep=True);owner.tick()
    assert owner.state.override is None and clock.elapsed>expiry
    assert e.output_observation()['accepted_rgb']==[1.,1.,1.]
    clock.advance(.1);owner.tick()
    assert max(abs(1-v) for v in e.output_observation()['accepted_rgb'])<=1/1024


def test_temporary_v2_appearance_can_resume_without_fabricating_starting_output():
    owner,e,backend,clock=runtime()
    owner.command('smart')
    owner.command('adjust',Appearance(4200,.1))
    assert owner.state.override.kind=='manual_hold'
    owner.command('resume')
    assert owner.tracker is not None
    before=e.output_observation()['accepted_rgb']
    clock.advance(.1);owner.tick()
    after=e.output_observation()['accepted_rgb']
    assert max(abs(a-b) for a,b in zip(before,after))<=1/1024


def test_manual_windows_clear_waits_for_explicit_retry():
    owner,e,backend,clock=runtime()
    owner.command('manual',Appearance(4200,.1))
    e.set_windows_nightlight_policy(True);owner.tick()
    count=len(backend.writes)
    e.set_windows_nightlight_policy(False);owner.tick()
    assert len(backend.writes)==count and owner.state.manual_resume_required
    owner.command('retry')
    assert not owner.state.manual_resume_required and e.is_applied and e.is_enabled


def test_foreign_output_never_becomes_an_inferred_kelvin_start():
    owner,e,backend,clock=runtime()
    foreign=list(backend.matrix);foreign[1]=.1;backend.matrix=tuple(foreign)
    e.refresh_output_observation()
    before=len(backend.writes)
    owner.command('smart');clock.advance(.1);owner.tick()
    assert owner.tracker is None and len(backend.writes)==before
    assert owner.state.availability=='external_conflict'


@pytest.mark.parametrize('change', ['callback_gap','sleep','wall_forward','wall_back','zone'])
def test_discontinuities_rebase_at_accepted_output_without_a_jump(change):
    from zoneinfo import ZoneInfo
    owner,e,backend,clock=runtime()
    owner.command('smart')
    for _ in range(20):clock.advance(.1);owner.tick()
    before=e.output_observation()['accepted_rgb']
    if change=='callback_gap':clock.advance(20)
    elif change=='sleep':clock.advance(3600,sleep=True)
    elif change=='wall_forward':clock.utc+=timedelta(hours=3)
    elif change=='wall_back':clock.utc-=timedelta(hours=3)
    else:
        clock.sample=lambda:ClockSample(clock.utc,clock.active,clock.elapsed,ZoneInfo('Asia/Tokyo'))
    owner.tick()
    assert e.output_observation()['accepted_rgb']==before
    assert owner.tracker.warmth.velocity==0 and owner.tracker.dim.velocity==0
    clock.advance(.1);owner.tick()
    assert max(abs(a-b) for a,b in zip(before,e.output_observation()['accepted_rgb']))<=1/1024


def test_native_epoch_change_after_write_cannot_commit_old_proposal(monkeypatch):
    owner,e,backend,clock=runtime()
    owner.command('smart')
    previous=owner.tracker
    apply=e.apply_automatic_sample
    def superseded(*args):
        result=apply(*args)
        e.begin_automatic()
        return result
    monkeypatch.setattr(e,'apply_automatic_sample',superseded)
    clock.advance(.1);owner.tick()
    assert owner.tracker==previous and owner.status=='Display sample invalidated'


def test_solar_runtime_ignores_vpn_proxy_and_environment_timezone(monkeypatch):
    import socket
    from zoneinfo import ZoneInfo
    engine,backend=setup()
    assert engine._apply_matrix(1,1,1)
    clock=Clock()
    clock.sample=lambda:ClockSample(clock.utc,clock.active,clock.elapsed,ZoneInfo('America/Detroit'))
    settings=SmartSettings(kind='solar',latitude=42.3353,longitude=-83.2864)
    owner=NativeSmartRuntime(engine,settings,clock)
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:pytest.fail('Smart must not resolve an IP location'))
    owner.command('smart')
    before=owner._reference(clock.sample())(0)
    monkeypatch.setenv('TZ','Asia/Tokyo')
    monkeypatch.setenv('HTTPS_PROXY','http://vpn.invalid:9999')
    monkeypatch.setenv('HTTP_PROXY','http://vpn.invalid:9999')
    owner._plan_key=None  # Force recomputation, not just a cache hit.
    assert owner._reference(clock.sample())(0)==before
    clock.advance(.1);owner.tick()
    assert owner.state.settings.latitude==42.3353 and owner.tracker is not None


def test_changing_color_policy_does_not_apply_or_migrate_output():
    e,backend=setup()
    assert e._apply_matrix(.9,.7,.5)
    old=e.output_observation()['accepted_rgb']; count=len(backend.writes)
    owner=NativeSmartRuntime(e,SmartSettings(kind='personal'),Clock())
    owner.command('smart')
    assert owner.tracker is None and len(backend.writes)==count
    assert e.output_observation()['accepted_rgb']==old


def test_manual_selected_while_windows_blocks_still_requires_explicit_recovery():
    owner,e,backend,clock=runtime()
    e.set_windows_nightlight_policy(True)
    owner.command('manual',Appearance(4200,.1))
    assert owner.state.manual_resume_required
    count=len(backend.writes)
    e.set_windows_nightlight_policy(False);owner.tick()
    assert len(backend.writes)==count and owner.state.manual_resume_required


@pytest.mark.parametrize('warmth,dim', [(1200,.8),(6500,0),(6500,.8),(1200,0)])
def test_valid_appearance_extremes_can_rejoin_smart(warmth,dim):
    owner,e,backend,clock=runtime()
    owner.command('manual',Appearance(warmth,dim))
    assert e.is_applied
    before=e.output_observation()['accepted_rgb']
    owner.command('smart')
    assert owner.tracker is not None
    clock.advance(.1);owner.tick()
    assert max(abs(a-b) for a,b in zip(before,e.output_observation()['accepted_rgb']))<=1/1024
