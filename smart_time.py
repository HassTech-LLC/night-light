"""Explicit civil, UTC, active and sleep-inclusive clocks for Smart Comfort.

No display, registry writes, settings writes or network access on import.
Windows interrupt-time counters are independent of user wall-clock changes.
"""
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from functools import lru_cache
import ctypes
import math
import os
import re
from typing import Callable
from zoneinfo import ZoneInfo


UTC = timezone.utc


def utc_now():
    return datetime.now(UTC)


def system_zone():
    """Read the OS zone, ignoring TZ/proxy/IP-derived environment settings."""
    if os.name!='nt':
        raise RuntimeError('Inject a timezone resolver on non-Windows test hosts.')
    import winreg
    from tzlocal.windows_tz import win_tz
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                       r'SYSTEM\CurrentControlSet\Control\TimeZoneInformation',0,winreg.KEY_READ) as key:
        name=winreg.QueryValueEx(key,'TimeZoneKeyName')[0].split('\x00',1)[0]
        try:disabled=winreg.QueryValueEx(key,'DynamicDaylightTimeDisabled')[0]==1
        except FileNotFoundError:disabled=False
        if disabled:
            def signed_minutes(value_name):
                value=winreg.QueryValueEx(key,value_name)[0]
                return value-(1<<32) if value>=(1<<31) else value
            bias=signed_minutes('Bias')+signed_minutes('StandardBias')
            return timezone(timedelta(minutes=-bias),name+' (DST off)')
    identifier=win_tz.get(name) or win_tz.get(name+' Standard Time')
    if identifier is None:raise ValueError('Windows timezone is not supported by the packaged mapping.')
    return ZoneInfo(identifier)


@lru_cache(maxsize=2)
def _counter(include_sleep):
    if os.name != 'nt':
        raise RuntimeError('Inject clock adapters on non-Windows test hosts.')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    # GetTickCount64 is exported on supported Windows builds, including those
    # where QueryInterruptTime is only reachable through an API-set DLL.
    method = kernel.GetTickCount64 if include_sleep else kernel.QueryUnbiasedInterruptTime
    method.argtypes = [] if include_sleep else [ctypes.POINTER(ctypes.c_ulonglong)]
    method.restype = ctypes.c_ulonglong if include_sleep else ctypes.c_int
    return method


def _interrupt_seconds(include_sleep):
    method = _counter(include_sleep)
    if include_sleep:
        return method() / 1000
    value = ctypes.c_ulonglong()
    if not method(ctypes.byref(value)):
        raise OSError('Windows active-time clock unavailable.')
    return value.value / 10_000_000


def active_seconds():
    return _interrupt_seconds(False)


def elapsed_seconds():
    return _interrupt_seconds(True)


@dataclass(frozen=True)
class ClockSample:
    utc: datetime
    active_seconds: float
    elapsed_seconds: float
    zone: object


class ClockSource:
    def __init__(self, *, utc: Callable=utc_now, active: Callable=active_seconds,
                 elapsed: Callable=elapsed_seconds, zone: Callable=system_zone):
        self.utc, self.active, self.elapsed, self.zone = utc, active, elapsed, zone
        self._zone = None
        self._zone_checked = None

    def refresh_zone(self):
        self._zone = None

    def elapsed_now(self):
        """Safety deadlines do not depend on UTC, active time or zone lookup."""
        value=self.elapsed()
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            raise ValueError('Invalid elapsed clock sample.')
        return value

    def sample(self):
        now, active, elapsed = self.utc(), self.active(), self.elapsed_now()
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('UTC clock must be timezone-aware.')
        if not all(math.isfinite(v) and v>=0 for v in (active,elapsed)):
            raise ValueError('Invalid monotonic clock sample.')
        if self._zone is None or self._zone_checked is None or not 0<=elapsed-self._zone_checked<60:
            self._zone = self.zone()
            self._zone_checked = elapsed
        return ClockSample(now.astimezone(UTC),active,elapsed,self._zone)


@dataclass(frozen=True)
class CivilOccurrence:
    local: datetime
    utc: datetime
    resolution: str
    occurrence_id: str


def resolve_civil(day: date, clock: str, zone: ZoneInfo):
    """Resolve gaps forward by their size and folds to the first UTC instant."""
    if not isinstance(clock,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',clock):
        raise ValueError('Enter a time in HH:MM format.')
    hour,minute = map(int,clock.split(':'))
    naive = datetime(day.year,day.month,day.day,hour,minute)
    candidates = [naive.replace(tzinfo=zone,fold=fold).astimezone(UTC).astimezone(zone) for fold in (0,1)]
    valid = {candidate.astimezone(UTC):candidate for candidate in candidates if candidate.replace(tzinfo=None)==naive}
    if valid:
        instant = min(valid)
        local = valid[instant]
        resolution = 'fold-first' if len(valid)>1 else 'exact'
    else:
        forward = [candidate for candidate in candidates if candidate.replace(tzinfo=None)>naive]
        if not forward:
            raise ValueError('This local time cannot be resolved in the selected timezone.')
        local = min(forward,key=lambda candidate:candidate.astimezone(UTC))
        instant = local.astimezone(UTC)
        resolution = 'gap-forward'
    identity = f'{getattr(zone,"key",str(zone))}|{day.isoformat()}|{clock}|{instant.isoformat()}'
    return CivilOccurrence(local,instant,resolution,identity)


def restored_pause_remaining(*, start, expiry, last_seen, now, duration):
    """Clamp persisted elapsed holds; uncertain clock rollback expires safely."""
    values = (start,expiry,last_seen,now,duration)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):
        return 0.0
    if not 0<duration<=86400 or not start<=last_seen or now<last_seen or expiry<start:
        return 0.0
    return max(0.0,min(float(duration),expiry-now))
