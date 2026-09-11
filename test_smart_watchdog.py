import pytest
from smart_state import Appearance
from test_smart_runtime import runtime


def test_comfort_timeout_restores_off_when_civil_clock_fails(monkeypatch):
    owner,engine,_,clock=runtime()
    owner.command('begin_comfort',Appearance(3200,.1),token='comfort')
    clock.advance(21,sleep=True)
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(OSError('zone unavailable')))
    owner.tick()
    assert owner.state.preview is None and owner.state.mode=='off'
    assert not engine.is_enabled


def test_release_works_when_civil_clock_fails(monkeypatch):
    owner,engine,_,clock=runtime()
    owner.command('manual',Appearance(3500,.1))
    owner.command('begin_compare',token='compare')
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(ValueError('zone unavailable')))
    owner.command('end_preview',token='compare')
    assert owner.state.preview is None
    assert engine.temperature_k==3500 and engine.is_enabled


def test_compare_returns_to_current_smart_reference_with_half_second_restore(monkeypatch):
    owner,engine,_,clock=runtime()
    owner.command('smart');clock.advance(.1);owner.tick()
    owner.command('begin_compare',token='compare')
    calls=[];original=engine.set_state
    def record(**kwargs):calls.append(kwargs);return original(**kwargs)
    monkeypatch.setattr(engine,'set_state',record)
    clock.advance(1)
    owner.command('end_preview',token='compare')
    assert calls and calls[-1]['duration']==.5
    assert calls[-1]['temperature_k']==pytest.approx(3500)


def test_late_preview_release_never_undoes_new_off_with_broken_clock(monkeypatch):
    owner,engine,_,clock=runtime()
    owner.command('smart');owner.command('begin_compare',token='compare')
    owner.command('off')
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(OSError('zone unavailable')))
    owner.command('end_preview',token='compare')
    assert owner.state.mode=='off' and not engine.is_enabled


def test_save_during_compare_restores_new_preference_not_old_one(monkeypatch):
    from dataclasses import replace
    from smart_state import stage_save
    owner,engine,_,clock=runtime()
    owner.command('smart');owner.command('begin_compare',token='compare')
    ticket=stage_save(owner.state,replace(owner.state.settings,warmth_kelvin=4200),owner.state.config_revision)
    calls=[];original=engine.set_state
    def record(**kwargs):calls.append(kwargs);return original(**kwargs)
    monkeypatch.setattr(engine,'set_state',record)
    owner.accept_saved(ticket,owner.state.config_revision+1)
    assert owner.state.preview is None
    assert calls[-1]['temperature_k']==pytest.approx(4200) and calls[-1]['duration']==.5


def test_clockless_smart_preview_timeout_uses_neutral_not_stale_schedule(monkeypatch):
    owner,engine,_,clock=runtime()
    owner.command('smart');owner.command('begin_comfort',Appearance(3000,.1),token='comfort')
    clock.advance(21,sleep=True)
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(OSError('zone unavailable')))
    owner.tick()
    assert owner.state.preview is None and owner.state.mode=='smart'
    assert not engine.is_enabled and owner.tracker is None


def test_timeout_does_not_overwrite_foreign_transform(monkeypatch):
    owner,engine,backend,clock=runtime()
    owner.command('begin_comfort',Appearance(3000,.1),token='comfort')
    # Model another application's full software matrix, not an HT appearance.
    before=list(backend.matrix);before[1]=.1
    backend.matrix=tuple(before)
    before=backend.matrix
    clock.advance(21,sleep=True)
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(OSError('zone unavailable')))
    owner.tick()
    assert owner.state.preview is None and backend.matrix==before
