// Records that a managed placeholder was activated and executed.
(function () {
  var id = new URL(document.currentScript.src).searchParams.get('id');
  window.__amanTagRuns = window.__amanTagRuns || [];
  window.__amanTagRuns.push(id);
})();
