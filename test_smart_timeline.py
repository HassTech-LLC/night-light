from datetime import datetime,timezone
from types import SimpleNamespace
from dataclasses import replace
from zoneinfo import ZoneInfo
from test_smart_restart import saved
from test_smart_desktop import controller


def test_timeline_uses_the_output_planner_and_carries_real_dates(saved):
    smart=controller(saved)
    try:
        clock=smart.owner.clock;sample=clock.sample()
        plan=smart.owner.state.settings.plan(sample.utc.date(),sample.zone)
        result=smart.timeline()
        assert result['start_utc']==min(plan.warmth.start,plan.dim.start).isoformat()
        assert result['ready_utc']==plan.ready.isoformat()
        assert result['neutral_utc']==plan.neutral.isoformat()
        assert 'not a catch-up estimate' in result['note']
    finally:smart.close()


def test_daylight_shows_upcoming_night_not_yesterdays_expired_schedule(saved):
    smart=controller(saved)
    try:
        smart.owner.clock.utc=datetime(2026,9,10,8,tzinfo=timezone.utc)
        result=smart.timeline()
        assert result['ready_utc'].startswith('2026-09-10T22:00')
        assert result['neutral_utc'].startswith('2026-09-11T07:00')
    finally:smart.close()


def test_clock_failure_reports_unavailable_not_stale_timeline(saved,monkeypatch):
    smart=controller(saved)
    try:
        assert smart.timeline()['ready_utc']
        monkeypatch.setattr(smart.owner.clock,'sample',lambda:(_ for _ in ()).throw(OSError('zone failed')))
        result=smart.timeline()
        assert 'ready_utc' not in result and result['available'] is False
    finally:smart.close()


def test_premium_snapshot_includes_current_planned_timeline(saved):
    from premium_ui import PremiumActions
    smart=controller(saved)
    try:
        actions=PremiumActions(SimpleNamespace(smart=smart),smart.owner.engine,saved)
        assert actions.snapshot()['times']['ready_utc']==smart.timeline()['ready_utc']
    finally:smart.close()


def test_timeline_exposes_first_fold_occurrence_in_windows_zone(saved):
    from smart_time import ClockSource
    smart=controller(saved)
    try:
        smart.owner.clock=ClockSource(utc=lambda:datetime(2026,11,1,5,tzinfo=timezone.utc),
            active=lambda:100.,elapsed=lambda:100.,zone=lambda:ZoneInfo('America/Detroit'))
        smart.owner.state=replace(smart.owner.state,settings=replace(smart.owner.state.settings,evening_ready='01:30'))
        result=smart.timeline()
        assert result['ready_utc']=='2026-11-01T05:30:00+00:00'
        assert 'fold-first' in result['time_resolution']
        assert result['timezone']=='America/Detroit'
    finally:smart.close()


def test_polar_fallback_is_labelled_not_presented_as_actual_sunset(saved):
    from smart_state import SmartSettings
    smart=controller(saved)
    try:
        smart.owner.clock.utc=datetime(2026,6,21,12,tzinfo=timezone.utc)
        smart.owner.state=replace(smart.owner.state,settings=SmartSettings(kind='solar',latitude=85,longitude=0,
            fallback_ready='22:00',fallback_neutral='07:00'))
        result=smart.timeline()
        assert result['kind']=='Your fallback schedule'
        assert result['ready_utc'].startswith('2026-06-21T22:00')
    finally:smart.close()
