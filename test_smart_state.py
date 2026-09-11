"""Pure owner-state contracts: no display, filesystem, timers or IPC."""
import dataclasses
import pytest

from smart_state import Appearance, OutputObservation, SmartSettings, ControlState as State, Event, reduce, resolve, stage_save, commit_saved


def ControlState(**kwargs):
    # Most reducer scenarios inject a confirmed fake backend. Production
    # construction remains unknown until the owner establishes availability.
    return State(**{'availability':'available',**kwargs})


def settings(**changes):
    value=dict(kind='personal',evening_ready='22:00',morning_neutral='07:00',
               warmth_kelvin=4000,dim_fraction=0)
    value.update(changes)
    return SmartSettings.from_dict(value)


@pytest.mark.parametrize('change',[
    {'kind':'automatic-ip'}, {'evening_ready':'25:00'}, {'morning_neutral':'22:00'},
    {'warmth_kelvin':True}, {'dim_fraction':float('nan')}, {'dim_fraction':.81},
    {'slower':0}, {'timezone_policy':'vpn'}, {'unknown':'ignored'},
    {'latitude':42}, {'latitude':91,'longitude':0}, {'kind':'solar'},
])
def test_invalid_settings_rejected(change):
    with pytest.raises(ValueError):settings(**change)


def test_settings_round_trip_and_independent_comfort():
    value=settings(warmth_kelvin=6500,dim_fraction=.4)
    assert SmartSettings.from_dict(value.to_dict())==value
    assert value.appearance==Appearance(6500,.4)
    assert settings(kind='solar',latitude=42.3353,longitude=-83.2864).kind=='solar'


def test_new_state_off_and_no_preview_implicit():
    assert State().availability=='unknown' and resolve(State()).kind=='none'
    state=ControlState()
    assert state.mode=='off'
    assert resolve(state).kind=='neutral'
    assert reduce(state,Event('begin_compare',0,token='a'))==state


def test_explicit_comfort_preview_over_off_and_new_off_wins():
    state=reduce(ControlState(),Event('begin_comfort',10,appearance=Appearance(4000,.1),token='native-a'))
    assert state.mode=='off'
    assert resolve(state).appearance==Appearance(4000,.1)
    off=reduce(state,Event('off',11))
    assert off.generation>state.generation
    assert resolve(off).kind=='neutral'
    assert reduce(off,Event('end_preview',12,token='native-a'))==off


def test_preview_expiry_resolves_latest_intent_not_captured_output():
    state=reduce(ControlState(),Event('manual',0,appearance=Appearance(5000,.1)))
    state=reduce(state,Event('begin_compare',1,token='a'))
    assert resolve(state).kind=='neutral'
    state=reduce(state,Event('adjust',2,appearance=Appearance(3500,.2)))
    state=reduce(state,Event('end_preview',11,token='a'))
    assert resolve(state).appearance==Appearance(3500,.2)


def test_smart_adjustment_and_pause_mutually_exclusive_elapsed_expiry():
    state=reduce(ControlState(),Event('smart',0))
    state=reduce(state,Event('adjust',5,appearance=Appearance(3500,.2)))
    assert state.mode=='smart' and state.override.kind=='manual_hold'
    assert resolve(state).kind=='appearance'
    state=reduce(state,Event('pause',6))
    assert state.override.kind=='neutral_pause' and resolve(state).kind=='neutral'
    assert reduce(state,Event('tick',3605)).override is not None
    state=reduce(state,Event('tick',3606))
    assert state.override is None and resolve(state).kind=='smart'


@pytest.mark.parametrize('kind',['pause','resume'])
def test_stale_smart_actions_cannot_enable_manual_or_off(kind):
    for state in (ControlState(),ControlState(mode='manual')):
        with pytest.raises(ValueError):reduce(state,Event(kind,0))


def test_windows_clear_does_not_silently_restore_manual():
    state=reduce(ControlState(),Event('manual',0,appearance=Appearance(3500,.2)))
    state=reduce(state,Event('availability',1,availability='windows_on'))
    assert resolve(state).kind=='none'
    state=reduce(state,Event('availability',2,availability='available'))
    assert resolve(state).kind=='none'
    state=reduce(state,Event('retry',3))
    assert resolve(state).appearance==Appearance(3500,.2)


def test_unexpected_conflict_latches_until_explicit_retry():
    state=reduce(ControlState(),Event('smart',0))
    state=reduce(state,Event('availability',1,availability='external_conflict'))
    state=reduce(state,Event('availability',2,availability='available'))
    assert resolve(state).kind=='none'
    assert resolve(reduce(state,Event('retry',3))).kind=='smart'
    off=reduce(state,Event('off',4))
    assert resolve(reduce(off,Event('retry',5))).kind=='neutral'


def test_save_ticket_invalidated_by_off_before_commit():
    state=ControlState(config_revision=12)
    ticket=stage_save(state,settings(),12)
    off=reduce(state,Event('off',10))
    with pytest.raises(ValueError,match='changed'):commit_saved(off,ticket,13)
    assert off.mode=='off'


def test_save_commits_only_matching_revision_and_keeps_display_block_separate():
    state=ControlState(config_revision=12,availability='windows_on')
    ticket=stage_save(state,settings(),12)
    saved=commit_saved(state,ticket,13)
    assert saved.mode=='smart' and saved.config_revision==13
    assert saved.settings==settings() and resolve(saved).kind=='none'
    with pytest.raises(ValueError):stage_save(saved,settings(),12)
    with pytest.raises(ValueError):commit_saved(state,ticket,12)


def test_preview_tokens_and_native_duration_limits():
    state=ControlState(mode='manual')
    preview=reduce(state,Event('begin_compare',10,token='a'))
    assert reduce(preview,Event('end_preview',11,token='b'))==preview
    assert reduce(preview,Event('tick',19.99)).preview is not None
    assert reduce(preview,Event('tick',20)).preview is None
    comfort=reduce(state,Event('begin_comfort',10,token='a',appearance=Appearance(3500,.2)))
    assert reduce(comfort,Event('tick',30)).preview is None


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,True])
def test_invalid_elapsed_clock_rejected(bad):
    with pytest.raises(ValueError):reduce(ControlState(),Event('tick',bad))


def test_snapshot_contains_only_typed_state_not_config_secrets():
    snapshot=ControlState().snapshot('session-1',1)
    assert snapshot['protocol_version']==2
    assert snapshot['mode']=='off' and snapshot['generation']==0
    assert 'ipc_token' not in snapshot and 'smart_nights' not in snapshot
    with pytest.raises(ValueError):ControlState().snapshot('',1)
    with pytest.raises(ValueError):ControlState().snapshot('session-1',True)


def test_state_is_immutable_and_unknown_event_rejected():
    state=ControlState()
    with pytest.raises(dataclasses.FrozenInstanceError):state.mode='smart'
    with pytest.raises(ValueError):reduce(state,Event('infer_bedtime',0))


def test_one_owner_cannot_commit_another_owners_ticket():
    first,second=ControlState(),ControlState()
    ticket=stage_save(first,settings(),0)
    with pytest.raises(ValueError,match='changed'):commit_saved(second,ticket,1)
    assert first.owner_id not in str(first.snapshot('public-session',1))


def test_duplicate_preview_request_does_not_extend_watchdog():
    state=reduce(ControlState(mode='manual'),Event('begin_compare',1,token='a'))
    assert reduce(state,Event('begin_compare',9,token='a'))==state
    with pytest.raises(ValueError,match='reused'):
        reduce(state,Event('begin_comfort',9,token='a',appearance=Appearance()))


def test_typed_settings_drive_dated_planner_without_legacy_inference():
    from datetime import date, timezone
    from smart_schedule import personal_plan
    chosen=settings(warmth_kelvin=3500,dim_fraction=.15)
    actual=chosen.plan(date(2026,9,9),timezone.utc)
    expected=personal_plan(date(2026,9,9),timezone.utc,'22:00','07:00',kelvin=3500,dim_fraction=.15)
    assert actual.occurrence_id==expected.occurrence_id
    assert actual.sample(actual.ready)==expected.sample(expected.ready)
    assert actual.source=='personal'


def test_output_observation_defaults_unknown_and_is_serialization_safe():
    value=OutputObservation().to_dict()
    assert value['provenance']=='unavailable' and not value['current_confirmed']
    written=OutputObservation(accepted_rgb=(1.,.7,.4),accepted_at=1.)
    assert written.to_dict()['provenance']=='write_ack'
    assert written.to_dict()['readback_rgb'] is None
    with pytest.raises(ValueError):OutputObservation(current_confirmed=True)
    with pytest.raises(ValueError):OutputObservation(accepted_rgb=(1.,float('nan'),.4))
    with pytest.raises(ValueError):OutputObservation(accepted_rgb=[1.,.7,.4])
