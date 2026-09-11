from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest

from smart_schedule import personal_plan, solar_plan, ScheduleUnavailable

UTC=timezone.utc


def test_personal_schedule_independent_channels_and_neutral_end():
    plan=personal_plan(date(2026,9,9),ZoneInfo('America/Detroit'),'21:00','07:00',kelvin=3500,dim_fraction=0)
    assert plan.ready.astimezone(ZoneInfo('America/Detroit')).hour==21
    assert plan.sample(plan.ready).kelvin==pytest.approx(3500)
    assert plan.sample(plan.ready).brightness==1
    assert plan.sample(plan.neutral).kelvin==6500
    assert plan.sample(plan.neutral).brightness==1
    assert plan.warmth.start<plan.ready
    assert plan.dim.peak==0


def test_short_night_reduces_each_peak_and_never_extends_past_morning():
    plan=personal_plan(date(2026,9,9),ZoneInfo('UTC'),'23:50','00:10',kelvin=1200,dim_fraction=.8)
    assert 0<plan.warmth.peak<1
    assert 0<plan.dim.peak<plan.warmth.peak
    assert plan.reduced_peak
    for channel in (plan.warmth,plan.dim):
        for i in range(1001):
            now=channel.start+(plan.neutral-channel.start)*i/1000
            sample=channel.sample(now)
            assert -1e-12<=sample.position<=channel.peak+1e-12
            assert abs(sample.velocity)<=channel.policy.rate*(1+1e-9)
            assert abs(sample.acceleration)<=channel.policy.acceleration*(1+1e-9)
        assert channel.sample(plan.neutral).position==0


def test_personal_dst_gap_is_disclosed_and_uses_real_instants():
    plan=personal_plan(date(2026,3,7),ZoneInfo('America/New_York'),'21:00','02:30')
    assert plan.neutral==datetime(2026,3,8,7,30,tzinfo=UTC)
    assert 'gap-forward' in plan.time_resolution


def test_equal_times_rejected():
    with pytest.raises(ValueError):personal_plan(date(2026,1,1),ZoneInfo('UTC'),'21:00','21:00')


def test_solar_dearborn_is_offline_and_returns_at_real_sunrise():
    from smart_mode import solar_event
    plan=solar_plan(date(2026,9,9),ZoneInfo('America/Detroit'),42.3353,-83.2864)
    assert plan.ready==solar_event(date(2026,9,9),42.3353,-83.2864,False)+timedelta(hours=1)
    assert plan.neutral==solar_event(date(2026,9,10),42.3353,-83.2864,True)
    assert plan.source=='solar'


def test_polar_events_require_explicit_fallback():
    with pytest.raises(ScheduleUnavailable):solar_plan(date(2026,6,21),ZoneInfo('UTC'),89,0)
    plan=solar_plan(date(2026,6,21),ZoneInfo('UTC'),89,0,fallback=('21:00','07:00'))
    assert plan.source=='explicit-fallback'


def test_same_utc_instant_same_output_regardless_display_zone():
    plan=personal_plan(date(2026,9,9),ZoneInfo('America/Detroit'),'21:00','07:00')
    now=plan.ready-timedelta(minutes=45)
    assert plan.sample(now)==plan.sample(now.astimezone(ZoneInfo('Asia/Kathmandu')))
