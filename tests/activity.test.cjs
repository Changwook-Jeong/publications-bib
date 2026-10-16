const test = require('node:test');
const assert = require('node:assert/strict');
const init = require('../web/research-activity.js');

class Element {
  constructor(dataset={}) {
    this.dataset=dataset;this.hidden=false;this.open=false;this.textContent='';
    this.attrs={};this.listeners={};this.children=[];this.queries={};
    const classes=new Set();
    this.classList={
      add:n=>classes.add(n),remove:n=>classes.delete(n),contains:n=>classes.has(n),
      toggle:(n,force)=>{if(force??!classes.has(n))classes.add(n);else classes.delete(n);}
    };
  }
  setAttribute(n,v){this.attrs[n]=v;}
  querySelector(s){return this.queries[s] || null;}
  querySelectorAll(s){return this.queries[s] || [];}
  addEventListener(n,fn){(this.listeners[n]??=[]).push(fn);}
  emit(n,event={}){for(const f of this.listeners[n] || [])f(event);}
  contains(e){return this.children.includes(e);}
  scrollIntoView(){this.scrolled=true;}
  focus(){this.focused=true;}
}

function fixture(search='') {
  const root=new Element();
  const panels=['papers','patents'].map(kind=>{
    const p=new Element({trendPanel:kind});
    p.queries['.history-scroll']=Object.assign(new Element(),{scrollWidth:520,clientWidth:375,scrollLeft:0});
    p.queries['.history-selection-tools']=new Element();
    p.queries['.history-selection-status']=new Element();
    p.queries['.history-close']=new Element();
    return p;
  });
  const buttons=['papers','patents'].map(trend=>new Element({trend}));
  const years=[];
  const links=[];
  const items=[];
  for(const kind of ['papers','patents']) for(const year of ['2022','2026']) {
    const p=new Element({historyPanel:kind+'-'+year,historyCount:'1'});
    const item=new Element({historyItem:kind+year});
    p.children.push(item);items.push(item);years.push(p);
    links.push(new Element({historyKind:kind,historyYear:year,historyKey:item.dataset.historyItem}));
  }
  root.queries={
    '[data-trend-panel]':panels,'[data-trend]':buttons,
    '[data-history-panel]':years,'[data-history-year]':links,
    '[data-history-item]':items,
    '.history-scroll':Object.assign(new Element(),{scrollWidth:1000,clientWidth:375,scrollLeft:0}),
    '.history-selection-tools':new Element(),'.history-selection-status':new Element(),'.history-close':new Element()
  };
  const env={
    location:{search,href:'https://example.org/research-preview/'+search},
    matchMedia:()=>({matches:true}),
    history:{replaceState:(_,__,url)=>{env.location.href=String(url);env.location.search=new URL(url).search;}}
  };
  return {root,panels,buttons,years,links,items,env,api:init(root,env)};
}

test('combined chart keeps both record groups visible and scrolls to recent years',()=>{
  const f=fixture();
  assert.equal(f.panels[0].hidden,false);
  assert.equal(f.panels[1].hidden,false);
  assert.equal(f.root.queries['.history-scroll'].scrollLeft,625);
  assert.equal(f.root.queries['.history-selection-tools'].hidden,true);
  assert.equal(f.root.classList.contains('history-enhanced'),true);
});
test('select patent stack without touching gallery query parameters',()=>{
  const f=fixture('?q=oxide&topic=materials&embed=1');
  f.api.selectYear('patents','2026');
  assert.equal(f.panels[1].hidden,false);
  const url=new URL(f.env.location.href);
  assert.equal(url.searchParams.get('trend'),'patents');
  assert.equal(url.searchParams.get('q'),'oxide');
  assert.equal(url.searchParams.get('embed'),'1');
});
test('dot selection opens matching year and highlights only that record',()=>{
  const f=fixture();
  let prevented=false;
  f.links[3].emit('click',{preventDefault:()=>{prevented=true;}});
  assert.equal(prevented,true);
  assert.equal(f.years[3].open,true);
  assert.equal(f.years[2].open,false);
  assert.equal(f.items[3].classList.contains('is-highlighted'),true);
  assert.equal(f.items[3].focused,true);
  assert.equal(f.items[3].scrolled,true);
  assert.equal(f.root.queries['.history-selection-status'].textContent,'2026 · 1 patent records');
  f.api.closeSelection();
  assert.equal(f.years[3].open,false);
  assert.equal(new URL(f.env.location.href).searchParams.has('history-year'),false);
});
test('restore a valid year and ignore invalid query input',()=>{
  const f=fixture('?trend=patents&history-year=2022&history-key=patents2022');
  assert.equal(f.years[2].open,true);
  assert.equal(f.items[2].classList.contains('is-highlighted'),true);
  assert.equal(f.api.selectYear('papers','2026<script>'),false);
  assert.equal(f.api.selectYear('unknown','2026'),false);
  const legacy=fixture('?trend=patents&history-year=2007');
  assert.equal(legacy.years.some(y=>y.open),false);
});
test('modified link click is not intercepted',()=>{
  const f=fixture();
  f.links[0].emit('click',{ctrlKey:true,preventDefault:()=>assert.fail('modified click intercepted')});
  assert.equal(f.years[0].open,false);
});
test('native closing of details synchronizes expanded state',()=>{
  const f=fixture();
  f.api.selectYear('papers','2026');
  f.years[1].open=false;f.years[1].emit('toggle');
  assert.equal(f.links[1].attrs['aria-expanded'],'false');
  assert.equal(f.root.queries['.history-selection-tools'].hidden,true);
});
test('switching stacks closes old selection but never hides either data series',()=>{
  const f=fixture();
  f.api.selectYear('papers','2026','papers2026');
  f.api.selectYear('patents','2022','patents2022');
  assert.equal(f.years.filter(y=>y.open).length,1);
  assert.equal(f.years[2].open,true);
  assert.equal(f.items[1].classList.contains('is-highlighted'),false);
  assert.equal(f.links[1].attrs['aria-expanded'],'false');
  assert.equal(f.links[2].attrs['aria-expanded'],'true');
  assert.ok(f.panels.every(p=>!p.hidden));
});
