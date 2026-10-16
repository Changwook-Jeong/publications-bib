// Progressive enhancement: every paper remains a real link without JavaScript.
(() => {
  const grid = document.querySelector('#research-grid');
  if (!grid) return;
  const cards = [...grid.querySelectorAll('.research-card')];
  const tools = document.querySelector('.explorer-tools');
  const search = document.querySelector('#research-search');
  const sort = document.querySelector('#research-sort');
  const filters = [...document.querySelectorAll('[data-filter]')];
  const views = [...document.querySelectorAll('[data-view]')];
  const empty = document.querySelector('.empty-state');
  const count = document.querySelector('#result-count');
  const dialog = document.querySelector('#research-reader');
  const content = document.querySelector('#reader-content');
  const scroller = document.querySelector('.reader-scroll');
  const previous = document.querySelector('#reader-prev');
  const next = document.querySelector('#reader-next');
  const close = document.querySelector('#reader-close');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const params = new URLSearchParams(location.search);
  let topic = filters.some(b => b.dataset.filter === params.get('topic')) ? params.get('topic') : 'all';
  let view = params.get('view') === 'list' ? 'list' : 'grid';
  let visible = [...cards], active = null, returnFocus = null;
  search.value = params.get('q') || '';
  sort.value = params.get('order') === 'oldest' ? 'oldest' : 'newest';
  tools.hidden = false;

  function saveState() {
    const url = new URL(location.href);
    for (const [key,value,defaultValue] of [
      ['topic',topic,'all'], ['q',search.value.trim(),''],
      ['order',sort.value,'newest'], ['view',view,'grid']
    ]) {
      if (value === defaultValue) url.searchParams.delete(key);
      else url.searchParams.set(key,value);
    }
    history.replaceState(null,'',url);
  }

  function update(animate = true) {
    const before = new Map(cards.filter(c => !c.hidden).map(c => [c,c.getBoundingClientRect()]));
    cards.forEach(c => c.getAnimations().forEach(a => a.cancel()));
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const sorted = [...cards].sort((a,b) => {
      const comparison = a.dataset.date.localeCompare(b.dataset.date);
      return (sort.value === 'oldest' ? comparison : -comparison) ||
        a.dataset.slug.localeCompare(b.dataset.slug);
    });
    for (const card of sorted) {
      const areaMatch = topic === 'all' || card.dataset.topic.split(' ').includes(topic);
      const text = card.dataset.search.toLocaleLowerCase();
      card.hidden = !(areaMatch && terms.every(term => text.includes(term)));
      grid.append(card);
    }
    visible = sorted.filter(c => !c.hidden);
    grid.classList.toggle('list-view',view === 'list');
    filters.forEach(b => {
      b.classList.toggle('active',b.dataset.filter === topic);
      b.setAttribute('aria-pressed',String(b.dataset.filter === topic));
    });
    views.forEach(b => b.setAttribute('aria-pressed',String(b.dataset.view === view)));
    count.textContent = visible.length + ' of ' + cards.length + ' papers · ' +
      (sort.value === 'oldest' ? 'oldest first' : 'newest first');
    empty.hidden = visible.length !== 0;
    if (animate && !motion.matches) {
      for (const card of visible) {
        if (!card.animate) continue;
        const old = before.get(card), now = card.getBoundingClientRect();
        const from = old
          ? {transform:'translate('+(old.left-now.left)+'px,'+(old.top-now.top)+'px)',opacity:.8}
          : {transform:'translateY(12px)',opacity:0};
        card.animate([from,{transform:'translate(0,0)',opacity:1}],{
          duration:250,easing:'cubic-bezier(.2,.7,.2,1)'
        });
      }
    }
    saveState();
  }

  function openPaper(slug,trigger) {
    const template = document.getElementById('summary-'+slug);
    const card = cards.find(c => c.dataset.slug === slug);
    if (!template || !card || typeof dialog.showModal !== 'function') return false;
    active = card;
    if (trigger) returnFocus = trigger;
    content.replaceChildren(template.content.cloneNode(true));
    const index = visible.indexOf(active);
    previous.disabled = index <= 0;
    next.disabled = index < 0 || index >= visible.length-1;
    document.querySelector('#reader-position').textContent =
      index < 0 ? '' : (index+1)+' / '+visible.length;
    scroller.scrollTop = 0;
    if (!dialog.open) {
      document.body.classList.add('reader-is-open');
      dialog.showModal();
    }
    close.focus({preventScroll:true});
    const url = new URL(location.href);
    url.hash = 'paper='+encodeURIComponent(slug);
    history.replaceState(null,'',url);
    return true;
  }

  filters.forEach(b => b.addEventListener('click',() => {topic=b.dataset.filter;update();}));
  views.forEach(b => b.addEventListener('click',() => {view=b.dataset.view;update();}));
  search.addEventListener('input',() => update());
  sort.addEventListener('change',() => update());
  document.querySelector('#reset-filters').addEventListener('click',() => {
    topic='all';search.value='';update();search.focus();
  });
  for (const link of grid.querySelectorAll('[data-paper]')) {
    link.addEventListener('click',event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      if (openPaper(link.dataset.paper,link)) event.preventDefault();
    });
  }
  cards.forEach(card => card.addEventListener('click',event => {
    if (event.target.closest('a,button,input,select') || window.getSelection()?.toString()) return;
    const link=card.querySelector('[data-paper]');
    openPaper(card.dataset.slug,link);
  }));
  previous.addEventListener('click',() => {
    const index=visible.indexOf(active);
    if(index>0) openPaper(visible[index-1].dataset.slug);
  });
  next.addEventListener('click',() => {
    const index=visible.indexOf(active);
    if(index>=0 && index<visible.length-1) openPaper(visible[index+1].dataset.slug);
  });
  close.addEventListener('click',() => dialog.close());
  dialog.addEventListener('click',event => {if(event.target===dialog) dialog.close();});
  dialog.addEventListener('close',() => {
    document.body.classList.remove('reader-is-open');
    const url=new URL(location.href);
    if(url.hash.startsWith('#paper=')) {url.hash='';history.replaceState(null,'',url);}
    if(returnFocus?.isConnected) returnFocus.focus({preventScroll:true});
    active=null;
  });
  update(false);
  if(location.hash.startsWith('#paper=')) {
    try {openPaper(decodeURIComponent(location.hash.slice(7)));}
    catch (_) { /* Invalid fragments must not break browsing. */ }
  }
})();
