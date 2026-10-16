// The embed view is a self-contained Home section. Keep Google Sites open when
// a reader opens a full summary; the standalone preview uses normal navigation.
if (document.documentElement.classList.contains('embed')) {
  for (const link of document.querySelectorAll('.summary-link')) {
    link.target = '_blank';
    link.rel = 'noopener';
  }
}
