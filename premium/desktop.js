/* No demo engine. Every display action is acknowledged by the native owner. */
(() => {
  'use strict';
  const $=s=>document.querySelector(s);
  const bridge=window.chrome?.webview;
  let current=null, hydrated=false, places=[], lastEdit=0, pending=null, debounce;
  let saveRequest=null, saveTimer, sequence=0, saveDraft=null, checking=false;
  let draftRevision=null, dirty=false, reloadRequested=false;
  let setupDismissed=false,setupRequested=false;
  let migrationEditing=false,migrationPrior=null;
  function readDraft() {
    if(current?.smart_settings||migrationEditing) return {settings:{...(current.smart_settings||{}),
      kind:$('#comfort-kind').value,evening_ready:$('#comfort-ready').value,morning_neutral:$('#comfort-neutral').value,
      warmth_kelvin:Number($('#comfort-warmth').value),dim_fraction:Number($('#comfort-dim').value)/100,
      warmth_lead:Number($('#comfort-warm-lead').value),dim_lead:Number($('#comfort-dim-lead').value),
      slower:Number($('#comfort-pace').value),solar_offset_minutes:Number($('#comfort-offset').value),
      latitude:$('#latitude').value===''?null:Number($('#latitude').value),
      longitude:$('#longitude').value===''?null:Number($('#longitude').value),
      fallback_ready:$('#quiet-start').value||null,fallback_neutral:$('#quiet-end').value||null}};
    return {latitude:$('#latitude').value,longitude:$('#longitude').value,profile:$('#profile').value,
      bedtime:$('#bedtime').value,start:$('#quiet-start').value,end:$('#quiet-end').value};
  }
  function matchesSaved(s,draft) {
    if(draft?.settings)return Object.entries(draft.settings).every(([k,v])=>s?.smart_settings?.[k]===v);
    if(!draft||!s?.settings)return false;
    const p=s.settings;
    const locationMatches=draft.latitude===''&&draft.longitude==='' ? p.location==null :
      p.location!=null&&Number(draft.latitude)===p.location.latitude&&Number(draft.longitude)===p.location.longitude;
    return locationMatches&&draft.profile===p.profile&&draft.bedtime===(p.bedtime||'')&&
      draft.start===(p.quiet?.start||'')&&draft.end===(p.quiet?.end||'');
  }
  function finishSave(text,success=false) {
    clearTimeout(saveTimer);saveRequest=null;checking=false;
    $('#save-smart').disabled=false;$('#smart-form').setAttribute('aria-busy','false');
    $('#save-smart').textContent=success?'Settings saved':'Save and enable Smart';
    $('#save-feedback').textContent=text;
    $('#check-save').hidden=true;$('#reload-saved').hidden=success;
    if(success){
      draftRevision=current?.config_revision;dirty=JSON.stringify(readDraft())!==JSON.stringify(saveDraft);
      if(dirty){$('#save-smart').textContent='Save and enable Smart';$('#save-feedback').textContent+=' Newer edits have not been saved.';}
    }
  }
  function checkSave() {
    checking=true;clearTimeout(saveTimer);
    $('#save-feedback').textContent='Save not yet confirmed. Checking…';
    saveTimer=setTimeout(()=>{
      finishSave("Couldn't confirm the save. Your edits are kept here.");
      $('#check-save').hidden=false;$('#reload-saved').hidden=false;
    },8000);
    send('state');
  }
  function feedback(text) { $('#feedback').textContent=text; }
  function savedStatus() {
    return 'Settings saved. '+(current.output_fault||current.blocked?
      'Display adjustment is unavailable. See the status above.':
      current.smart?'See the current Smart status above.':'Smart is currently off.');
  }
  function send(action,args={}) {
    if(!bridge) { feedback('Desktop connection unavailable. Open the installed Night Light app.'); return; }
    bridge.postMessage({action,protocol_version:2,...(current?{session_id:current.session_id}:{}),...args});
  }
  function field(id,value) { if(document.activeElement!==$(id)) $(id).value=value??''; }
  function render(s,local=false) {
    if(!local&&current?.session_id===s.session_id&&s.sequence<=current.sequence)return;
    if(Boolean(current?.smart_settings)!==Boolean(s.smart_settings))hydrated=false;
    current=s;
    const build=s.build_identity;
    $('#build-identity').textContent=build?.kind==='packaged'
      ?`${build.label} · Version ${build.version} · Build ${build.build_id}${build.dirty?' · Uncommitted source':''}`
      :build?.label||'Build identity unavailable. This view cannot confirm an installed release.';
    $('#first-run-guide').hidden=!(s.first_run||setupRequested)||setupDismissed;
    $('#reopen-setup').hidden=!s.smart_settings;
    $('#skip-setup').textContent=s.power?'Not now — keep current mode':'Not now — keep original colors';
    if(s.first_run&&!hydrated&&!setupDismissed)$('#first-run-guide').scrollIntoView?.({block:'start'});
    $('#comfort-settings').hidden=!(s.smart_settings||migrationEditing);
    $('#migration-begin').hidden=Boolean(s.smart_settings)||migrationEditing;
    $('#migration-preview').hidden=!migrationEditing;$('#migration-keep').hidden=!migrationEditing;
    $('#migration-switch').hidden=!(migrationEditing&&s.migration_review?.switch_available);
    $('#save-smart').hidden=migrationEditing;
    if(migrationEditing&&s.migration_review){
      const r=s.migration_review;
      $('#migration-summary').textContent=`Proposed schedule: starts ${r.start_label||r.start}, evening ready ${r.ready_label||r.ready}, neutral ${r.neutral_label||r.neutral}. Current mode (${r.preserved_mode}) and existing settings stay unchanged. New Smart stops routine learning. This is a schedule review, not a display preview.${r.switch_available?' Choose Use this Smart Comfort schedule to save a recovery copy and switch.':' Switching is unavailable until recovery storage is ready.'}`;
    }
    $('#restore-comfort').hidden=s.preview_kind!=='comfort';
    $('#comfort-preview-status').textContent=s.preview_kind==='comfort'?`Temporary preview: ${s.preview_remaining} seconds remaining. Your saved mode is unchanged.`:'';
    document.querySelectorAll('#profile,#bedtime').forEach(x=>x.parentElement.hidden=Boolean(s.smart_settings)||migrationEditing);
    document.querySelectorAll('#learning').forEach(x=>x.closest('details').hidden=Boolean(s.smart_settings));
    $('#legacy-timing-note').hidden=Boolean(s.smart_settings)||migrationEditing;
    $('#delete-location').hidden=Boolean(s.smart_settings)||migrationEditing;
    $('#preview-comfort').hidden=migrationEditing;
    $('#power').disabled=false;
    document.querySelectorAll('#warmth,#dimming,#compare,[name="mode"],#migration-preview,#migration-switch,#preview-comfort').forEach(x=>x.disabled=Boolean(s.migration_pending));
    $('#save-smart').disabled=Boolean(s.migration_pending||saveRequest);
    if(!dirty&&!saveRequest)draftRevision=s.config_revision;
    $('#status-meta').textContent=s.meta;
    $('#status-title').textContent=s.title;
    $('#status-copy').textContent=s.detail;
    $('#power').setAttribute('aria-checked',String(s.power));
    document.querySelectorAll('[name="mode"]').forEach(x=>x.checked=(x.value==='smart')===s.smart);
    if(Date.now()-lastEdit>400) {
      field('#warmth',Math.round((6500-s.kelvin)/50)); field('#dimming',Math.round((1-s.brightness)*100));
      sliderLabels();
      $('#warmth-value').value=s.kelvin.toLocaleString()+' K';
    }
    $('#pause').textContent=s.hold?'Resume Smart':'Pause 1 hour';
    $('#pause').classList.toggle('resume',s.hold);
    $('#pause').disabled=!s.smart||Boolean(s.migration_pending);
    $('#repair').hidden=!(s.blocked||s.output_fault);
    $('#repair').textContent=s.output_fault?'Display adjustment stopped. Check Quick guide & safety, then Retry display.':s.blocked?'Windows Night Light is on or its state is unknown. This filter is paused to prevent stacking. See Quick guide & safety.':'';
    $('#timeline').hidden=!s.smart||(Boolean(s.smart_settings)&&!s.times?.start);
    const times=s.times||{};
    $('.timeline-label:nth-child(1) span').textContent=s.smart_settings?'Starts':'Warm up';
    $('.timeline-label:nth-child(2) span').textContent=s.smart_settings?'Evening ready':'Late evening';
    $('#start-label').textContent=times.start||'—';
    $('.timeline-label:nth-child(2) strong').textContent=times.late||'—';
    $('#end-label').textContent=times.end||'—';
    $('#timeline-caption').textContent=times.note||'Set location or fallback quiet hours to calculate your schedule.';
    $('.example-label').textContent=times.kind||'Local solar schedule';
    $('#learning-status').textContent=s.learning_status;
    $('#hotkey-status').textContent=s.hotkey_status;
    const originalPreview=s.preview_kind?s.preview_kind==='compare':s.preview;
    $('#compare').setAttribute('aria-pressed',String(originalPreview));
    $('#compare-title').textContent=originalPreview?'Original colors':'Hold to see original';
    if(!hydrated) {
      const p=s.settings;
      field('#latitude',p.location?.latitude);field('#longitude',p.location?.longitude);
      field('#profile',p.profile);field('#bedtime',p.bedtime);
      field('#quiet-start',p.quiet?.start);field('#quiet-end',p.quiet?.end);
      $('#learning').checked=p.learning;$('#autostart').checked=p.autostart;
      if(s.smart_settings){
        const v=s.smart_settings;
        for(const [id,key] of Object.entries({'comfort-kind':'kind','comfort-ready':'evening_ready',
          'comfort-neutral':'morning_neutral','comfort-warmth':'warmth_kelvin','comfort-warm-lead':'warmth_lead',
          'comfort-dim-lead':'dim_lead','comfort-pace':'slower','comfort-offset':'solar_offset_minutes'}))field('#'+id,v[key]);
        field('#comfort-dim',v.dim_fraction*100);field('#latitude',v.latitude);field('#longitude',v.longitude);
        field('#quiet-start',v.fallback_ready);field('#quiet-end',v.fallback_neutral);
      }
      hydrated=true;
    }
    $('#sample').style.setProperty('--tint',originalPreview||!s.enabled?'0':String((6500-s.kelvin)/16000));
    $('#sample').style.setProperty('--dim',originalPreview||!s.enabled?'0':String(1-s.brightness));
    $('#sample').setAttribute('aria-label',originalPreview||!s.enabled?'Original color sample':`${s.kelvin} kelvin, ${Math.round((1-s.brightness)*100)} percent dimmed`);
  }
  function sliderLabels() {
    const k=6500-Number($('#warmth').value)*50, dim=Number($('#dimming').value);
    $('#warmth-value').value=k.toLocaleString()+' K';$('#dimming-value').value=dim+'%';
    $('#warmth').setAttribute('aria-valuetext',k+' kelvin');$('#dimming').setAttribute('aria-valuetext',dim+' percent dimming');
    $('#warmth').style.setProperty('--fill',Number($('#warmth').value)/106*100+'%');
    $('#dimming').style.setProperty('--fill',dim/80*100+'%');
  }
  function adjust() {
    lastEdit=Date.now();sliderLabels();
    pending={kelvin:6500-Number($('#warmth').value)*50,brightness:1-Number($('#dimming').value)/100};
    clearTimeout(debounce);debounce=setTimeout(()=>{send('adjust',pending);pending=null;},30);
  }
  $('#warmth').addEventListener('input',adjust);$('#dimming').addEventListener('input',adjust);
  $('#migration-begin').addEventListener('click',()=>{
    if(!current)return feedback('Desktop connection unavailable.');
    migrationPrior={draft:readDraft(),dirty,revision:draftRevision};migrationEditing=true;render(current,true);$('#comfort-kind').focus();
  });
  function previewMigration(){
    $('#migration-summary').textContent='Preparing a read-only schedule review…';
    send('preview_migration',{...readDraft(),expected_revision:draftRevision,request_id:'review-'+(window.crypto?.randomUUID?.()||Date.now())});
  }
  $('#migration-preview').addEventListener('click',previewMigration);
  $('#migration-switch').addEventListener('click',()=>{
    const r=current?.migration_review;
    if(!r?.switch_available)return feedback('Review Smart Comfort before switching.');
    $('#migration-summary').textContent='Saving a recovery copy and switching Smart Comfort…';
    send('commit_migration',{review_id:r.review_id,expected_revision:r.config_revision,
      request_id:'switch-'+(window.crypto?.randomUUID?.()||Date.now())});
  });
  $('#migration-keep').addEventListener('click',()=>{
    migrationEditing=false;$('#migration-summary').textContent='Current policy kept. No migration settings were saved.';
    if(migrationPrior){
      for(const [id,key] of Object.entries({latitude:'latitude',longitude:'longitude',profile:'profile',bedtime:'bedtime','quiet-start':'start','quiet-end':'end'}))field('#'+id,migrationPrior.draft[key]);
      dirty=migrationPrior.dirty;draftRevision=migrationPrior.revision;
    }
    if(current)render(current,true);
  });
  $('#start-setup').addEventListener('click',()=>{
    setupDismissed=true;setupRequested=false;$('#first-run-guide').hidden=true;$('#schedule-settings').open=true;
    $('#comfort-kind').focus();
  });
  $('#skip-setup').addEventListener('click',()=>{
    setupDismissed=true;setupRequested=false;$('#first-run-guide').hidden=true;
    feedback('Setup skipped for this session. Your current mode is unchanged. Reopen Quick start any time.');
  });
  $('#reopen-setup').addEventListener('click',()=>{setupDismissed=false;setupRequested=true;$('#first-run-guide').hidden=false;$('#start-setup').focus();});
  $('#power').addEventListener('click',()=>{clearTimeout(debounce);pending=null;send('power');});
  $('#close-window').addEventListener('click',()=>send('hide'));
  $('#minimize').addEventListener('click',()=>send('minimize'));
  $('.app-header').addEventListener('pointerdown',e=>{if(e.button===0&&!e.target.closest('button'))send('drag');});
  document.querySelectorAll('[name="mode"]').forEach(x=>x.addEventListener('change',()=>send('mode',{mode:x.value})));
  $('#pause').addEventListener('click',()=>send(current?.hold?'resume':'pause'));
  $('#neutral').addEventListener('click',()=>{clearTimeout(debounce);pending=null;send('off');});
  document.querySelectorAll('[data-kelvin]').forEach(x=>x.addEventListener('click',()=>send('adjust',{kelvin:Number(x.dataset.kelvin),brightness:current?.brightness??1})));
  let comparing=false;
  function compare(on) { if(comparing===on)return;comparing=on;send('compare',{enabled:on}); }
  $('#compare').addEventListener('pointerdown',e=>{if(e.button!==0)return;e.preventDefault();$('#compare').focus();$('#compare').setPointerCapture(e.pointerId);compare(true);});
  ['pointerup','pointercancel','lostpointercapture','blur'].forEach(type=>$('#compare').addEventListener(type,()=>compare(false)));
  $('#compare').addEventListener('keydown',e=>{if([' ','Enter'].includes(e.key)){e.preventDefault();compare(true);}});
  $('#compare').addEventListener('keyup',e=>{if([' ','Enter'].includes(e.key)){e.preventDefault();compare(false);}});
  window.addEventListener('blur',()=>compare(false));document.addEventListener('visibilitychange',()=>{if(document.hidden)compare(false);});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){compare(false);send('hide');}});
  $('#lookup').addEventListener('click',()=>{feedback('Looking up…');$('#lookup').disabled=true;send('lookup',{country:$('#country').value,postal:$('#postal').value});});
  $('#places').addEventListener('change',()=>{const p=places[Number($('#places').value)];if(p){field('#latitude',p.latitude);field('#longitude',p.longitude);}});
  $('#smart-form').addEventListener('submit',e=>{
    e.preventDefault();if(migrationEditing){previewMigration();return;}if(saveRequest)return;
    if(!bridge||!current){finishSave('Not saved. Desktop connection unavailable. Reopen Night Light and try again.');return;}
    saveDraft=readDraft();
    saveRequest='save-'+(window.crypto?.randomUUID?.()||Date.now()+'-'+(++sequence));
    checking=false;$('#check-save').hidden=true;$('#reload-saved').hidden=true;
    $('#save-smart').disabled=true;$('#save-smart').textContent='Saving…';
    $('#smart-form').setAttribute('aria-busy','true');$('#save-feedback').textContent='Saving your schedule…';
    saveTimer=setTimeout(checkSave,8000);
    try { send(current.smart_settings?'save_comfort':'save_smart',{request_id:saveRequest,expected_revision:draftRevision,...saveDraft}); }
    catch { finishSave('Not saved. Could not reach Night Light. Please try again.'); }
  });
  $('#smart-form').addEventListener('input',()=>{dirty=true;if(!saveRequest){$('#save-smart').textContent='Save and enable Smart';$('#save-feedback').textContent='Changes not saved yet.';}});
  $('#preview-comfort').addEventListener('click',()=>send('preview_comfort',{
    warmth_kelvin:Number($('#comfort-warmth').value),dim_fraction:Number($('#comfort-dim').value)/100}));
  $('#restore-comfort').addEventListener('click',()=>send('compare',{enabled:false}));
  $('#check-save').addEventListener('click',checkSave);
  $('#reload-saved').addEventListener('click',()=>{
    if(!current||!window.confirm('Replace these edits with the latest saved settings?'))return;
    reloadRequested=true;$('#save-feedback').textContent='Loading saved settings…';send('state');
  });
  $('#delete-location').addEventListener('click',()=>{if(window.confirm('Delete the saved location and stop Smart Mode?')){hydrated=false;send('delete_location');}});
  $('#learning').addEventListener('change',e=>send('learning',{enabled:e.target.checked}));
  $('#autostart').addEventListener('change',e=>send('autostart',{enabled:e.target.checked}));
  $('#reset-learning').addEventListener('click',()=>{if(window.confirm('Delete your local learning history?'))send('reset_learning');});
  $('#mark-sleep').addEventListener('click',()=>send('mark_sleep'));$('#mark-wake').addEventListener('click',()=>send('mark_wake'));
  $('#windows-off').addEventListener('click',()=>send('windows_off'));$('#quit').addEventListener('click',()=>send('quit'));
  $('#retry-display').addEventListener('click',()=>send('retry_display'));
  bridge?.addEventListener('message',e=>{
    const m=e.data;
    if(m.kind==='state'&&current?.session_id===m.state.session_id&&m.state.sequence<=current.sequence)return;
    if(reloadRequested&&m.kind==='state'){
      reloadRequested=false;hydrated=false;dirty=false;draftRevision=m.state.config_revision;
      finishSave('Loaded the saved settings.');$('#reload-saved').hidden=true;
    }
    if(m.kind==='state')render(m.state);
    if(saveRequest&&m.request_id===saveRequest) {
      if(m.kind==='error')finishSave(m.message);
      else if(m.kind==='state'&&!current.smart_settings)finishSave(savedStatus(),true);
    }
    if(saveRequest&&m.kind==='state'&&current.smart_settings){
      const result=current.save_result;
      if(result?.request_id===saveRequest){
        if(result.outcome==='saved')finishSave(savedStatus(),true);
        else if(result.outcome==='save_failed')finishSave('Could not save. Your edits are kept here. Reload saved settings or try again.');
        else if(result.outcome==='save_superseded')finishSave('A newer action replaced this save. Check the current mode; your edits are kept here.');
      }
    }
    if(checking&&m.kind==='state'&&!current.smart_settings&&matchesSaved(current,saveDraft)&&current.smart)finishSave(savedStatus(),true);
    if(m.kind==='state'&&m.message)feedback(m.message);
    if(m.kind==='error') {feedback(m.message);$('#lookup').disabled=false;if(migrationEditing)$('#migration-summary').textContent=m.message+' Your current policy is unchanged.';}
    if(m.kind==='lookup') {
      $('#lookup').disabled=false;places=m.places;
      $('#places').replaceChildren(...places.map((p,i)=>new Option(p.label,String(i))));
      $('#places-field').hidden=false;$('#places').dispatchEvent(new Event('change'));
      feedback('Review the matching area, then Save and enable Smart.');
    }
  });
  // No example schedule or active filter is shown while connecting.
  $('#status-meta').textContent=bridge?'Connecting':'UI preview · not connected';$('#status-title').textContent='Night Light';
  $('#status-copy').textContent=bridge?'Connecting to your display controls…':'Latest-source interface preview. This page cannot change your display.';
  if(!bridge)document.title='Night Light — latest-source UI preview (not installed)';
  $('#power').setAttribute('aria-checked','false');
  document.querySelectorAll('[name="mode"]').forEach(x=>x.checked=false);
  document.querySelectorAll('#power,#warmth,#dimming,#compare,[name="mode"]').forEach(x=>x.disabled=true);
  $('#timeline').hidden=true;$('#pause').disabled=true;sliderLabels();
  $('#warmth-value').value='—';$('#dimming-value').value='—';send('state');
})();
