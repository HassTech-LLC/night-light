from datetime import date
from zoneinfo import ZoneInfo
import socket

from smart_schedule import solar_plan, personal_plan
from smart_time import system_zone
from smart_location import lookup_postal


def test_proxy_and_vpn_environment_cannot_relocate_saved_solar_schedule(monkeypatch):
    args=(date(2026,9,9),ZoneInfo('America/Detroit'),42.3353,-83.2864)
    before=solar_plan(*args)
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY'):
        monkeypatch.setenv(name,'http://127.0.0.1:9')
    monkeypatch.setenv('TZ','Asia/Tokyo')
    monkeypatch.setattr(socket,'create_connection',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Scheduler attempted network access')))
    after=solar_plan(*args)
    assert before.ready==after.ready and before.neutral==after.neutral
    assert before.sample(before.ready)==after.sample(after.ready)
    assert personal_plan(date(2026,9,9),ZoneInfo('America/Detroit'),'21:00','07:00').source=='personal'


def test_system_zone_ignores_process_tz_override(monkeypatch):
    monkeypatch.delenv('TZ',raising=False)
    before=system_zone()
    alternative='Asia/Tokyo' if str(before)!='Asia/Tokyo' else 'America/New_York'
    monkeypatch.setenv('TZ',alternative)
    assert system_zone()==before


def test_postal_lookup_uses_entered_area_and_never_ip_fallback():
    requests=[]
    def blocked(request,timeout):
        requests.append(request.full_url)
        raise OSError('VPN/network unavailable')
    try:lookup_postal('US','48127',opener=blocked)
    except OSError:pass
    assert requests==['https://api.zippopotam.us/us/48127']
