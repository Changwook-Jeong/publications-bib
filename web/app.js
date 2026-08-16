(() => {
  const filters = [...document.querySelectorAll('.filter')];
  const publications = [...document.querySelectorAll('.publication')];
  const yearSections = [...document.querySelectorAll('.year-section')];
  const search = document.querySelector('#publication-search');
  const emptyState = document.querySelector('#empty-state');
  let activeFilter = 'all';

  Object.entries(window.PUBLICATION_COUNTS || {}).forEach(([key, value]) => {
    const count = document.querySelector(`[data-count="${key}"]`);
    if (count) count.textContent = value;
  });

  const update = () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    publications.forEach((item) => {
      const categoryMatches = activeFilter === 'all' || item.dataset.category === activeFilter;
      const searchMatches = !query || item.dataset.search.includes(query);
      item.hidden = !(categoryMatches && searchMatches);
      if (!item.hidden) visible += 1;
    });
    yearSections.forEach((section) => {
      section.hidden = !section.querySelector('.publication:not([hidden])');
    });
    emptyState.hidden = visible !== 0;
  };

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      activeFilter = button.dataset.filter;
      filters.forEach((candidate) => candidate.classList.toggle('active', candidate === button));
      update();
    });
  });

  search.addEventListener('input', update);

  document.addEventListener('click', async (event) => {
    const button = event.target.closest('.copy-key');
    if (!button) return;
    const original = button.textContent;
    try {
      await navigator.clipboard.writeText(button.dataset.key);
      button.textContent = 'Copied';
    } catch {
      button.textContent = button.dataset.key;
    }
    window.setTimeout(() => { button.textContent = original; }, 1400);
  });
})();
