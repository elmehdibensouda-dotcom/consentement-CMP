(function (document) {
  const dot = document.getElementById('analytics-dot');
  const state = document.getElementById('analytics-state');
  function render(choice) {
    const allowed = !choice || !choice.purposes || choice.purposes.analytics !== false;
    if (dot) dot.classList.toggle('on', allowed);
    if (state) state.textContent = allowed
      ? 'Mesure d’audience : exemple local actif selon le choix Aman'
      : 'Mesure d’audience : exemple local désactivé selon le choix Aman';
  }
  const choice = window.AmanCMP && window.AmanCMP.getChoice();
  render(choice);
  document.addEventListener('aman:consent-update', function (event) { render(event.detail); });
})(document);
