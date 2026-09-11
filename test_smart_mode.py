from datetime import datetime, date, timedelta, timezone
import math
import pytest
from smart_mode import solar_event, solar_target, coordinates, SmartController

UTC = timezone.utc

def test_noaa_equatorial_equinox_vector():
    day = date(2026,3,20)
    rise = solar_event(day,0,0,True)
    setting = solar_event(day,0,0,False)
    assert abs((rise-datetime(2026,3,20,6,4,tzinfo=UTC)).total_seconds()) < 300
    assert abs((setting-datetime(2026,3,20,18,11,tzinfo=UTC)).total_seconds()) < 300

@pytest.mark.parametrize('lat,lon',[(float('nan'),0),(0,float('inf')),(91,0),(0,-181)])
def test_invalid_location(lat,lon):
    with pytest.raises(ValueError): coordinates(lat,lon)

def test_night_knots_and_daylight():
    day=date(2026,9,9)
    sunset=solar_event(day,40.7,-74,False)
    assert solar_target(sunset,40.7,-74).kelvin == 4800
    assert solar_target(sunset+timedelta(hours=4),40.7,-74).kelvin == 1700
    assert solar_target(sunset+timedelta(hours=4),40.7,-74,'maximum').brightness == .2
    sunrise=solar_event(day+timedelta(days=1),40.7,-74,True)
    assert solar_target(sunrise+timedelta(seconds=1),40.7,-74).kelvin == 6500

def test_polar_no_invented_events():
    assert solar_event(date(2026,6,21),89,0,True) is None
    target=solar_target(datetime(2026,6,21,tzinfo=UTC),89,0)
    assert target.kelvin == 6500
    assert 'No solar' in target.stage

def test_timezone_equivalent_instant():
    now=datetime(2026,9,10,2,tzinfo=UTC)
    assert solar_target(now,40.7,-74) == solar_target(now.astimezone(timezone(timedelta(hours=-4))),40.7,-74)

class Config:
    def __init__(self): self.data={}
    def get(self,k,d=None): return self.data.get(k,d)
    def set(self,k,v,save_now=True): self.data[k]=v

class Engine:
    is_suppressed_by_windows_nightlight=False
    is_enabled=False
    def __init__(self): self.calls=[]
    def set_state(self,**kwargs):
        self.calls.append(kwargs)
        self.is_enabled=kwargs.get('enabled',self.is_enabled)
    def reset_to_neutral(self): self.is_enabled=False

def controller():
    now=[datetime(2026,9,10,2,tzinfo=UTC)]
    config=Config(); engine=Engine()
    control=SmartController(engine,config,lambda:now[0])
    control.configure(40.7,-74)
    return control,engine,config,now

def test_pause_expiry_and_catchup():
    c,e,config,now=controller()
    assert e.calls[-1]['duration']==120
    c.hold(pause=True); assert not e.is_enabled
    now[0]+=timedelta(minutes=30); c.tick(); assert not e.is_enabled
    now[0]+=timedelta(minutes=31); c.tick(); assert e.is_enabled
    assert e.calls[-1]['duration']==120

def test_manual_adjustment_does_not_get_overwritten():
    c,e,config,now=controller(); c.hold()
    count=len(e.calls); now[0]+=timedelta(seconds=25); c.tick()
    assert len(e.calls)==count
    c.resume(); assert len(e.calls)>count

def test_windows_exclusion_and_rejoin():
    c,e,config,now=controller()
    e.is_suppressed_by_windows_nightlight=True
    count=len(e.calls); now[0]+=timedelta(seconds=25); c.tick()
    assert len(e.calls)==count
    assert 'Windows' in c.status
    e.is_suppressed_by_windows_nightlight=False
    now[0]+=timedelta(seconds=25); c.tick()
    assert e.calls[-1]['duration']==120

def test_missing_location_neutral_and_manual_stops_timer():
    c,e,config,now=controller()
    config.set('smart_location',None); c.tick()
    assert not e.is_enabled and 'setup' in c.status
    c.manual(); count=len(e.calls); c.tick(); assert len(e.calls)==count

def test_no_restart_of_initial_fade():
    c,e,config,now=controller(); count=len(e.calls)
    now[0]+=timedelta(seconds=25); c.tick(); assert len(e.calls)==count

def test_short_night_morning_has_no_jump():
    lat,lon=59.9,10.7
    dawn=solar_event(date(2026,5,15),lat,lon,True,96)
    before=solar_target(dawn-timedelta(seconds=1),lat,lon)
    after=solar_target(dawn+timedelta(seconds=1),lat,lon)
    assert abs(before.kelvin-after.kelvin)<10
    assert abs(before.brightness-after.brightness)<.01

@pytest.mark.parametrize('lat,lon',[(40.7,-74),(-33.9,151.2),(51.5,-.1),(35.7,139.7)])
def test_two_day_curve_is_bounded(lat,lon):
    start=datetime(2026,9,9,tzinfo=UTC)
    for minute in range(0,2880,15):
        t=solar_target(start+timedelta(minutes=minute),lat,lon)
        assert 1200<=t.kelvin<=6500
        assert .2<=t.brightness<=1 and math.isfinite(t.brightness)
