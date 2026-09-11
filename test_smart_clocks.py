from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from smart_time import ClockSource, resolve_civil, restored_pause_remaining


def test_missing_hour_moves_forward_by_gap():
    result=resolve_civil(date(2026,3,8),'02:30',ZoneInfo('America/New_York'))
    assert result.local.hour==3 and result.local.minute==30
    assert result.resolution=='gap-forward'
    assert result.utc==datetime(2026,3,8,7,30,tzinfo=timezone.utc)


def test_repeated_hour_uses_first_occurrence_and_stable_identity():
    args=(date(2026,11,1),'01:30',ZoneInfo('America/New_York'))
    result=resolve_civil(*args)
    assert result.utc==datetime(2026,11,1,5,30,tzinfo=timezone.utc)
    assert result.resolution=='fold-first'
    assert result.occurrence_id==resolve_civil(*args).occurrence_id


@pytest.mark.parametrize('name',['Asia/Kathmandu','Australia/Eucla','Pacific/Chatham','America/Detroit','UTC'])
def test_fractional_and_ordinary_zones_roundtrip(name):
    result=resolve_civil(date(2026,7,1),'19:17',ZoneInfo(name))
    assert result.utc.astimezone(ZoneInfo(name))==result.local
    assert result.local.hour==19 and result.local.minute==17


def test_clocks_are_independent_across_sleep_and_wall_correction():
    counters={'active':10,'elapsed':10,'utc':datetime(2026,1,1,tzinfo=timezone.utc)}
    source=ClockSource(utc=lambda:counters['utc'],active=lambda:counters['active'],
                       elapsed=lambda:counters['elapsed'],zone=lambda:ZoneInfo('UTC'))
    first=source.sample()
    counters['elapsed']+=3600
    second=source.sample()
    assert second.active_seconds==first.active_seconds
    assert second.elapsed_seconds-first.elapsed_seconds==3600


def test_restart_pause_is_bounded_and_clock_rollback_expires():
    assert restored_pause_remaining(start=100,expiry=3700,last_seen=200,now=400,duration=3600)==3300
    assert restored_pause_remaining(start=100,expiry=3700,last_seen=200,now=150,duration=3600)==0
    assert restored_pause_remaining(start=100,expiry=3700,last_seen=200,now=4000,duration=3600)==0


@pytest.mark.parametrize('bad',['25:00','2:30','12:60','',None])
def test_bad_civil_times_rejected(bad):
    with pytest.raises(ValueError):resolve_civil(date(2026,1,1),bad,ZoneInfo('UTC'))


def test_windows_clock_exports_and_packaged_database():
    import os
    from zoneinfo import available_timezones
    if os.name!='nt':pytest.skip('Windows-only read-only clock adapter')
    source=ClockSource()
    first,second=source.sample(),source.sample()
    assert second.active_seconds>=first.active_seconds>0
    assert second.elapsed_seconds>=first.elapsed_seconds>0
    assert len(available_timezones())>=500
