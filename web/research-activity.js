// The data and SVGs are server rendered. Enhancement never requests private data.
(function () {
  function initResearchActivity(root, env) {
    if (!root) return null;
    const panels = [...root.querySelectorAll('[data-trend-panel]')];
    const buttons = [...root.querySelectorAll('[data-trend]')];
    const years = [...root.querySelectorAll('[data-history-panel]')];
    const links = [...root.querySelectorAll('[data-history-year]')];
    const items = [...root.querySelectorAll('[data-history-item]')];
    const reduced = env.matchMedia('(prefers-reduced-motion: reduce)');
    const scrolled = new Set();
    let active = 'papers';
    const params = new URLSearchParams(env.location.search);
    root.classList.add('history-enhanced');
    root.querySelector('.trend-switch').hidden = false;

    function currentSelection(kind) {
      return years.find(p => p.open && p.dataset.historyPanel.startsWith(kind+'-'));
    }
    function save() {
      const url = new URL(env.location.href);
      if (active === 'papers') url.searchParams.delete('trend');
      else url.searchParams.set('trend',active);
      const panel = currentSelection(active);
      if (panel) url.searchParams.set('history-year',panel.dataset.historyPanel.split('-')[1]);
      else url.searchParams.delete('history-year');
      const highlighted = items.find(i => i.classList.contains('is-highlighted') && panel?.contains(i));
      if (highlighted) url.searchParams.set('history-key',highlighted.dataset.historyItem);
      else url.searchParams.delete('history-key');
      env.history.replaceState(null,'',url);
    }
    function sync(kind) {
      const trend = panels.find(p => p.dataset.trendPanel === kind);
      const selection = currentSelection(kind);
      trend.querySelector('.history-selection-tools').hidden = !selection;
      trend.querySelector('.history-selection-status').textContent = selection
        ? selection.dataset.historyPanel.split('-')[1]+' · '+selection.dataset.historyCount+' '+(kind === 'papers' ? 'papers' : 'patent records')
        : '';
      for (const link of links) {
        if (link.dataset.historyKind !== kind) continue;
        const id = kind+'-'+link.dataset.historyYear;
        link.setAttribute('aria-controls','history-'+id);
        link.setAttribute('aria-expanded',String(selection?.dataset.historyPanel === id));
        link.classList.toggle('selected-year',selection?.dataset.historyPanel === id);
      }
    }
    function selectTrend(kind, persist = true) {
      if (!panels.some(p => p.dataset.trendPanel === kind)) return false;
      active = kind;
      panels.forEach(p => {p.hidden=p.dataset.trendPanel !== kind;});
      buttons.forEach(b => b.setAttribute('aria-pressed',String(b.dataset.trend === kind)));
      const region = panels.find(p => !p.hidden).querySelector('.history-scroll');
      if (region && !scrolled.has(region)) {
        region.scrollLeft=Math.max(0,region.scrollWidth-region.clientWidth);
        scrolled.add(region);
      }
      sync(kind);
      if (persist) save();
      return true;
    }
    function selectYear(kind, year, key = '', shouldScroll = true, persist = true) {
      const panel = years.find(p => p.dataset.historyPanel === kind+'-'+year);
      if (!panel) return false;
      selectTrend(kind,false);
      years.forEach(p => {if(p.dataset.historyPanel.startsWith(kind+'-')) p.open=p===panel;});
      items.forEach(i => i.classList.remove('is-highlighted'));
      const item = items.find(i => i.dataset.historyItem === key && panel.contains(i));
      if (item) item.classList.add('is-highlighted');
      sync(kind);
      if (shouldScroll) {
        (item || panel).scrollIntoView({behavior:reduced.matches?'auto':'smooth',block:'nearest'});
        if(item) item.focus({preventScroll:true});
      }
      if (persist) save();
      return true;
    }
    function closeSelection(kind = active) {
      const selected=currentSelection(kind);
      const selectedYear=selected?.dataset.historyPanel.split('-')[1];
      years.forEach(p => {if(p.dataset.historyPanel.startsWith(kind+'-')) p.open=false;});
      items.forEach(i => i.classList.remove('is-highlighted'));
      sync(kind);save();
      const yearLink=links.find(l => l.dataset.historyKind===kind && l.dataset.historyYear===selectedYear && !l.dataset.historyKey);
      yearLink?.focus({preventScroll:true});
    }
    buttons.forEach(b => b.addEventListener('click',() => selectTrend(b.dataset.trend)));
    links.forEach(link => link.addEventListener('click',event => {
      if(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if(selectYear(link.dataset.historyKind,link.dataset.historyYear,link.dataset.historyKey || ''))
        event.preventDefault();
    }));
    panels.forEach(p => p.querySelector('.history-close').addEventListener('click',() => closeSelection(p.dataset.trendPanel)));
    years.forEach(p => p.addEventListener('toggle',() => {
      const kind=p.dataset.historyPanel.split('-')[0];
      sync(kind);
      if(kind===active) save();
    }));
    selectTrend(params.get('trend') === 'patents' ? 'patents' : 'papers',false);
    if(params.has('history-year'))
      selectYear(active,params.get('history-year'),params.get('history-key') || '',false,false);
    return {selectTrend,selectYear,closeSelection};
  }
  if(typeof module !== 'undefined' && module.exports) module.exports=initResearchActivity;
  if(typeof document !== 'undefined')
    initResearchActivity(document.querySelector('#research-activity'),window);
})();
