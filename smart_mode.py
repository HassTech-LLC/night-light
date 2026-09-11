"""Offline Solar Sync calculations and GUI-thread scheduling controller.

NOAA fractional-year approximation: gml.noaa.gov/grad/solcalc/solareqns.PDF.
Solar events are approximate, not medical or calibrated light measurements.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
import math
from smart_learning import TimingLearner, estimate, clock_minutes
from smart_migration import uses_v2

UTC = timezone.utc


def coordinates(latitude, longitude):
    lat, lon = float(latitude), float(longitude)
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError('Latitude must be -90..90; longitude -180..180.')
    return lat, lon


@lru_cache(maxsize=64)
def solar_event(day: date, latitude: float, longitude: float, rising: bool, zenith=90.833):
    """Return an aware UTC event, or None for polar day/night. East is positive."""
    lat, lon = coordinates(latitude, longitude)
    gamma = 2 * math.pi / (366 if day.year % 4 == 0 and (day.year % 100 != 0 or day.year % 400 == 0) else 365) * (day.timetuple().tm_yday - 1)
    eq = 229.18 * (.000075 + .001868*math.cos(gamma) - .032077*math.sin(gamma) - .014615*math.cos(2*gamma) - .040849*math.sin(2*gamma))
    dec = .006918 - .399912*math.cos(gamma) + .070257*math.sin(gamma) - .006758*math.cos(2*gamma) + .000907*math.sin(2*gamma) - .002697*math.cos(3*gamma) + .00148*math.sin(3*gamma)
    phi = math.radians(lat)
    denominator = math.cos(phi)*math.cos(dec)
    if abs(denominator) < 1e-12:
        return None
    cosine = (math.cos(math.radians(zenith))-math.sin(phi)*math.sin(dec))/denominator
    if not -1 <= cosine <= 1:
        return None
    angle = math.degrees(math.acos(cosine))
    minutes = 720 - 4*lon - eq + (-4*angle if rising else 4*angle)
    return datetime.combine(day, time(), UTC) + timedelta(minutes=minutes)


@dataclass(frozen=True)
class Target:
    kelvin: int
    brightness: float
    stage: str


def blend(a, b, fraction, stage):
    eased = .5 - .5*math.cos(math.pi*max(0, min(1, fraction)))
    return Target(round(a[0]+(b[0]-a[0])*eased), a[1]+(b[1]-a[1])*eased, stage)


def solar_target(now, latitude, longitude, profile='balanced', sleep_minute=None):
    """Pair actual UTC sunset/sunrise, including date-line and overnight cases."""
    if now.tzinfo is None:
        raise ValueError('An aware datetime is required.')
    now = now.astimezone(UTC)
    lat, lon = coordinates(latitude, longitude)
    events = []
    for offset in range(-2, 3):
        day = now.date()+timedelta(days=offset)
        sunset = solar_event(day, lat, lon, False)
        sunrise = solar_event(day, lat, lon, True)
        if sunset is not None:
            events.append((sunset, False))
        if sunrise is not None:
            events.append((sunrise, True))
    if not events:
        return Target(6500, 1, 'No solar events — choose Manual or another location')
    points = [(6500,1), (4800,.9), (3200,.65), (2200,.45), (1700,.3)]
    if profile == 'maximum':
        points = [(6500,1), (4200,.8), (2700,.5), (1700,.3), (1200,.2)]
    def night_at(instant, sunset):
        if sleep_minute is not None:
            local=sunset.astimezone()
            bedtime=local.replace(hour=sleep_minute//60,minute=sleep_minute%60,second=0,microsecond=0)
            if sleep_minute<720: bedtime+=timedelta(days=1)
            sunset=min(sunset,(bedtime-timedelta(hours=4)).astimezone(UTC))
        minutes = (instant-sunset).total_seconds()/60
        knots = [-60,0,60,180,240]
        stages = ['Dusk transition','Early evening','Late evening','Deep night']
        for i in range(4):
            if minutes <= knots[i+1]:
                return blend(points[i],points[i+1],(minutes-knots[i])/(knots[i+1]-knots[i]),stages[i])
        return Target(*points[-1], 'Deep night')
    # Morning recovery starts at civil dawn and ends at sunrise. At high latitudes
    # without civil dawn, use a clearly bounded one-hour recovery before sunrise.
    for sunrise, rising in sorted(events):
        if not rising:
            continue
        dawns = [solar_event(now.date()+timedelta(days=i), lat, lon, True, 96) for i in range(-2,3)]
        dawn = max((d for d in dawns if d and d < sunrise and sunrise-d < timedelta(hours=6)), default=sunrise-timedelta(hours=1))
        if dawn <= now < sunrise:
            previous = [event for event, rising in events if not rising and event < dawn]
            if not previous:
                return Target(6500,1,'No sunset — choose Manual')
            at_dawn = night_at(dawn, max(previous))
            return blend((at_dawn.kelvin,at_dawn.brightness), points[0], (now-dawn)/(sunrise-dawn), 'Morning recovery')
    def start_for(event):
        if sleep_minute is None:return event-timedelta(hours=1)
        local=event.astimezone()
        bedtime=local.replace(hour=sleep_minute//60,minute=sleep_minute%60,second=0,microsecond=0)
        if sleep_minute<720:bedtime+=timedelta(days=1)
        return min(event-timedelta(hours=1),(bedtime-timedelta(hours=5)).astimezone(UTC))
    sunsets = sorted(event for event, rising in events if not rising and start_for(event) <= now)
    if not sunsets:
        return Target(6500,1,'Daylight')
    sunset = sunsets[-1]
    following = [event for event, rising in events if rising and event > sunset]
    if following and now >= min(following):
        return Target(6500,1,'Daylight')
    if not following:
        return Target(6500,1,'No sunrise — choose Manual')
    return night_at(now, sunset)


def quiet_target(now,start,end,profile='balanced'):
    start,end=clock_minutes(start),clock_minutes(end)
    length=(end-start)%1440
    if length==0:raise ValueError('Quiet-hours start and end must differ.')
    local=now.astimezone()
    elapsed=(local.hour*60+local.minute+local.second/60-start)%1440
    if elapsed>=length:return Target(6500,1,'Quiet hours · daylight')
    deep=(1200,.2) if profile=='maximum' else (1700,.3)
    fade=min(60,length/2)
    if elapsed<fade:return blend((6500,1),deep,elapsed/fade,'Quiet hours · evening transition')
    if elapsed>length-fade:return blend(deep,(6500,1),(elapsed-length+fade)/fade,'Quiet hours · morning recovery')
    return Target(*deep,'Quiet hours · night')


class SmartController:
    """One scheduler; injected engine/config/clock keep tests off the display."""
    def __init__(self, engine, config, clock=lambda: datetime.now(UTC)):
        self.engine, self.config, self.clock = engine, config, clock
        self.status = 'Manual'
        self.last_tick = None
        self.rejoin = True
        self.blocked = False
        self.fade_until = 0
        self.learner=TimingLearner(config)
        self.learning_status='Learning off'
        self.last_guard=None

    @property
    def enabled(self):
        if uses_v2(self.config):return False
        return self.config.get('smart_enabled', False) is True

    def configure(self, latitude, longitude, profile='balanced'):
        lat, lon = coordinates(latitude, longitude)
        if profile not in ('balanced','maximum'):
            raise ValueError('Choose Balanced or Maximum.')
        self.config.set('smart_location', {'latitude':lat,'longitude':lon}, save_now=False)
        self.config.set('smart_profile', profile, save_now=False)
        self.config.set('smart_enabled', True, save_now=False)
        self.resume()

    def manual(self, reset=False):
        if reset:
            # The old-policy migration adapter keeps the same emergency-Off
            # guarantee: a settings lock/failure cannot delay neutral intent.
            self.engine.reset_to_neutral()
        self.config.set('smart_enabled', False)
        self.config.set('smart_hold_until', 0)
        self.status = 'Manual'
        if reset:
            self.config.set('enabled', False)

    def hold(self, pause=False):
        if not self.enabled:
            return
        self.config.set('smart_hold_until', self.clock().timestamp()+3600)
        self.config.set('smart_hold_kind', 'pause' if pause else 'adjustment')
        self.rejoin = True
        if pause:
            self.engine.set_state(enabled=False, smooth=True)
        self.status = 'Smart paused for 1 hour' if pause else 'Smart adjustment for 1 hour'

    def resume(self):
        self.config.set('smart_hold_until', 0)
        self.rejoin = True
        self.fade_until = 0
        self.tick()

    def tick(self):
        if uses_v2(self.config):
            self.status = 'New Smart policy selected; legacy scheduler stopped'
            return
        if getattr(self.config,'automatic_output_blocked',False):
            self.status = 'Smart unavailable — recovery settings could not be saved. Restart after repairing storage.'
            return
        if not self.enabled:
            self.status = 'Manual'
            return
        now = self.clock()
        stamp = now.timestamp()
        if self.last_tick is None or stamp-self.last_tick > 60 or stamp < self.last_tick:
            self.rejoin = True
            self.fade_until = 0
        self.last_tick = stamp
        if self.engine.is_suppressed_by_windows_nightlight:
            self.status = 'Smart paused — Windows Night Light on or unknown'
            self.blocked = True
            self.rejoin = True
            return
        if self.blocked:
            self.blocked = False
            self.fade_until = 0
        try:
            hold = float(self.config.get('smart_hold_until', 0))
            if not math.isfinite(hold) or hold > stamp+3600:
                hold = 0
            if stamp < hold:
                kind = self.config.get('smart_hold_kind','adjustment')
                if kind == 'pause' and self.engine.is_enabled:
                    self.engine.set_state(enabled=False)
                self.status = f'Smart {kind} until {datetime.fromtimestamp(hold).strftime("%H:%M")}'
                return
            profile=self.config.get('smart_profile','balanced')
            window,confidence,count=estimate(self.config.get('smart_nights',[]) if isinstance(self.config.get('smart_nights',[]),list) else [])
            learning=self.config.get('smart_learning',False) is True
            self.learning_status=f'{confidence} confidence · {count}/14 usable nights' if learning else 'Learning off'
            if learning and window:
                self.learning_status+=f' · estimated sleep {window[0]//60:02d}:{window[0]%60:02d}, wake {window[1]//60:02d}:{window[1]%60:02d}'
            bedtime=self.config.get('smart_bedtime','')
            guard=clock_minutes(bedtime) if bedtime else (window[0] if learning and window else None)
            if guard!=self.last_guard:
                self.last_guard=guard;self.rejoin=True;self.fade_until=0
            location = self.config.get('smart_location')
            if isinstance(location,dict):
                target=solar_target(now,location['latitude'],location['longitude'],profile,guard)
            else:
                target=Target(6500,1,'No location')
            if target.stage.startswith('No '):
                quiet=self.config.get('smart_quiet_hours')
                if isinstance(quiet,dict):
                    target=quiet_target(now,quiet['start'],quiet['end'],profile)
                elif learning and window:
                    start=(window[0]-240)%1440;end=window[1]
                    target=quiet_target(now,f'{start//60:02d}:{start%60:02d}',f'{end//60:02d}:{end%60:02d}',profile)
                else:
                    raise ValueError('Solar events unavailable. Set quiet hours or use Manual.')
            mode='Adaptive Solar' if learning and window else 'Solar Sync'
            self.status = f'{mode} · {target.stage} · {target.kelvin} K / {round(target.brightness*100)}% brightness'
            if stamp < self.fade_until:
                return
            duration = (1200 if guard is not None else 120) if self.rejoin else 25
            self.engine.set_state(enabled=True, temperature_k=target.kelvin, brightness=target.brightness, smooth=True, duration=duration)
            self.fade_until = stamp+duration
            self.rejoin = False
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            self.status = f'Smart needs setup: {error}'
            self.engine.set_state(enabled=False, smooth=True)
