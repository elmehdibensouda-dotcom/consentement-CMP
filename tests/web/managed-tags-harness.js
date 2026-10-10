/*
 * Browser regression harness for aman-cmp.js managed tags (P4).
 * Each page declares its placeholders; the harness injects dynamic ones, gives
 * consent, then checks which placeholders the SDK activated and executed.
 * Result: <body data-result="pass|fail"> and a JSON report in #results.
 */
(function () {
  'use strict';
  var NONCE = document.body.dataset.testNonce || '';
  var crossOrigin = location.protocol + '//localhost:' + location.port;
  var choiceKey = 'aman:choice:' + document.body.dataset.propertyId;
  try { localStorage.removeItem(choiceKey); sessionStorage.removeItem(choiceKey); } catch (_) {}
  window.__amanTagRuns = [];
  window.AmanConsentConfig = { version: '1', locale: 'fr', channel: 'web', propertyId: document.body.dataset.propertyId };

  var sdk = document.createElement('script');
  if (NONCE) sdk.setAttribute('nonce', NONCE);
  sdk.src = '../../aman-cmp.js';
  sdk.dataset.amanAllowedScriptOrigins = crossOrigin + ' javascript:alert(1) https://user:pw@cdn.invalid';
  document.head.appendChild(sdk);

  function placeholder(id, src, nonce) {
    var el = document.createElement('script');
    el.type = 'text/plain';
    if (nonce) el.setAttribute('nonce', nonce);
    el.dataset.amanCategory = 'analytics';
    el.dataset.amanSrc = src;
    el.dataset.testId = id;
    document.body.appendChild(el);
  }
  function wait(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }
  function finish(failures, report) {
    document.getElementById('results').textContent = JSON.stringify({ failures: failures, report: report }, null, 2);
    document.body.dataset.result = failures.length ? 'fail' : 'pass';
  }

  async function run() {
    for (var i = 0; i < 50 && !(window.AmanCMP && window.AmanCMP.saveChoice); i += 1) await wait(50);
    if (!window.AmanCMP || !window.AmanCMP.saveChoice) return finish(['SDK did not initialize'], {});
    var expectations = JSON.parse(document.body.dataset.expect);
    var withNonce = NONCE || '';
    placeholder('dynamic-no-nonce', 'fixtures/tag.js?id=dynamic-no-nonce', '');
    placeholder('dynamic-wrong-nonce', 'fixtures/tag.js?id=dynamic-wrong-nonce', 'not-the-page-nonce');
    placeholder('dynamic-matching', 'fixtures/tag.js?id=dynamic-matching', withNonce);
    placeholder('javascript-url', 'javascript:window.__amanTagRuns.push("javascript-url")', withNonce);
    placeholder('data-url', 'data:text/javascript,window.__amanTagRuns.push("data-url")', withNonce);
    placeholder('credentials-url', location.protocol + '//user:pw@' + location.host + '/tests/web/fixtures/tag.js?id=credentials-url', withNonce);
    placeholder('unlisted-origin', 'https://unlisted.invalid/tag.js?id=unlisted-origin', withNonce);
    placeholder('allowed-cross-origin', crossOrigin + '/tests/web/fixtures/tag.js?id=allowed-cross-origin', withNonce);
    await wait(200);

    var failures = [];
    var beforeConsent = window.__amanTagRuns.slice();
    var loadedBefore = Array.prototype.filter.call(document.querySelectorAll('script[data-test-id]'), function (el) {
      return el.dataset.amanLoaded === 'true';
    });
    if (beforeConsent.length || loadedBefore.length) failures.push('a placeholder started before consent');

    window.AmanCMP.saveChoice({ analytics: true });
    await wait(1500);

    var report = {};
    Object.keys(expectations).forEach(function (id) {
      var el = document.querySelector('script[data-test-id="' + id + '"]');
      var activated = !!el && el.dataset.amanLoaded === 'true';
      var executed = window.__amanTagRuns.indexOf(id) !== -1;
      report[id] = { activated: activated, executed: executed };
      if (activated !== expectations[id] || executed !== expectations[id]) {
        failures.push(id + ': expected ' + (expectations[id] ? 'activation' : 'no activation'));
      }
    });
    finish(failures, report);
  }
  run().catch(function (error) { finish(['harness error: ' + error.message], {}); });
})();
