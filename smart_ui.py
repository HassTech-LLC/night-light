"""Native Smart setup; postal lookup is explicit and learning is opt-in."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from smart_location import lookup_postal
from smart_learning import clock_minutes
from smart_mode import coordinates


def show_smart_setup(parent, controller):
    window=tk.Toplevel(parent);window.title('Smart Mode — Night Light by HT');window.geometry('510x650')
    book=ttk.Notebook(window);book.pack(fill='both',expand=True,padx=12,pady=12)
    tabs={}
    for name in ['Location','Schedule','Learning','Guide']:
        tabs[name]=ttk.Frame(book,padding=14);book.add(tabs[name],text=name)
    def label(box,text):ttk.Label(box,text=text,wraplength=450,justify='left').pack(anchor='w',pady=8)
    def entry(box,title,value=''):
        label(box,title);var=tk.StringVar(value=str(value));ttk.Entry(box,textvariable=var).pack(fill='x');return var
    status=tk.StringVar(value=controller.status)
    ttk.Label(window,textvariable=status,wraplength=480).pack(fill='x',padx=14,pady=6)
    location=controller.config.get('smart_location')
    if not isinstance(location,dict):location={}
    box=tabs['Location']
    label(box,'Lookup sends only country and postal code to Zippopotam.us when clicked. Solar calculations then run offline. Unsupported areas can enter city coordinates below.')
    country=entry(box,'Country code (US, CA, GB…)','US');postal=entry(box,'ZIP / postal code')
    lat=entry(box,'City latitude (north positive)',location.get('latitude',''));lon=entry(box,'City longitude (east positive)',location.get('longitude',''))
    choices=[];selection=tk.StringVar();selector=ttk.Combobox(box,textvariable=selection,state='readonly');selector.pack(fill='x',pady=8)
    def choose(event=None):
        i=selector.current()
        if 0<=i<len(choices):lat.set(str(choices[i]['latitude']));lon.set(str(choices[i]['longitude']))
    selector.bind('<<ComboboxSelected>>',choose)
    def lookup():
        c,p=country.get(),postal.get();button.configure(state='disabled');status.set('Looking up…');result=queue.Queue()
        def work():
            try:result.put((lookup_postal(c,p),None))
            except Exception:result.put((None,'Lookup failed. Check the code or enter coordinates.'))
        threading.Thread(target=work,daemon=True).start()
        def poll():
            if not window.winfo_exists():return
            try:data,error=result.get_nowait()
            except queue.Empty:window.after(100,poll);return
            button.configure(state='normal')
            if error:status.set(error);return
            choices[:]=data;selector.configure(values=[x['label'] for x in data]);selector.current(0);choose();status.set('Review the area, then Save and enable Smart.')
        window.after(100,poll)
    button=ttk.Button(box,text='Look up postal code online',command=lookup);button.pack(fill='x')
    def delete():
        controller.manual(reset=True);controller.config.set('smart_location',None);lat.set('');lon.set('');choices.clear();selection.set('');selector.configure(values=[]);status.set('Location deleted. Smart stopped; display neutral.')
    ttk.Button(box,text='Delete location and stop Smart',command=delete).pack(fill='x',pady=8)
    box=tabs['Schedule'];label(box,'Solar Sync starts near sunset; neutral colors return by sunrise. Balanced is recommended. Maximum reaches 1200 K / 20% brightness.')
    profile=tk.StringVar(value=controller.config.get('smart_profile','balanced'));ttk.Combobox(box,textvariable=profile,values=['balanced','maximum'],state='readonly').pack(fill='x')
    bedtime=entry(box,'Optional bedtime HH:MM',controller.config.get('smart_bedtime',''))
    label(box,'A bedtime or confident learned estimate moves the curve earlier, never later. Leave blank for sunset only.')
    quiet=controller.config.get('smart_quiet_hours');quiet=quiet if isinstance(quiet,dict) else {}
    start=entry(box,'Fallback quiet start HH:MM',quiet.get('start',''));end=entry(box,'Fallback neutral time HH:MM',quiet.get('end',''))
    label(box,'Fallback is used only when location or solar events are unavailable. These times follow the Windows local clock.')
    box=tabs['Learning'];learning=tk.BooleanVar(value=controller.config.get('smart_learning',False) is True)
    def toggle():
        controller.config.set('smart_learning',learning.get());controller.learner.last_active=controller.learner.pending=None;controller.rejoin=True;controller.fade_until=0;controller.tick();status.set('Local learning enabled; collecting consistent nights.' if learning.get() else 'Learning paused. Stored history retained until reset.')
    ttk.Checkbutton(box,text='Opt in to local activity-timing learning',variable=learning,command=toggle).pack(anchor='w')
    label(box,'Stores at most 14 daily timing pairs after a long idle period and sustained return to activity. No keys, apps, titles, screenshots or browsing are recorded. Timing never leaves this computer. Inactivity is only an estimate, not measured sleep.')
    label(box,'Seven consistent nights are required. Low confidence uses Solar Sync. Disable to pause collection; reset to delete history. Set bedtime in Schedule to override the estimate.')
    learning_status=tk.StringVar(value=controller.learning_status);ttk.Label(box,textvariable=learning_status,wraplength=440).pack(fill='x',pady=12)
    def reset():
        controller.learner.reset();controller.rejoin=True;controller.fade_until=0;controller.tick();learning_status.set(controller.learning_status);status.set('Learning history deleted.')
    ttk.Button(box,text='Reset / delete learning history',command=reset).pack(fill='x')
    def mark_sleep():
        if not learning.get():status.set('Enable local learning first.');return
        from datetime import datetime
        controller.learner.last_active=datetime.now().astimezone();controller.learner.pending=None
        status.set('Winding-down time noted locally for this session.')
    def mark_wake():
        if not learning.get() or controller.learner.last_active is None:status.set('No winding-down time available.');return
        from datetime import datetime
        controller.learner.record(controller.learner.last_active,datetime.now().astimezone())
        controller.learner.last_active=controller.learner.pending=None
        controller.tick();learning_status.set(controller.learning_status)
    ttk.Button(box,text='I am winding down',command=mark_sleep).pack(fill='x',pady=5)
    ttk.Button(box,text='I am awake',command=mark_wake).pack(fill='x',pady=5)
    box=tabs['Guide']
    label(box,'Pin for convenience: right-click the app in Start and choose Pin to taskbar (sometimes under More). The tray icon near the clock is separate from its taskbar shortcut.')
    label(box,'Left-click the tray icon or pinned shortcut to toggle. Right-click the tray icon to open controls. Smart setup reopens this guide.')
    label(box,'Warmth reduces blue output. Dimming changes software output, not monitor hardware brightness. Smart follows the evening curve; Manual keeps your settings.')
    label(box,'Manual adjustments hold for one hour. Pause returns original colors for one hour. Resume rejoins Smart. App Off / zero warmth stops automation until enabled again.')
    label(box,'Emergency reset: Ctrl+Alt+Shift+N restores neutral and stops Smart while the app runs. If unavailable, use App Off in the flyout or taskbar Jump List. It cannot recover a crashed app.')
    label(box,getattr(controller,'hotkey_status','Shortcut registration not checked in this session.'))
    label(box,'Windows Night Light on or unknown pauses this filter. No stacking. The app does not measure sleep or melatonin and is not medical treatment.')
    def save():
        try:
            if bedtime.get():clock_minutes(bedtime.get())
            quiet=None
            if start.get() or end.get():
                if clock_minutes(start.get())==clock_minutes(end.get()):raise ValueError('Quiet times must differ.')
                quiet={'start':start.get(),'end':end.get()}
            coords=coordinates(lat.get(),lon.get()) if lat.get() or lon.get() else None
            if coords is None and quiet is None:raise ValueError('Provide location or fallback quiet hours.')
            controller.config.set('smart_bedtime',bedtime.get(),save_now=False);controller.config.set('smart_quiet_hours',quiet,save_now=False);controller.config.set('smart_learning',learning.get(),save_now=False)
            if coords:controller.configure(*coords,profile.get())
            else:
                controller.config.set('smart_location',None,save_now=False);controller.config.set('smart_profile',profile.get(),save_now=False);controller.config.set('smart_enabled',True,save_now=False);controller.resume()
            status.set(controller.status);learning_status.set(controller.learning_status)
        except (ValueError,TypeError) as error:messagebox.showerror('Check settings',str(error),parent=window)
    ttk.Button(window,text='Save and enable Smart',command=save).pack(fill='x',padx=14,pady=12)
    window.bind('<Escape>',lambda event:window.destroy())
    return window
