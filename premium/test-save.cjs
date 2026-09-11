/* Isolated controller tests: no browser, native bridge, display or user storage. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
function fixture() {
  const nodes=new Map(),sent=[],timers=new Map();let timerId=0,receive;
  function node(selector) {
    if(!nodes.has(selector))nodes.set(selector,{value:'',textContent:'',disabled:false,hidden:false,checked:false,
      handlers:{},attributes:{},style:{setProperty(){}},classList:{toggle(){}},
      parentElement:{hidden:false},closest(){return this.parentElement;},
      setAttribute(k,v){this.attributes[k]=v;},addEventListener(k,fn){this.handlers[k]=fn;},
      replaceChildren(){},focus(){},setPointerCapture(){}});
    return nodes.get(selector);
  }
  const bridge={postMessage:m=>sent.push(m),addEventListener:(kind,fn)=>receive=fn};
  const window={chrome:{webview:bridge},addEventListener(){},confirm:()=>true,crypto:{randomUUID:()=>String(++timerId)}};
  const document={querySelector:node,querySelectorAll:selector=>selector.split(',').flatMap(part=>{
    if(part==='[name="mode"]')return ['smart','manual'].map(value=>{const n=node('mode-'+value);n.value=value;return n;});
    return part.startsWith('#')?[node(part)]:[];
  }),addEventListener(){},activeElement:null};
  const context={window,document,console,Date,Math,Number,String,JSON,crypto:window.crypto,
    setTimeout:(fn,ms)=>{const id=++timerId;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'desktop.js'),'utf8'),context);
  let sequence=0;
  const state=(changes={})=>({protocol_version:2,session_id:'test-session',sequence:++sequence,config_revision:3,
    meta:'Manual · off',title:'Off',detail:'No automatic changes',power:false,smart:false,enabled:false,
    kelvin:4000,brightness:1,hold:false,blocked:false,preview:false,times:{},
    settings:{location:null,profile:'balanced',bedtime:'',quiet:null,learning:false,autostart:false},...changes});
  function message(m){receive({data:m});}
  function event(selector,kind){node(selector).handlers[kind]({preventDefault(){}});}
  function timer(ms){const entry=[...timers].find(([,t])=>t.ms===ms);assert.ok(entry,`timer ${ms}`);timers.delete(entry[0]);entry[1].fn();}
  message({kind:'state',state:state()});
  return {node,sent,state,message,event,timer};
}
function submit(f){f.node('#latitude').value='42';f.node('#longitude').value='-83';f.event('#smart-form','input');f.event('#smart-form','submit');return f.sent.at(-1);}
{
  const f=fixture(),request=submit(f);
  assert.equal(request.session_id,'test-session');assert.equal(request.expected_revision,3);
  assert.equal(f.node('#save-smart').disabled,true);
  f.event('#smart-form','submit');assert.equal(f.sent.filter(m=>m.action==='save_smart').length,1);
  f.message({kind:'error',request_id:request.request_id,message:'Could not save your settings.'});
  assert.equal(f.node('#latitude').value,'42');assert.equal(f.node('#save-smart').disabled,false);
}
{
  const f=fixture();submit(f);f.timer(8000);
  assert.match(f.node('#save-feedback').textContent,/Checking/);
  assert.equal(f.sent.at(-1).action,'state');
  f.timer(8000);assert.equal(f.node('#check-save').hidden,false);
  assert.match(f.node('#save-feedback').textContent,/edits are kept/);
}
{
  const f=fixture(),request=submit(f);f.timer(8000);
  f.message({kind:'state',state:f.state({config_revision:4,smart:true,settings:{location:{latitude:42,longitude:-83},profile:'balanced',bedtime:'',quiet:null}})});
  assert.match(f.node('#save-feedback').textContent,/saved/i);
  assert.equal(f.node('#save-smart').disabled,false);
  assert.equal(f.sent.filter(m=>m.request_id===request.request_id).length,1);
}
{
  const f=fixture();f.node('#warmth').value='40';f.event('#warmth','input');
  f.event('#power','click');
  assert.equal(f.sent.at(-1).action,'power');
  assert.throws(()=>f.timer(30),/timer 30/);
}
{
  const f=fixture(),request=submit(f);
  f.node('#latitude').value='43';f.event('#smart-form','input');
  f.message({kind:'state',request_id:request.request_id,state:f.state({config_revision:4,smart:true})});
  assert.equal(f.node('#latitude').value,'43');
  assert.match(f.node('#save-feedback').textContent,/Newer edits have not been saved/);
}
{
  const f=fixture();submit(f);
  f.message({kind:'state',state:f.state({session_id:'restarted',config_revision:8})});
  assert.equal(f.node('#latitude').value,'42');
  f.message({kind:'state',state:f.state({session_id:'restarted',sequence:1,title:'stale'})});
  assert.notEqual(f.node('#status-title').textContent,'stale');
}
{
  const f=fixture();
  f.message({kind:'state',state:f.state({output_fault:'external_conflict'})});
  assert.equal(f.node('#repair').hidden,false);
  f.event('#retry-display','click');
  assert.equal(f.sent.at(-1).action,'retry_display');
  assert.equal(f.sent.at(-1).session_id,'test-session');
}
{
  const f=fixture(),request=submit(f);
  f.message({kind:'state',request_id:request.request_id,state:f.state({smart:true,output_fault:'backend_error'})});
  assert.match(f.node('#save-feedback').textContent,/saved.*unavailable/i);
  assert.equal(f.node('#save-smart').disabled,false);
}
{
  const f=fixture(),settings={kind:'personal',evening_ready:'22:00',morning_neutral:'07:00',
    warmth_kelvin:4000,dim_fraction:0,warmth_lead:180,dim_lead:60,slower:1,solar_offset_minutes:60,
    latitude:null,longitude:null,fallback_ready:null,fallback_neutral:null};
  f.message({kind:'state',state:f.state({smart_settings:settings})});
  f.node('#comfort-warmth').value='3200';f.event('#smart-form','input');f.event('#smart-form','submit');
  const request=f.sent.at(-1);
  assert.equal(request.action,'save_comfort');assert.equal(request.settings.warmth_kelvin,3200);
  f.message({kind:'state',request_id:request.request_id,state:f.state({smart_settings:settings,
    save_result:{request_id:request.request_id,outcome:'saving'}})});
  assert.equal(f.node('#save-smart').disabled,true,'transport reply cannot acknowledge persistence');
  f.message({kind:'state',state:f.state({smart:true,config_revision:4,smart_settings:request.settings,
    save_result:{request_id:request.request_id,outcome:'saved'}})});
  assert.equal(f.node('#save-smart').disabled,false);
  assert.match(f.node('#save-feedback').textContent,/saved/i);
}
{
  const f=fixture();f.message({kind:'state',state:f.state({first_run:true})});
  assert.equal(f.node('#first-run-guide').hidden,false);
  const count=f.sent.length;f.event('#skip-setup','click');
  assert.equal(f.sent.length,count,'Skip must not enable or persist display intent');
  f.message({kind:'state',state:f.state({first_run:true})});
  assert.equal(f.node('#first-run-guide').hidden,true);
  f.event('#reopen-setup','click');
  f.message({kind:'state',state:f.state({first_run:false})});
  assert.equal(f.node('#first-run-guide').hidden,false,'Periodic state must not dismiss reopened help');
}
{
  const f=fixture();f.node('#latitude').value='43';f.event('#smart-form','input');
  const count=f.sent.length;f.event('#migration-begin','click');
  assert.equal(f.sent.length,count,'Opening review does not mutate native settings');
  assert.equal(f.node('#save-smart').hidden,true);
  f.event('#smart-form','submit');assert.equal(f.sent.at(-1).action,'preview_migration');
  f.node('#latitude').value='50';f.event('#migration-keep','click');
  assert.equal(f.node('#latitude').value,'43','Keep restores the preceding unsaved draft');
  f.message({kind:'state',state:f.state({title:'Next native snapshot'})});
  assert.equal(f.node('#status-title').textContent,'Next native snapshot','Local rendering must not forge a native sequence');
}
{
  const f=fixture();f.message({kind:'state',state:f.state({migration_pending:true,smart:true})});
  for(const id of ['#warmth','#dimming','#compare','#save-smart','#pause','mode-smart','mode-manual'])
    assert.equal(f.node(id).disabled,true,`${id} must wait for the handoff`);
  assert.equal(f.node('#power').disabled,false,'Off stays available');
  f.message({kind:'state',state:f.state({migration_pending:false,smart:true})});
  assert.equal(f.node('#warmth').disabled,false);
}
{
  const f=fixture();f.message({kind:'state',state:f.state({build_identity:{kind:'packaged',
    label:'Packaged private candidate',version:'0.1.0',build_id:'1234567890abcdef',dirty:true}})});
  assert.match(f.node('#build-identity').textContent,/0.1.0.*1234567890abcdef.*Uncommitted/);
  f.message({kind:'state',state:f.state({build_identity:{kind:'development',label:'Source development run'}})});
  assert.equal(f.node('#build-identity').textContent,'Source development run');
}
console.log('Save UI controller: 13 isolated scenarios passed');
