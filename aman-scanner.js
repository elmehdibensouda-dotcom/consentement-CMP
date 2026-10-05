/* Aman local inventory helper. Paste into DevTools on a domain you are authorized to assess. */
(() => {
  const ROOT_ID = '__aman_inventory_root__';
  const previous = document.getElementById(ROOT_ID);
  if (previous) {
    previous.shadowRoot?.querySelector('aside')?.focus();
    return;
  }

  const cleanURL = (raw) => {
    try {
      const url = new URL(raw, location.href);
      if (!['http:', 'https:'].includes(url.protocol)) return null;
      return `${url.origin}${url.pathname}`;
    } catch (_) {
      return null;
    }
  };
  const pageURL = cleanURL(location.href);
  const pageOrigin = location.origin;
  const items = [];
  const markedScriptURLs = new Set();
  const add = (kind, raw, detail = '', amanControl = null) => {
    const url = cleanURL(raw);
    if (!url) return;
    const item = {
      kind,
      url,
      origin: new URL(url).origin,
      firstParty: new URL(url).origin === pageOrigin,
      detail,
      classification: 'à examiner'
    };
    if (amanControl) item.amanControl = amanControl;
    items.push(item);
  };

  for (const script of document.scripts) {
    const placeholder = script.type === 'text/plain' && script.dataset.amanSrc;
    if (script.dataset.amanCategory && script.src) {
      const url = cleanURL(script.src);
      if (url) markedScriptURLs.add(url);
      add('Script', script.src, `Marqueur data-aman-category=${script.dataset.amanCategory}; ${script.dataset.amanLoaded === 'true' ? 'script injecté' : 'état de chargement à vérifier'}`, 'marker_present');
    } else if (placeholder) {
      const category = script.dataset.amanCategory;
      const url = cleanURL(script.dataset.amanSrc);
      if (url) markedScriptURLs.add(url);
      add('Espace de script Aman', script.dataset.amanSrc,
        category ? `Marqueur présent pour ${category}; ${script.dataset.amanLoaded === 'true' ? 'script signalé comme injecté' : 'espace inerte observé'}` : 'Espace inerte sans identifiant de finalité',
        category ? 'marker_present' : 'marker_missing');
    }
    else if (script.src) add('Script', script.src, script.type || 'JavaScript', 'marker_missing');
    else items.push({
      kind: 'Script inline', url: pageURL || `${pageOrigin}/`, origin: pageOrigin,
      firstParty: true, detail: `Code inline non copié; type ${script.type || 'JavaScript'}`,
      classification: 'à examiner', amanControl: 'marker_missing'
    });
  }
  for (const frame of document.querySelectorAll('iframe[src]')) add('Iframe', frame.src, 'Frame intégré; mécanisme de contrôle à examiner séparément');
  for (const entry of performance.getEntriesByType('resource')) {
    if (['script', 'xmlhttprequest', 'fetch'].includes(entry.initiatorType)) {
      const control = entry.initiatorType === 'script'
        ? (markedScriptURLs.has(cleanURL(entry.name)) ? 'marker_present' : 'marker_missing')
        : null;
      add(`Réseau · ${entry.initiatorType}`, entry.name, 'Ressource observée depuis le chargement de la page', control);
    }
  }
  const seen = new Set();
  const uniqueItems = items.filter((item) => {
    const key = `${item.kind}\u0000${item.url}\u0000${item.detail}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const cookieNames = document.cookie.split(';').map((part) => part.trim().split('=')[0])
    .filter(Boolean).map((name) => {
      try { return decodeURIComponent(name); } catch (_) { return name; }
    });
  const cookieItems = cookieNames.map((name) => ({ name, classification: 'à examiner' }));

  const host = document.createElement('div');
  host.id = ROOT_ID;
  const shadow = host.attachShadow({ mode: 'open' });
  const style = document.createElement('style');
  style.textContent = `
    :host{all:initial;position:fixed;inset:auto 18px 18px auto;z-index:2147483647;color:#1b2922;font:14px/1.45 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    *{box-sizing:border-box}aside{width:min(760px,calc(100vw - 36px));max-height:min(78vh,760px);display:flex;flex-direction:column;background:#fff;border:1px solid #dbe4dc;border-radius:14px;box-shadow:0 16px 60px #10241c55;overflow:hidden}
    header{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;padding:16px 18px;border-bottom:1px solid #e8eee8;background:#f7faf6}h2{margin:0;font-size:17px}header p{margin:5px 0 0;color:#64736a;font-size:12px}.close{border:1px solid #dce5dc;border-radius:8px;padding:7px 10px;background:white;color:#293a30;cursor:pointer}
    .notice{margin:12px 16px 0;padding:10px 12px;border-radius:9px;background:#fff7e8;border:1px solid #efe0bb;color:#6b5929;font-size:11px}.meta{padding:10px 16px;color:#637168;font-size:11px}.table-wrap{overflow:auto;padding:0 16px 12px}table{border-collapse:collapse;width:100%;font-size:11px}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #edf1ed;padding:8px 7px}th{position:sticky;top:0;background:#fff;color:#66746b;font-weight:650}td.url{max-width:330px;overflow-wrap:anywhere;color:#234935}select{max-width:130px;border:1px solid #dce5dc;border-radius:6px;padding:5px;background:#fff;color:#26362c;font:inherit}
    .cookies{padding:4px 18px 12px;color:#55645a;font-size:11px}.cookies b{color:#25382c}.actions{display:flex;align-items:center;gap:8px;padding:12px 16px;border-top:1px solid #e8eee8;background:#fbfcfa}.actions button{border:1px solid #dce5dc;background:#fff;border-radius:8px;padding:8px 11px;color:#25382c;font:600 11px system-ui;cursor:pointer}.actions .primary{background:#176447;border-color:#176447;color:white}.status{font-size:11px;color:#176447}.empty{padding:22px;color:#64736a;text-align:center;font-size:12px}
    @media(max-width:560px){:host{inset:auto 8px 8px}.table-wrap{padding:0 9px 10px}th,td{padding:7px 4px}td.url{max-width:170px}.notice,.meta,.cookies{margin-left:9px;margin-right:9px;padding-left:9px;padding-right:9px}}
  `;
  const panel = document.createElement('aside');
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Inventaire local Aman');
  panel.tabIndex = -1;
  const header = document.createElement('header');
  const heading = document.createElement('div');
  const title = document.createElement('h2');
  title.textContent = 'Inventaire local de la page';
  const sub = document.createElement('p');
  sub.textContent = 'Aman · lecture seule · résultats conservés dans cet onglet';
  heading.append(title, sub);
  const close = document.createElement('button');
  close.type = 'button';
  close.className = 'close';
  close.textContent = 'Fermer';
  header.append(heading, close);
  const notice = document.createElement('div');
  notice.className = 'notice';
    notice.textContent = 'Analyse ponctuelle du chargement actuel. Le marqueur direct Aman est un signal DOM, pas une preuve de blocage; un gestionnaire de balises peut appliquer d’autres contrôles. Les valeurs des cookies ne sont jamais lues; les cookies HttpOnly ne sont pas visibles. Aucun résultat n’est envoyé à Aman. Réexécute après les parcours et interactions à examiner.';
  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = `Page : ${pageURL || location.origin} · Analyse : ${new Date().toLocaleString()}`;
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  if (uniqueItems.length) {
    const table = document.createElement('table');
    const head = document.createElement('thead');
    const headerRow = document.createElement('tr');
    ['Type', 'Adresse observée', 'Origine', 'Signal Aman direct', 'Détail', 'Classement manuel'].forEach((label) => {
      const th = document.createElement('th');
      th.textContent = label;
      headerRow.append(th);
    });
    head.append(headerRow);
    const body = document.createElement('tbody');
    for (const item of uniqueItems) {
      const row = document.createElement('tr');
      const type = document.createElement('td');
      type.textContent = item.kind;
      const address = document.createElement('td');
      address.className = 'url';
      address.textContent = item.url;
      const origin = document.createElement('td');
      origin.textContent = item.firstParty ? 'Première partie' : 'Tiers';
      const control = document.createElement('td');
      control.textContent = item.amanControl === 'marker_present' ? 'Marqueur repéré' : item.amanControl === 'marker_missing' ? 'Aucun marqueur repéré' : 'Non évalué';
      const detail = document.createElement('td');
      detail.textContent = item.detail || '—';
      const classification = document.createElement('td');
      const select = document.createElement('select');
      select.setAttribute('aria-label', `Classer ${item.kind} ${item.url}`);
      ['à examiner', 'essentiel', 'mesure d’audience', 'personnalisation', 'publicité'].forEach((optionText) => {
        const option = document.createElement('option');
        option.value = optionText;
        option.textContent = optionText;
        select.append(option);
      });
      select.addEventListener('change', () => { item.classification = select.value; });
      classification.append(select);
      row.append(type, address, origin, control, detail, classification);
      body.append(row);
    }
    table.append(head, body);
    wrap.append(table);
  } else {
    const empty = document.createElement('div');
    empty.className = 'empty';
    empty.textContent = 'Aucun script, iframe ou appel réseau de type script/fetch/XHR observé.';
    wrap.append(empty);
  }
  const cookieLine = document.createElement('section');
  cookieLine.className = 'table-wrap';
  const cookieTitle = document.createElement('h3');
  cookieTitle.textContent = `Noms de cookies lisibles (${cookieItems.length})`;
  cookieLine.append(cookieTitle);
  if (cookieItems.length) {
    const table = document.createElement('table');
    const head = document.createElement('thead');
    const headerRow = document.createElement('tr');
    ['Nom du cookie', 'Classement manuel'].forEach((label) => {
      const th = document.createElement('th');
      th.textContent = label;
      headerRow.append(th);
    });
    head.append(headerRow);
    const body = document.createElement('tbody');
    for (const item of cookieItems) {
      const row = document.createElement('tr');
      const name = document.createElement('td');
      name.textContent = item.name;
      const classification = document.createElement('td');
      const select = document.createElement('select');
      select.setAttribute('aria-label', `Classer le cookie ${item.name}`);
      ['à examiner', 'essentiel', 'mesure d’audience', 'personnalisation', 'publicité'].forEach((optionText) => {
        const option = document.createElement('option');
        option.value = optionText;
        option.textContent = optionText;
        select.append(option);
      });
      select.addEventListener('change', () => { item.classification = select.value; });
      classification.append(select);
      row.append(name, classification);
      body.append(row);
    }
    table.append(head, body);
    cookieLine.append(table);
  } else {
    const emptyCookies = document.createElement('p');
    emptyCookies.textContent = 'Aucun nom de cookie accessible sur cette page.';
    cookieLine.append(emptyCookies);
  }
  const actions = document.createElement('div');
  actions.className = 'actions';
  const copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'primary';
  copy.textContent = 'Copier le rapport JSON';
  const download = document.createElement('button');
  download.type = 'button';
  download.textContent = 'Télécharger JSON';
  const status = document.createElement('span');
  status.className = 'status';
  const report = () => ({
    schema: 'aman-local-inventory-v1',
    scannedAt: new Date().toISOString(),
    page: pageURL,
    scope: 'current-page-only; no network upload',
    limitations: ['cookie values are not read', 'HttpOnly cookies are invisible', 'single page-load snapshot', 'inventory requires human review'],
    cookies: cookieItems,
    resources: uniqueItems
  });
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(report(), null, 2));
      status.textContent = 'Rapport copié dans le presse-papiers.';
    } catch (_) {
      status.textContent = 'Presse-papiers indisponible. Utilise Télécharger JSON.';
    }
  });
  download.addEventListener('click', () => {
    const blob = new Blob([JSON.stringify(report(), null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `aman-inventaire-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
    status.textContent = 'Rapport téléchargé.';
  });
  close.addEventListener('click', () => host.remove());
  actions.append(copy, download, status);
  panel.append(header, notice, meta, wrap, cookieLine, actions);
  shadow.append(style, panel);
  (document.body || document.documentElement).append(host);
  panel.focus();
  window.AmanLocalInventory = report;
})();
