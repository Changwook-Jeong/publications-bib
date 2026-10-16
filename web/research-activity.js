// Paired stacks are server rendered. Enhancement never requests private data.
(function () {
  function initResearchActivity(root, env) {
    if (!root) return null;
    const years = [...root.querySelectorAll('[data-history-panel]')];
    const links = [...root.querySelectorAll('[data-history-year]')];
    const items = [...root.querySelectorAll('[data-history-item]')];
    const tools = root.querySelector('.history-selection-tools');
    const status = root.querySelector('.history-selection-status');
    const reduced = env.matchMedia('(prefers-reduced-motion: reduce)');
    const params = new URLSearchParams(env.location.search);
    root.classList.add('history-enhanced');
    const region = root.querySelector('.history-scroll');
    region.scrollLeft = Math.max(0,region.scrollWidth-region.clientWidth);

    function currentSelection() { return years.find(p => p.open); }
    function save() {
      const url = new URL(env.location.href);
      const panel = currentSelection();
      if (panel) {
        const [kind,year] = panel.dataset.historyPanel.split('-');
        url.searchParams.set('trend',kind);
        url.searchParams.set('history-year',year);
      } else {
        url.searchParams.delete('trend');
        url.searchParams.delete('history-year');
      }
      const highlighted = items.find(i => i.classList.contains('is-highlighted') && panel?.contains(i));
      if (highlighted) url.searchParams.set('history-key',highlighted.dataset.historyItem);
      else url.searchParams.delete('history-key');
      env.history.replaceState(null,'',url);
    }
    function sync() {
      const selection = currentSelection();
      tools.hidden = !selection;
      if (selection) {
        const [kind,year] = selection.dataset.historyPanel.split('-');
        status.textContent = year+' · '+selection.dataset.historyCount+' '+(kind==='papers'?'papers':'patent records');
      } else status.textContent = '';
      links.forEach(link => {
        const id=link.dataset.historyKind+'-'+link.dataset.historyYear;
        link.setAttribute('aria-controls','history-'+id);
        link.setAttribute('aria-expanded',String(selection?.dataset.historyPanel===id));
        link.classList.toggle('selected-year',selection?.dataset.historyPanel===id);
      });
    }
    function selectYear(kind, year, key='', shouldScroll=true, persist=true) {
      const panel=years.find(p=>p.dataset.historyPanel===kind+'-'+year);
      if(!panel) return false;
      years.forEach(p=>{p.open=p===panel;});
      items.forEach(i=>i.classList.remove('is-highlighted'));
      const item=items.find(i=>i.dataset.historyItem===key && panel.contains(i));
      if(item) item.classList.add('is-highlighted');
      sync();
      if(shouldScroll) {
        (item || panel).scrollIntoView({behavior:reduced.matches?'auto':'smooth',block:'nearest'});
        if(item) item.focus({preventScroll:true});
      }
      if(persist) save();
      return true;
    }
    function closeSelection() {
      const selected=currentSelection()?.dataset.historyPanel;
      years.forEach(p=>{p.open=false;});
      items.forEach(i=>i.classList.remove('is-highlighted'));
      sync();save();
      links.find(l=>l.dataset.historyKind+'-'+l.dataset.historyYear===selected && !l.dataset.historyKey)?.focus({preventScroll:true});
    }
    links.forEach(link=>link.addEventListener('click',event=>{
      if(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if(selectYear(link.dataset.historyKind,link.dataset.historyYear,link.dataset.historyKey || '')) event.preventDefault();
    }));
    root.querySelector('.history-close').addEventListener('click',closeSelection);
    years.forEach(panel=>panel.addEventListener('toggle',()=>{sync();save();}));
    sync();
    if(params.has('history-year'))
      selectYear(params.get('trend')==='patents'?'patents':'papers',params.get('history-year'),params.get('history-key') || '',false,false);
    return {selectYear,closeSelection};
  }
  if(typeof module!=='undefined' && module.exports) module.exports=initResearchActivity;
  if(typeof document!=='undefined') initResearchActivity(document.querySelector('#research-activity'),window);
})();
