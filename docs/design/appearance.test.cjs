// Run: node --test docs/design/appearance.test.cjs
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');
const source=readFileSync(join(__dirname,'appearance.js'),'utf8');
function setup(saved=null,blocked=false) {
  class Element {
    constructor(value) {this.value=value;this.dataset={};this.attributes={};this.children=[];this.events={};this.tokens={};this.style={setProperty:(key,value)=>this.tokens[key]=value};}
    setAttribute(key,value){this.attributes[key]=value;}
    append(...children){this.children.push(...children);}
    addEventListener(type,handler){this.events[type]=handler;}
    fire(type){this.events[type]?.({target:this});}
  }
  const elements=new Map();
  const find=selector=>{if(!elements.has(selector)) elements.set(selector,new Element()); return elements.get(selector);};
  const theme=['dark','light'].map(value=>new Element(value));
  const material=['liquid','frosted','solid','ceramic'].map(value=>new Element(value));
  const body=new Element();
  let stored=saved;
  const document={body,querySelector:find,createElement:()=>new Element(),createTextNode:value=>value,
    querySelectorAll:selector=>selector.includes('name="theme"') ? theme : selector.includes('name="material"') ? material : find('.palette-grid').children};
  vm.runInNewContext(source,{document,localStorage:{getItem:()=>{if(blocked)throw Error();return stored;},setItem:(_,value)=>{if(blocked)throw Error();stored=value;}}});
  return {find,theme,material,body,palette:id=>find('.palette-grid').children.find(button=>button.dataset.palette===id),saved:()=>stored};
}
test('independent palettes and materials survive reload',()=>{
  const ui=setup();ui.palette('ocean').fire('click');ui.material[1].fire('change');
  ui.theme[1].fire('change');ui.palette('rose').fire('click');ui.material[3].fire('change');
  const saved=JSON.parse(ui.saved());assert.equal(saved.dark.preset,'ocean');assert.equal(saved.dark.material,'frosted');
  assert.equal(saved.light.preset,'rose');assert.equal(saved.light.material,'ceramic');
  const reload=setup(ui.saved());assert.equal(reload.body.dataset.material,'ceramic');
  assert.equal(reload.find('.flyout').tokens['--palette-surface'],'#e99bb1');
  reload.theme[0].fire('change');assert.equal(reload.body.dataset.material,'frosted');
});
test('custom colors, motion and mode-scoped reset',()=>{
  const ui=setup();ui.palette('sage').fire('click');ui.theme[1].fire('change');
  const picker=ui.find('#accent-color');picker.value='#00ff44';picker.fire('input');picker.fire('change');
  assert.equal(JSON.parse(ui.saved()).light.preset,'custom');
  assert.equal(JSON.parse(ui.saved()).light.accent,'#00ff44');
  ui.find('#gentle-motion').checked=false;ui.find('#gentle-motion').fire('change');
  assert.equal(ui.body.dataset.motion,'still');
  ui.find('#reset-appearance').fire('click');
  const saved=JSON.parse(ui.saved());assert.equal(saved.dark.preset,'sage');assert.equal(saved.light.preset,'signature');
});
test('page background is independent, persisted and migrates old settings',()=>{
  const ui=setup();
  const picker=ui.find('#background-color');picker.value='#102030';picker.fire('input');picker.fire('change');
  assert.equal(ui.body.tokens['--page-background'],'#102030');
  ui.theme[1].fire('change');assert.equal(ui.body.tokens['--page-background'],'#e8ebef');
  ui.theme[0].fire('change');
  assert.equal(setup(ui.saved()).body.tokens['--page-background'],'#102030');
  const legacy=JSON.parse(ui.saved());delete legacy.dark.background;
  assert.equal(setup(JSON.stringify(legacy)).body.tokens['--page-background'],'#f3f1ec');
  ui.find('#reset-appearance').fire('click');assert.equal(ui.body.tokens['--page-background'],'#101217');
});
test('presets apply accent, panel and background without changing material',()=>{
  const ui=setup();ui.material[3].fire('change');ui.palette('ocean').fire('click');
  assert.equal(ui.body.tokens['--page-background'],'#12344f');
  assert.equal(ui.find('.flyout').tokens['--palette-surface'],'#184e78');
  assert.equal(ui.body.dataset.material,'ceramic');
  ui.theme[1].fire('change');ui.palette('ocean').fire('click');
  assert.equal(ui.body.tokens['--page-background'],'#559bd0');
});
test('individual presets only change their own color and persist',()=>{
  const ui=setup();ui.palette('ocean').fire('click');
  for(const key of ['accent','surface','background']) {
    const before=JSON.parse(ui.saved()).dark;
    ui.find('#'+key+'-presets').children[5].fire('click');
    const after=JSON.parse(ui.saved()).dark;
    assert.notEqual(after[key],before[key]);
    for(const other of ['accent','surface','background'].filter(value=>value!==key))assert.equal(after[other],before[other]);
    assert.equal(after.material,before.material);
  }
  assert.equal(setup(ui.saved()).body.tokens['--page-background'],'#4f2536');
});
test('corrupt, invalid and unavailable storage never breaks appearance',()=>{
  for(const stored of ['{','null','[]',JSON.stringify({theme:'bad',dark:{accent:'url(x)',surface:'#fff'}})]) {
    assert.equal(setup(stored).find('.flyout').dataset.theme,'dark');
  }
  const ui=setup(null,true);ui.palette('lavender').fire('click');
  assert.match(ui.find('#appearance-save').textContent,/unavailable/);
  assert.equal(ui.find('.flyout').tokens['--palette-surface'],'#583c7a');
});
test('all palette and material combinations generate valid color tokens',()=>{
  const ui=setup();
  for(const theme of ui.theme)for(const material of ui.material)for(const id of ['signature','amber','ocean','sage','lavender','rose','graphite','mocha','midnight','jade','cloud']){
    theme.fire('change');material.fire('change');ui.palette(id).fire('click');
    assert.equal(ui.body.dataset.material,material.value);
    for(const token of Object.values(ui.find('.flyout').tokens))assert.match(token,/^#[0-9a-f]{6}([0-9a-f]{2})?$/i);
  }
});
test('factory appearance is signature charcoal and amber with an exact legacy migration',()=>{
  const ui=setup();
  assert.equal(ui.find('.flyout').dataset.standard,'true');
  assert.equal(ui.body.dataset.material,'frosted');
  assert.equal(ui.body.tokens['--page-background'],'#101217');
  assert.equal(ui.find('.flyout').tokens['--palette-accent'],'#f3ad3d');
  const legacy=JSON.stringify({theme:'dark',motion:true,
    dark:{preset:'custom',accent:'#a5c9f5',surface:'#202d40',background:'#101a29',material:'liquid'},
    light:{preset:'custom',accent:'#295b87',surface:'#e8eef5',background:'#cad9e9',material:'liquid'}});
  const migrated=setup(legacy);const saved=JSON.parse(migrated.saved());
  assert.equal(saved.dark.preset,'signature');assert.equal(saved.dark.material,'frosted');
  assert.equal(saved.light.preset,'signature');assert.equal(saved.light.material,'ceramic');
});
