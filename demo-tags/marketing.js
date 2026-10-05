(function (document) {
  const dot = document.getElementById('marketing-dot');
  const state = document.getElementById('marketing-state');
  function render(choice) {
    const allowed = !choice || !choice.purposes || choice.purposes.marketing !== false;
    if (dot) dot.classList.toggle('on', allowed);
    if (state) state.textContent = allowed
      ? 'Publicité personnalisée : exemple local actif selon le choix Aman'
      : 'Publicité personnalisée : exemple local désactivé selon le choix Aman';
  }
  const choice = window.AmanCMP && window.AmanCMP.getChoice();
  render(choice);
  document.addEventListener('aman:consent-update', function (event) { render(event.detail); });
})(document);
