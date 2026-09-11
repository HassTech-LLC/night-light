from datetime import datetime,timedelta,timezone
import io
import json
import pytest
from smart_learning import estimate,TimingLearner,clock_minutes
from smart_location import lookup_postal
from smart_mode import solar_target,quiet_target
from test_smart_mode import Config,controller


def nights(count):return [{'date':str(i),'sleep':1380+i%3*5,'wake':420} for i in range(count)]

def test_confidence_and_midnight_wrap():
    assert estimate(nights(6))[0] is None
    assert estimate(nights(7))[1]=='Medium'
    assert estimate(nights(14))[1]=='High'
    entries=[{'sleep':1430 if i%2 else 10,'wake':420} for i in range(14)]
    assert estimate(entries)[0][0] in (0,1430,10)

def test_outlier_and_malformed_data():
    sample=nights(13)+[{'sleep':600,'wake':420}]
    assert estimate(sample)[0][0]>=1380
    assert estimate([{},None,{'sleep':'bad','wake':1}])[0] is None

def test_learning_opt_in_retention_and_reset():
    config=Config();learner=TimingLearner(config)
    now=datetime(2026,9,1,23,tzinfo=timezone.utc)
    learner.observe(now,3600);assert learner.last_active is None
    config.set('smart_learning',True)
    for i in range(20):learner.record(now+timedelta(days=i),now+timedelta(days=i,hours=8))
    assert len(config.get('smart_nights'))==14
    assert set(config.get('smart_nights')[0])=={'date','sleep','wake'}
    learner.reset();assert config.get('smart_nights')==[]

def test_idle_requires_sustained_return():
    config=Config();config.set('smart_learning',True);learner=TimingLearner(config)
    now=datetime.now().astimezone()
    learner.observe(now,8*3600);learner.observe(now+timedelta(seconds=25),0)
    assert not config.get('smart_nights')
    learner.observe(now+timedelta(seconds=210),0)
    assert len(config.get('smart_nights'))==1

def test_postal_request_and_choices():
    seen=[]
    def opener(request,timeout):
        seen.append((request.full_url,timeout))
        return io.BytesIO(json.dumps({'places':[{'latitude':'40.7','longitude':'-74','place name':'City'}]}).encode())
    result=lookup_postal('US','10001',opener)
    assert result==[{'latitude':40.7,'longitude':-74.,'label':'City'}]
    assert seen==[('https://api.zippopotam.us/us/10001',10)]
    with pytest.raises(ValueError):lookup_postal('../','bad',opener)

def test_postal_limits():
    with pytest.raises(ValueError):lookup_postal('US','10001',lambda *a,**k:io.BytesIO(b'x'*65537))
    with pytest.raises(ValueError):lookup_postal('US','10001',lambda *a,**k:io.BytesIO(b'{"places":[]}'))

def test_quiet_hours_cross_midnight():
    now=datetime.now().astimezone().replace(hour=23,minute=0,second=0)
    assert quiet_target(now,'20:00','07:00').kelvin==1700
    assert quiet_target(now.replace(hour=12),'20:00','07:00').kelvin==6500
    with pytest.raises(ValueError):quiet_target(now,'07:00','07:00')

def test_guard_never_weakens_solar_output():
    start=datetime(2026,9,9,tzinfo=timezone.utc)
    for i in range(96):
        now=start+timedelta(minutes=15*i)
        original=solar_target(now,40.7,-74)
        adapted=solar_target(now,40.7,-74,sleep_minute=22*60)
        assert adapted.kelvin<=original.kelvin
        assert adapted.brightness<=original.brightness+1e-9

def test_fallback_and_adaptive_controller():
    c,e,config,now=controller();config.set('smart_location',None)
    config.set('smart_quiet_hours',{'start':'20:00','end':'07:00'});c.resume()
    assert 'Quiet hours' in c.status
    config.set('smart_learning',True);config.set('smart_nights',nights(14));c.resume()
    assert 'Adaptive Solar' in c.status and 'High' in c.learning_status
    assert e.calls[-1]['duration']==1200

def test_hotkey_dispatch_only_calls_on_poll():
    import threading
    from smart_windows import EmergencyHotkey
    hotkey=EmergencyHotkey.__new__(EmergencyHotkey);hotkey.fired=threading.Event()
    calls=[];hotkey.callback=lambda:calls.append(True)
    hotkey.fired.set();assert calls==[]
    hotkey.poll();hotkey.poll();assert calls==[True]

def test_native_setup_tabs_construct_without_network(tk_root):
    from tkinter import ttk
    from smart_ui import show_smart_setup
    root=tk_root;window=None
    try:
        c,e,config,now=controller()
        window=show_smart_setup(root,c);window.withdraw();root.update_idletasks()
        book=next(w for w in window.winfo_children() if isinstance(w,ttk.Notebook))
        assert [book.tab(tab,'text') for tab in book.tabs()]==['Location','Schedule','Learning','Guide']
    finally:
        if window:window.destroy()

def test_real_hotkey_thread_message_lifecycle_without_display():
    import ctypes
    import time
    from smart_windows import EmergencyHotkey
    calls=[];hotkey=EmergencyHotkey(lambda:calls.append(True))
    try:
        if not hotkey.active:pytest.skip('Shortcut already registered by another application')
        assert ctypes.windll.user32.PostThreadMessageW(hotkey.thread_id,0x0312,0x484e,0)
        for _ in range(100):
            hotkey.poll()
            if calls:break
            time.sleep(.01)
        assert calls==[True]
    finally:hotkey.close()
    assert not hotkey.active and not hotkey.thread.is_alive()
