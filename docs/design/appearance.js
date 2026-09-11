/* Local-only appearance preferences. No native/display integration. */
(() => {
  "use strict";
  const find = selector => document.querySelector(selector);
  const app = find('.flyout');
  const storageKey = 'night-light-concept-appearance-v1';
  const presets = {
    signature: { name:'Night Light', dark:['#f3ad3d','#191c22'], light:['#995b16','#f7f3ea'] },
    amber: { name:'Amber', dark:['#e6b16a','#70451c'], light:['#995b16','#efb75d'] },
    ocean: { name:'Ocean', dark:['#8acaff','#184e78'], light:['#2167a2','#70b5e8'] },
    sage: { name:'Sage', dark:['#a9d3b4','#315c40'], light:['#356947','#8cbe92'] },
    lavender: { name:'Lavender', dark:['#c9b4f5','#583c7a'], light:['#75539e','#b49ade'] },
    rose: { name:'Rose', dark:['#f0afbb','#78334d'], light:['#a3425a','#e99bb1'] },
    graphite: { name:'Graphite', dark:['#d4d9df','#353e4c'], light:['#4c5661','#a5afbe'] },
    mocha: { name:'Mocha', dark:['#e4bd96','#44352f'], light:['#78452f','#d5b69d'] },
    midnight: { name:'Midnight', dark:['#97baff','#19243d'], light:['#294f99','#a5badc'] },
    jade: { name:'Jade', dark:['#8cdbc5','#193f38'], light:['#145d4d','#98c9b9'] },
    cloud: { name:'Cloud', dark:['#c1ccd9','#303640'], light:['#536679','#e7e4dc'] }
  };
  const materials = {
    liquid:'Liquid: translucent panel, luminous control surfaces, pill-shaped actions and a softly lit backdrop. CSS glass, not native Apple rendering.',
    frosted:'Frosted: a diffused panel, satin controls and restrained depth throughout. Recommended for everyday readability.',
    solid:'Solid: opaque surfaces, flat controls and crisp geometry throughout. No blur or decorative backdrop.',
    ceramic:'Ceramic: an opaque sculpted panel, recessed controls and soft raised buttons. No backdrop blur.'
  };
  const presetBackgrounds = {
    signature:['#101217','#e8ebef'],
    amber:['#462c16','#d9a247'], ocean:['#12344f','#559bd0'],
    sage:['#203e2b','#70a77a'], lavender:['#39284f','#987bc8'],
    rose:['#4f2536','#ce7e99'], graphite:['#242c38','#8995a7'],
    mocha:['#251c19','#ac8973'], midnight:['#0c1426','#718db8'],
    jade:['#0d2924','#679f8e'], cloud:['#181e27','#b9c1c9']
  };
  const defaults = theme => ({
    preset:'signature',
    accent:presets.signature[theme][0],
    surface:presets.signature[theme][1],
    background:presetBackgrounds.signature[theme==='dark'?0:1],
    material:theme==='dark'?'frosted':'ceramic'
  });
  const preferences = {theme:'dark',motion:true,dark:defaults('dark'),light:defaults('light')};
  const individualButtons = [];
  const presetColor = (id,key,theme) => key==='background' ? presetBackgrounds[id][theme==='dark'?0:1] : presets[id][theme][key==='accent'?0:1];
  const isHex = value => typeof value === 'string' && /^#[0-9a-f]{6}$/i.test(value);
  let canSave = true;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (saved && typeof saved === 'object') {
      if (saved.theme === 'dark' || saved.theme === 'light') preferences.theme = saved.theme;
      if (typeof saved.motion === 'boolean') preferences.motion = saved.motion;
      for (const theme of ['dark','light']) {
        const entry = saved[theme];
        if (!entry || !isHex(entry.accent) || !isHex(entry.surface)) continue;
        preferences[theme] = {accent:entry.accent,surface:entry.surface,background:isHex(entry.background) ? entry.background : '#f3f1ec',
          preset:Object.hasOwn(presets,entry.preset) ? entry.preset : 'custom',
          material:Object.hasOwn(materials,entry.material) ? entry.material : 'liquid'};
      }
      const legacyDark={preset:'custom',accent:'#a5c9f5',surface:'#202d40',background:'#101a29',material:'liquid'};
      const legacyLight={preset:'custom',accent:'#295b87',surface:'#e8eef5',background:'#cad9e9',material:'liquid'};
      const exact=(actual,expected)=>Object.keys(expected).every(key=>actual?.[key]===expected[key]);
      if(exact(preferences.dark,legacyDark)&&exact(preferences.light,legacyLight)){
        preferences.dark=defaults('dark');preferences.light=defaults('light');
        localStorage.setItem(storageKey,JSON.stringify(preferences));
      }
    }
  } catch { /* Corrupt or inaccessible preferences never block the demo. */ }
  const rgb = hex => [1,3,5].map(index => parseInt(hex.slice(index,index+2),16));
  const hex = values => '#' + values.map(value => Math.round(value).toString(16).padStart(2,'0')).join('');
  const mix = (a,b,amount) => hex(rgb(a).map((value,index) => value*(1-amount)+rgb(b)[index]*amount));
  const luminance = color => rgb(color).map(value => {
    const channel=value/255; return channel<=.04045 ? channel/12.92 : ((channel+.055)/1.055)**2.4;
  }).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
  const contrast = (a,b) => (Math.max(luminance(a),luminance(b))+.05)/(Math.min(luminance(a),luminance(b))+.05);
  const foreground = surface => contrast('#ffffff',surface)>contrast('#000000',surface) ? '#ffffff' : '#000000';
  function readableAccent(accent,backgrounds,text) {
    for(let step=0;step<=100;step++) {
      const candidate=mix(accent,text,step/100);
      if(backgrounds.every(surface=>contrast(candidate,surface)>=4.5)) return candidate;
    }
    return text;
  }
  function save() {
    try { localStorage.setItem(storageKey,JSON.stringify(preferences)); canSave=true; }
    catch { canSave=false; }
    find('#appearance-save').textContent = canSave
      ? 'Saved in this browser. Light and dark keep their own colors and finish.'
      : 'Browser storage is unavailable. Changes work here but will not survive a reload.';
  }
  function renderAppearance() {
    const theme=preferences.theme, selected=preferences[theme];
    app.dataset.theme=theme;
    app.dataset.standard=String(selected.preset==='signature');
    document.body.dataset.material=selected.material;
    document.body.dataset.motion=preferences.motion ? 'gentle' : 'still';
    const pageText=foreground(selected.background);
    document.body.style.setProperty('--page-background',selected.background);
    document.body.style.setProperty('--page-text',pageText);
    document.body.style.setProperty('--page-line',mix(selected.background,pageText,.35));
    document.body.style.setProperty('--page-control',mix(selected.background,pageText,.08));
    document.body.style.setProperty('--page-selected',mix(selected.background,pageText,.16));
    const text=foreground(selected.surface);
    // Bound contrast against either extreme of the wallpaper, not just the base tint.
    let alpha=.82;
    while(alpha<1 && ['#000000','#ffffff'].some(backdrop=>contrast(text,mix(backdrop,selected.surface,alpha))<4.5)) alpha=Math.min(1,alpha+.01);
    const backgrounds=['#000000','#ffffff'].map(backdrop=>mix(backdrop,selected.surface,alpha));
    const recess=text==='#ffffff' ? '#000000' : '#ffffff';
    const tokens={surface:selected.surface,text,accent:readableAccent(selected.accent,backgrounds,text),
      line:mix(selected.surface,text,.4),well:mix(selected.surface,recess,.12),selected:mix(selected.surface,recess,.24),
      glass:selected.surface+Math.ceil(alpha*255).toString(16).padStart(2,'0'),frost:selected.surface+'fc'};
    tokens['accent-text']=foreground(tokens.accent);
    for(const [name,value] of Object.entries(tokens)) app.style.setProperty('--palette-'+name,value);
    document.querySelectorAll('input[name="theme"]').forEach(input=>input.checked=input.value===theme);
    document.querySelectorAll('input[name="material"]').forEach(input=>input.checked=input.value===selected.material);
    find('#material-description').textContent=materials[selected.material];
    find('#palette-title').textContent=`Colors for ${theme === 'dark' ? 'night / dark' : 'light'} mode`;
    find('#accent-color').value=selected.accent;
    find('#surface-color').value=selected.surface;
    find('#background-color').value=selected.background;
    find('#gentle-motion').checked=preferences.motion;
    individualButtons.forEach(({button,id,key})=>{
      const color=presetColor(id,key,theme);
      button.style.setProperty('--color-chip',color);
      button.style.setProperty('--color-chip-text',foreground(color));
      button.setAttribute('aria-pressed',String(selected[key].toLowerCase()===color));
    });
    document.querySelectorAll('.palette-choice').forEach(button=>{
      button.setAttribute('aria-pressed',String(button.dataset.palette===selected.preset));
      button.style.setProperty('--swatch',presets[button.dataset.palette][theme][0]);
      button.style.setProperty('--swatch-panel',presets[button.dataset.palette][theme][1]);
      button.style.setProperty('--swatch-background',presetBackgrounds[button.dataset.palette][theme==='dark'?0:1]);
    });
  }
  for(const [id,preset] of Object.entries(presets)) {
    const button=document.createElement('button');
    button.type='button'; button.className='palette-choice'; button.dataset.palette=id;
    button.setAttribute('aria-pressed','false');
    const swatch=document.createElement('span'); swatch.className='palette-swatch'; swatch.setAttribute('aria-hidden','true');
    button.append(swatch,document.createTextNode(preset.name));
    button.addEventListener('click',()=>{
      Object.assign(preferences[preferences.theme],{preset:id,accent:preset[preferences.theme][0],surface:preset[preferences.theme][1],background:presetBackgrounds[id][preferences.theme==='dark'?0:1]});
      renderAppearance(); save();
    });
    find('.palette-grid').append(button);
  }
  document.querySelectorAll('input[name="theme"]').forEach(input=>input.addEventListener('change',()=>{
    preferences.theme=input.value; renderAppearance(); save();
  }));
  document.querySelectorAll('input[name="material"]').forEach(input=>input.addEventListener('change',()=>{
    preferences[preferences.theme].material=input.value; renderAppearance(); save();
  }));
  for(const key of ['accent','surface','background']) {
    for(const [id,preset] of Object.entries(presets)) {
      const button=document.createElement('button');
      button.type='button';button.className='individual-preset';button.append(document.createTextNode(preset.name));
      button.setAttribute('aria-label',`${preset.name} ${key==='surface'?'panel':key==='background'?'background':'accent'}`);
      button.addEventListener('click',()=>{
        Object.assign(preferences[preferences.theme],{preset:'custom',[key]:presetColor(id,key,preferences.theme)});
        renderAppearance();save();
      });
      individualButtons.push({button,id,key});
      find('#'+key+'-presets').append(button);
    }
    find('#'+key+'-color').addEventListener('input',event=>{
      if(!isHex(event.target.value)) return;
      Object.assign(preferences[preferences.theme],{preset:'custom',[key]:event.target.value}); renderAppearance();
    });
    find('#'+key+'-color').addEventListener('change',save);
  }
  find('#gentle-motion').addEventListener('change',event=>{preferences.motion=event.target.checked;renderAppearance();save();});
  find('#reset-appearance').addEventListener('click',()=>{preferences[preferences.theme]=defaults(preferences.theme);renderAppearance();save();});
  renderAppearance();
})();
