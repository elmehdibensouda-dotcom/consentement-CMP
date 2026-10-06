/*
 * Aman Consent — proof-of-concept browser SDK.
 * This is a local demo foundation, not a production CMP or legal compliance guarantee.
 * Cookie purposes and consentRequired values must be reviewed for each controller.
 */
(function (window, document) {
  'use strict';

  const SDK_SCRIPT = document.currentScript;
  const STORAGE_CONFIG = 'aman:demo:config';
  const STORAGE_CHOICE = 'aman:demo:choice';
  const MEMORY_STORAGE = new Map();
  const DEFAULT_MAX_AGE_MS = 180 * 24 * 60 * 60 * 1000;
  const MANAGED_TAG_SELECTOR = 'script[type="text/plain"][data-aman-src]';
  const DEFAULTS = {
    version: '1',
    locale: 'fr',
    title: 'Votre vie privée, notre priorité',
    message: 'Choisissez les catégories de cookies que vous souhaitez autoriser.',
    color: '#176447',
    categories: [
      { id: 'essential', label: 'Essentiels', description: 'Nécessaires au fonctionnement du site.', required: true, consentRequired: false },
      { id: 'analytics', label: 'Mesure d’audience', description: 'Aide à comprendre la fréquentation du site.', required: false, consentRequired: true },
      { id: 'marketing', label: 'Publicité personnalisée', description: 'Permet de mesurer ou personnaliser des campagnes.', required: false, consentRequired: true }
    ]
  };
  const LABELS = {
    fr: { accept: 'Tout accepter', reject: 'Tout refuser', customize: 'Personnaliser', details: 'Informations détaillées', information: 'Informations sur le traitement', controller: 'Responsable', categories: 'Catégories de données', recipients: 'Destinataires', transfers: 'Transferts à l’étranger', reference: 'Référence CNDP', contact: 'Contact pour exercer vos droits', save: 'Enregistrer mes choix', close: 'Fermer', manage: 'Gérer mes cookies', title: 'Vos préférences', saved: 'Vos préférences ont été enregistrées.', temporary: 'Votre choix s’applique à cet onglet seulement : le navigateur ne l’a pas enregistré durablement.', unavailable: 'Le centre de préférences est temporairement indisponible. Les scripts facultatifs restent désactivés.' },
    ar: { accept: 'قبول الكل', reject: 'رفض الكل', customize: 'تخصيص', details: 'معلومات مفصلة', information: 'معلومات حول المعالجة', controller: 'المسؤول عن المعالجة', categories: 'فئات البيانات', recipients: 'الجهات المستفيدة', transfers: 'التحويلات إلى الخارج', reference: 'مرجع CNDP', contact: 'جهة الاتصال لممارسة حقوقك', save: 'حفظ اختياراتي', close: 'إغلاق', manage: 'إدارة ملفات تعريف الارتباط', title: 'تفضيلاتك', saved: 'تم حفظ تفضيلاتك.', temporary: 'يسري اختيارك في علامة التبويب هذه فقط؛ لم يتم حفظه بشكل دائم.', unavailable: 'مركز التفضيلات غير متاح مؤقتًا. ستظل البرامج النصية الاختيارية معطلة.' }
  };

  function read(key) {
    if (MEMORY_STORAGE.has(key)) {
      try { return JSON.parse(JSON.stringify(MEMORY_STORAGE.get(key))); }
      catch (_) { return null; }
    }
    try {
      const value = window.localStorage.getItem(key);
      if (value !== null) return JSON.parse(value);
    } catch (_) {}
    try {
      const value = window.sessionStorage.getItem(key);
      if (value !== null) return JSON.parse(value);
    } catch (_) {}
    return null;
  }
  function write(key, value) {
    let serialized;
    try {
      serialized = JSON.stringify(value);
      MEMORY_STORAGE.set(key, JSON.parse(serialized));
    } catch (_) { return false; }
    try { window.localStorage.setItem(key, serialized); return true; }
    catch (_) {
      try { window.sessionStorage.setItem(key, serialized); }
      catch (_) {}
      return false;
    }
  }
  function removeStorageKey(key) {
    MEMORY_STORAGE.delete(key);
    try { window.localStorage.removeItem(key); } catch (_) {}
    try { window.sessionStorage.removeItem(key); } catch (_) {}
  }
  function clearDemoData() {
    const prefixes = ['aman:choice:', 'aman:policy:'];
    for (const key of Array.from(MEMORY_STORAGE.keys())) {
      if (key === STORAGE_CONFIG || key === STORAGE_CHOICE || prefixes.some(prefix => key.startsWith(prefix))) {
        MEMORY_STORAGE.delete(key);
      }
    }
    ['localStorage', 'sessionStorage'].forEach(name => {
      try {
        const storage = window[name];
        const keys = [];
        for (let index = 0; index < storage.length; index += 1) {
          const key = storage.key(index);
          if (key && (key === STORAGE_CONFIG || key === STORAGE_CHOICE || prefixes.some(prefix => key.startsWith(prefix)))) keys.push(key);
        }
        keys.forEach(key => storage.removeItem(key));
      } catch (_) {}
    });
  }
  function normalizeLocale(value) {
    const language = String(value || '').trim().toLowerCase().split(/[-_]/, 1)[0];
    return language === 'ar' ? 'ar' : 'fr';
  }
  function config() {
    const stored = read(STORAGE_CONFIG);
    const attributes = SDK_SCRIPT ? SDK_SCRIPT.dataset : {};
    const hostConfig = window.AmanConsentConfig || {};
    const scriptConfig = {};
    if (attributes.amanApiBaseUrl) scriptConfig.apiBaseUrl = attributes.amanApiBaseUrl;
    if (attributes.amanPropertyId) scriptConfig.propertyId = attributes.amanPropertyId;
    if (attributes.amanChannel) scriptConfig.channel = attributes.amanChannel;
    if (attributes.amanLocale) scriptConfig.locale = attributes.amanLocale;
    if (attributes.amanTitle) scriptConfig.title = attributes.amanTitle;
    if (attributes.amanMessage) scriptConfig.message = attributes.amanMessage;
    if (attributes.amanColor) scriptConfig.color = attributes.amanColor;
    if (attributes.amanCollectDecisionEvents !== undefined) {
      scriptConfig.collectDecisionEvents = attributes.amanCollectDecisionEvents === 'true';
    }
    const merged = Object.assign({}, DEFAULTS, stored || {}, scriptConfig, hostConfig);
    merged.localeExplicit = attributes.amanLocale !== undefined ||
      Object.prototype.hasOwnProperty.call(stored || {}, 'locale') ||
      Object.prototype.hasOwnProperty.call(hostConfig, 'locale');
    merged.locale = normalizeLocale(merged.locale);
    return merged;
  }
  function choiceKey(cfg) { return cfg.propertyId ? 'aman:choice:' + cfg.propertyId : STORAGE_CHOICE; }
  function readChoice(cfg) { return read(choiceKey(cfg)); }
  function choiceRetentionMs(cfg) {
    const configuredMs = Math.max(1, Number(cfg.retentionDays) || 180) * 24 * 60 * 60 * 1000;
    return cfg.channel === 'web' ? Math.min(configuredMs, DEFAULT_MAX_AGE_MS) : configuredMs;
  }
  function isRecord(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }
  function hasOnlyKeys(value, allowed) {
    return isRecord(value) && Object.keys(value).every(function (key) { return allowed.includes(key); });
  }
  function validText(value, maximum) {
    return typeof value === 'string' && value.trim().length > 0 && value.length <= maximum;
  }
  function validPrivacyNotice(notice) {
    if (!hasOnlyKeys(notice, ['controllerName', 'contact', 'processingReference', 'dataCategories', 'recipients', 'transfers'])) return false;
    return validText(notice.controllerName, 200) && validText(notice.contact, 256) &&
      validText(notice.processingReference, 120) &&
      ['dataCategories', 'recipients', 'transfers'].every(function (field) {
        return Array.isArray(notice[field]) && notice[field].length > 0 &&
          notice[field].every(function (item) { return validText(item, 200); });
      });
  }
  function validatePublishedPolicy(policy, cfg) {
    if (!hasOnlyKeys(policy, ['schemaVersion', 'propertyId', 'policyVersion', 'status', 'purposes', 'languages', 'defaultLanguage', 'retentionDays', 'notice', 'noticeTranslations']) ||
        policy.schemaVersion !== 1 || policy.status !== 'published' || policy.propertyId !== cfg.propertyId ||
        !validText(policy.policyVersion, 64) || !Number.isInteger(policy.retentionDays) ||
        policy.retentionDays < 1 || policy.retentionDays > 3650 ||
        (cfg.channel === 'web' && policy.retentionDays > 180) ||
        !validPrivacyNotice(policy.notice)) {
      throw new Error('Aman policy does not match the supported schema.');
    }
    const supportedLanguages = ['fr', 'ar'];
    if (!Array.isArray(policy.languages) || policy.languages.length === 0 ||
        new Set(policy.languages).size !== policy.languages.length ||
        !policy.languages.every(function (language) { return supportedLanguages.includes(language); }) ||
        (policy.defaultLanguage !== undefined && !policy.languages.includes(policy.defaultLanguage))) {
      throw new Error('Aman policy has unsupported language settings.');
    }
    if (policy.noticeTranslations !== undefined) {
      if (!hasOnlyKeys(policy.noticeTranslations, ['fr', 'ar']) ||
          !validPrivacyNotice(policy.noticeTranslations.fr) || !validPrivacyNotice(policy.noticeTranslations.ar) ||
          !Object.keys(policy.noticeTranslations).every(function (language) { return policy.languages.includes(language); })) {
        throw new Error('Aman policy has incomplete translated notices.');
      }
    }
    if (!Array.isArray(policy.purposes) || policy.purposes.length === 0) {
      throw new Error('Aman policy must define at least one purpose.');
    }
    const ids = new Set();
    const supportedChannels = ['web', 'ios', 'android'];
    policy.purposes.forEach(function (purpose) {
      if (!hasOnlyKeys(purpose, ['id', 'label', 'description', 'required', 'consentRequired', 'channels', 'vendors']) ||
          typeof purpose.id !== 'string' || !/^[a-z][a-z0-9_-]{1,63}$/.test(purpose.id) || ids.has(purpose.id) ||
          !hasOnlyKeys(purpose.label, ['fr', 'ar']) ||
          !validText(purpose.label.fr, 120) || !validText(purpose.label.ar, 120) ||
          !hasOnlyKeys(purpose.description, ['fr', 'ar']) ||
          !validText(purpose.description.fr, 600) || !validText(purpose.description.ar, 600) ||
          typeof purpose.required !== 'boolean' || typeof purpose.consentRequired !== 'boolean' ||
          (purpose.required && purpose.consentRequired) ||
          !Array.isArray(purpose.channels) || purpose.channels.length === 0 ||
          new Set(purpose.channels).size !== purpose.channels.length ||
          !purpose.channels.every(function (channel) { return supportedChannels.includes(channel); }) ||
          (purpose.vendors !== undefined && (!Array.isArray(purpose.vendors) ||
            !purpose.vendors.every(function (vendor) { return typeof vendor === 'string' && vendor.length <= 128; })))) {
        throw new Error('Aman policy contains an unsupported purpose.');
      }
      ids.add(purpose.id);
    });
    if (!policy.purposes.some(function (purpose) { return purpose.channels.includes(cfg.channel); })) {
      throw new Error('Aman policy does not contain a purpose for this channel.');
    }
    return policy;
  }
  function secureApiBase(value) {
    let url;
    try { url = new URL(String(value), window.location.href); }
    catch (_) { throw new Error('URL de l’API Aman invalide.'); }
    const host = url.hostname.toLowerCase().replace(/^\[|\]$/g, '');
    const loopback = ['localhost', '127.0.0.1', '::1'].includes(host);
    if (url.username || url.password || url.search || url.hash ||
        (url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback))) {
      throw new Error('Aman exige HTTPS, sauf pour les hôtes loopback de développement.');
    }
    return url.href.replace(/\/+$/, '');
  }
  async function loadPublishedPolicy(cfg) {
    if (!/^[A-Za-z0-9_-]{1,128}$/.test(String(cfg.propertyId || ''))) {
      throw new Error('Identifiant de propriété Aman invalide.');
    }
    const cacheKey = 'aman:policy:' + cfg.propertyId;
    const cached = read(cacheKey);
    const headers = {};
    if (cached && cached.etag) headers['If-None-Match'] = cached.etag;
    const base = secureApiBase(cfg.apiBaseUrl);
    let response;
    try {
      response = await fetch(base + '/v1/public/properties/' + encodeURIComponent(cfg.propertyId) + '/policy', {
        method: 'GET', headers, credentials: 'omit', cache: 'no-store', redirect: 'error'
      });
    } catch (error) {
      if (cached && cached.policy && cached.policy.status === 'published') response = null;
      else throw error;
    }
    if (response && response.url) {
      let finalUrl;
      try { finalUrl = new URL(response.url); }
      catch (_) { throw new Error('URL finale de la politique Aman invalide.'); }
      const finalHost = finalUrl.hostname.toLowerCase().replace(/^\[|\]$/g, '');
      const finalLoopback = ['localhost', '127.0.0.1', '::1'].includes(finalHost);
      if (finalUrl.username || finalUrl.password || finalUrl.search || finalUrl.hash ||
          (finalUrl.protocol !== 'https:' && !(finalUrl.protocol === 'http:' && finalLoopback))) {
        throw new Error('Aman refuse une redirection vers une connexion non sécurisée.');
      }
    }
    let policy;
    if (response === null) policy = cached.policy;
    else if (response.status === 304 && cached) policy = cached.policy;
    else if (response.ok) policy = await response.json();
    else throw new Error('Aucune politique Aman publiée pour cette propriété.');
    validatePublishedPolicy(policy, cfg);
    if (response && response.ok) write(cacheKey, { etag: response.headers.get('ETag'), policy });
    const requestedLocale = normalizeLocale(cfg.localeExplicit ? cfg.locale : (policy.defaultLanguage || cfg.locale || 'fr'));
    const locale = policy.languages.includes(requestedLocale) ? requestedLocale : (policy.defaultLanguage || policy.languages[0]);
    const localizedNotice = policy.noticeTranslations && policy.noticeTranslations[locale];
    const channel = cfg.channel || 'web';
    const purposes = (policy.purposes || []).filter(function (purpose) {
      return Array.isArray(purpose.channels) && purpose.channels.includes(channel);
    }).map(function (purpose) {
      return {
        id: purpose.id,
        label: typeof purpose.label === 'string' ? purpose.label : (purpose.label[locale] || purpose.label.fr),
        description: typeof purpose.description === 'string' ? purpose.description : (purpose.description[locale] || purpose.description.fr),
        vendors: Array.isArray(purpose.vendors) ? purpose.vendors : [],
        required: purpose.required === true,
        consentRequired: purpose.consentRequired === true
      };
    });
    return Object.assign({}, cfg, {
      version: policy.policyVersion,
      policyVersion: policy.policyVersion,
      retentionDays: policy.retentionDays,
      notice: localizedNotice || policy.notice,
      locale,
      categories: purposes
    });
  }
  function t(cfg) { return LABELS[cfg.locale === 'ar' ? 'ar' : 'fr']; }
  function validChoice(choice, cfg) {
    if (!choice || typeof choice !== 'object' || Array.isArray(choice)) return false;
    const now = Date.now();
    if (choice.version !== cfg.version || !Number.isFinite(choice.savedAt) ||
        choice.savedAt < 0 || choice.savedAt > now || now - choice.savedAt > choiceRetentionMs(cfg)) return false;
    return !!choice.purposes && typeof choice.purposes === 'object' && !Array.isArray(choice.purposes);
  }
  function currentChoice(cfg) {
    const choice = readChoice(cfg);
    if (!choice) return null;
    if (validChoice(choice, cfg)) return choice;
    removeStorageKey(choiceKey(cfg));
    return null;
  }
  let choiceExpiryTimer = null;
  function scheduleChoiceExpiry(cfg, choice) {
    if (choiceExpiryTimer !== null) window.clearTimeout(choiceExpiryTimer);
    choiceExpiryTimer = null;
    if (!validChoice(choice, cfg)) return;
    const expiry = choice.savedAt + choiceRetentionMs(cfg);
    const delay = Math.max(1, expiry - Date.now() + 1);
    choiceExpiryTimer = window.setTimeout(function () {
      choiceExpiryTimer = null;
      const current = currentChoice(cfg);
      if (current) {
        scheduleChoiceExpiry(cfg, current);
        return;
      }
      applyTags(cfg, null);
      if (!document.querySelector('.aman-banner')) renderBanner(cfg, null);
    }, Math.min(delay, 2147483647));
  }
  function observeChoiceChanges(cfg) {
    window.addEventListener('storage', function (event) {
      const key = choiceKey(cfg);
      if (event.key !== null && event.key !== key) return;
      let choice = null;
      if (event.key === key && event.newValue) {
        try { choice = JSON.parse(event.newValue); }
        catch (_) { choice = null; }
      }
      if (validChoice(choice, cfg)) MEMORY_STORAGE.set(key, choice);
      else { MEMORY_STORAGE.delete(key); choice = null; }
      scheduleChoiceExpiry(cfg, choice);
      applyTags(cfg, choice);
      const banner = document.querySelector('.aman-banner');
      if (choice) {
        if (banner) banner.remove();
      } else if (!banner) renderBanner(cfg, null);
    });
  }
  function consentFor(category, choice) {
    if (category.required) return true;
    if (choice && choice.purposes && Object.prototype.hasOwnProperty.call(choice.purposes, category.id)) {
      return choice.purposes[category.id] === true;
    }
    return category.consentRequired === false;
  }
  function emitConsentUpdate(cfg, choice) {
    const purposes = {};
    cfg.categories.forEach(function (category) {
      purposes[category.id] = consentFor(category, choice);
    });
    const detail = {
      propertyId: cfg.propertyId || null,
      policyVersion: cfg.policyVersion || cfg.version || null,
      channel: cfg.channel || 'web',
      hasUserChoice: !!choice,
      purposes
    };
    document.dispatchEvent(new CustomEvent('aman:consent-update', { detail }));
    try {
      if (typeof window.dataLayer === 'undefined') window.dataLayer = [];
      if (Array.isArray(window.dataLayer)) {
        window.dataLayer.push({ event: 'aman_consent_update', aman: detail });
      }
    } catch (_) {}
  }
  function applyTags(cfg, choice) {
    document.querySelectorAll(MANAGED_TAG_SELECTOR).forEach(function (placeholder) {
      const category = cfg.categories.find(function (item) { return item.id === placeholder.dataset.amanCategory; });
      if (!category || !consentFor(category, choice) || placeholder.dataset.amanLoaded === 'true') return;
      const script = document.createElement('script');
      script.src = placeholder.dataset.amanSrc;
      script.async = true;
      if (SDK_SCRIPT && SDK_SCRIPT.nonce) script.nonce = SDK_SCRIPT.nonce;
      script.dataset.amanLoaded = 'true';
      script.dataset.amanCategory = category.id;
      placeholder.dataset.amanLoaded = 'true';
      placeholder.parentNode.insertBefore(script, placeholder.nextSibling);
      document.dispatchEvent(new CustomEvent('aman:tag-loaded', { detail: { category: category.id } }));
    });
    emitConsentUpdate(cfg, choice);
  }
  let tagObserver = null;
  function containsManagedTag(node) {
    if (!node || node.nodeType !== 1) return false;
    return node.matches(MANAGED_TAG_SELECTOR) || !!node.querySelector(MANAGED_TAG_SELECTOR);
  }
  function observeManagedTags(cfg) {
    if (!window.MutationObserver || !document.documentElement) return;
    tagObserver = new window.MutationObserver(function (records) {
      const changed = records.some(function (record) {
        if (record.type === 'attributes') return containsManagedTag(record.target);
        return Array.prototype.some.call(record.addedNodes, containsManagedTag);
      });
      if (changed) applyTags(cfg, currentChoice(cfg));
    });
    tagObserver.observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['type', 'data-aman-src', 'data-aman-category']
    });
  }
  function createEventId() {
    if (!window.crypto || typeof window.crypto.getRandomValues !== 'function') return null;
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, function (value) { return value.toString(16).padStart(2, '0'); }).join('');
    return hex.slice(0, 8) + '-' + hex.slice(8, 12) + '-' + hex.slice(12, 16) + '-' + hex.slice(16, 20) + '-' + hex.slice(20);
  }
  function recordConsentEvent(cfg, choice, action) {
    if (cfg.collectDecisionEvents !== true || !cfg.apiBaseUrl || !cfg.propertyId || !cfg.policyVersion) return;
    const eventId = createEventId();
    if (!eventId) return;
    let base;
    try { base = secureApiBase(cfg.apiBaseUrl); }
    catch (_) { return; }
    fetch(base + '/v1/public/properties/' + encodeURIComponent(cfg.propertyId) + '/consent-events', {
      method: 'POST',
      credentials: 'omit',
      keepalive: true,
      redirect: 'error',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        eventId: eventId,
        policyVersion: cfg.policyVersion,
        channel: cfg.channel || 'web',
        action: action,
        purposes: choice.purposes
      })
    }).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (result) {
        document.dispatchEvent(new CustomEvent('aman:consent-event-status', {
          detail: {
            state: response.ok ? (result.duplicate ? 'duplicate' : 'recorded') : 'failed',
            status: response.status,
            propertyId: cfg.propertyId
          }
        }));
      });
    }).catch(function () {
      document.dispatchEvent(new CustomEvent('aman:consent-event-status', {
        detail: { state: 'failed', status: 0, propertyId: cfg.propertyId }
      }));
    });
  }
  function make(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }
  function appendNotice(parent, cfg) {
    const notice = cfg.notice;
    if (!notice) return;
    const labels = t(cfg);
    const details = make('details', 'aman-details');
    details.append(make('summary', '', labels.information));
    const list = make('dl', 'aman-notice-list');
    [
      [labels.controller, notice.controllerName],
      [labels.contact, notice.contact],
      [labels.reference, notice.processingReference],
      [labels.categories, notice.dataCategories],
      [labels.recipients, notice.recipients],
      [labels.transfers, notice.transfers]
    ].forEach(function (entry) {
      const value = Array.isArray(entry[1]) ? entry[1].join(', ') : entry[1];
      if (value) list.append(make('dt', '', entry[0]), make('dd', '', value));
    });
    details.append(list);
    parent.append(details);
  }
  function save(purposes, cfg, action) {
    const normalized = {};
    cfg.categories.forEach(function (category) {
      normalized[category.id] = category.required ? true :
        (Object.prototype.hasOwnProperty.call(purposes, category.id) ? purposes[category.id] === true : category.consentRequired === false);
    });
    const value = { version: cfg.version, savedAt: Date.now(), purposes: normalized };
    const storedDurably = write(choiceKey(cfg), value);
    scheduleChoiceExpiry(cfg, value);
    recordConsentEvent(cfg, value, action || 'custom');
    applyTags(cfg, value);
    renderStatus(storedDurably ? t(cfg).saved : t(cfg).temporary, cfg.locale);
    closePanel(false);
    const banner = document.querySelector('.aman-banner');
    if (banner) banner.remove();
    const status = document.getElementById('aman-demo-status');
    if (status) { status.tabIndex = -1; status.focus({ preventScroll: true }); }
    document.dispatchEvent(new CustomEvent('aman:consent-saved', {
      detail: Object.assign({}, value, { storedDurably: storedDurably })
    }));
    return value;
  }
  let activePanel = null;
  let panelFocusOrigin = null;
  function closePanel(restoreFocus) {
    const origin = panelFocusOrigin;
    if (activePanel) activePanel.remove();
    activePanel = null;
    panelFocusOrigin = null;
    if (restoreFocus !== false && origin && origin.isConnected) origin.focus();
  }
  function renderStatus(message, locale) {
    const statusLocale = normalizeLocale(locale);
    let status = document.getElementById('aman-demo-status');
    if (!status) {
      status = make('p', 'aman-status');
      status.id = 'aman-demo-status';
      status.setAttribute('role', 'status');
      status.setAttribute('aria-live', 'polite');
      document.body.append(status);
    }
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.lang = statusLocale;
    status.dir = statusLocale === 'ar' ? 'rtl' : 'ltr';
    status.textContent = message;
  }
  function openPanel(cfg, choice) {
    if (activePanel) return;
    panelFocusOrigin = document.activeElement;
    const labels = t(cfg);
    const rtl = cfg.locale === 'ar';
    const overlay = make('div', 'aman-overlay');
    overlay.setAttribute('role', 'presentation');
    const dialog = make('section', 'aman-dialog');
    dialog.setAttribute('role', 'dialog');
    dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'aman-dialog-title');
    dialog.lang = cfg.locale;
    dialog.tabIndex = -1;
    dialog.dir = rtl ? 'rtl' : 'ltr';
    const header = make('div', 'aman-dialog-head');
    const title = make('h2', '', labels.title); title.id = 'aman-dialog-title';
    const close = make('button', 'aman-close', '×'); close.type = 'button'; close.setAttribute('aria-label', labels.close); close.addEventListener('click', function () { closePanel(); });
    header.append(title, close);
    const rows = make('div', 'aman-options');
    const choices = Object.assign({}, choice ? choice.purposes : {});
    cfg.categories.forEach(function (category) {
      if (!Object.prototype.hasOwnProperty.call(choices, category.id)) {
        choices[category.id] = category.required || category.consentRequired === false;
      }
      const row = make('label', 'aman-option');
      const copy = make('span', 'aman-option-copy');
      copy.append(make('strong', '', category.label), make('small', '', category.description));
      if (category.vendors.length) {
        const vendorText = rtl ? 'الموردون المرتبطون (للاسترشاد): ' : 'Fournisseurs associés (indicatif) : ';
        copy.append(make('small', '', vendorText + category.vendors.join(', ')));
      }
      const input = document.createElement('input');
      input.type = 'checkbox'; input.checked = category.required || choices[category.id] === true;
      input.disabled = !!category.required;
      input.setAttribute('aria-label', category.label);
      input.addEventListener('change', function () { choices[category.id] = input.checked; });
      row.append(copy, input); rows.append(row);
    });
    const actions = make('div', 'aman-dialog-actions');
    const saveButton = make('button', 'aman-button aman-primary', labels.save);
    saveButton.type = 'button'; saveButton.addEventListener('click', function () { save(choices, cfg, 'custom'); });
    actions.append(saveButton);
    dialog.append(header, make('p', 'aman-dialog-note', cfg.message), rows);
    appendNotice(dialog, cfg);
    dialog.append(actions);
    overlay.append(dialog);
    overlay.addEventListener('click', function (event) { if (event.target === overlay) closePanel(); });
    overlay.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        event.preventDefault();
        closePanel();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = Array.prototype.slice.call(dialog.querySelectorAll(
        'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, a[href], [tabindex]:not([tabindex="-1"])'
      )).filter(function (item) { return !item.hidden && item.getClientRects().length > 0; });
      if (!focusable.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    });
    document.body.append(overlay);
    activePanel = overlay;
    close.focus();
  }
  function renderBanner(cfg, currentChoice) {
    const labels = t(cfg);
    const banner = make('section', 'aman-banner');
    banner.setAttribute('aria-label', cfg.title);
    banner.lang = cfg.locale;
    banner.dir = cfg.locale === 'ar' ? 'rtl' : 'ltr';
    const textBlock = make('div', 'aman-copy');
    textBlock.append(make('strong', 'aman-title', cfg.title), make('span', 'aman-message', cfg.message));
    if (cfg.notice) {
      const infoLink = make('button', 'aman-link', labels.details);
      infoLink.type = 'button';
      infoLink.addEventListener('click', function () { openPanel(cfg, currentChoice); });
      textBlock.append(infoLink);
    }
    const actions = make('div', 'aman-actions');
    const accept = make('button', 'aman-button aman-primary', labels.accept);
    const reject = make('button', 'aman-button aman-secondary', labels.reject);
    const customize = make('button', 'aman-button aman-secondary', labels.customize);
    accept.type = reject.type = customize.type = 'button';
    accept.addEventListener('click', function () { const all = {}; cfg.categories.forEach(function (item) { all[item.id] = true; }); save(all, cfg, 'accept_all'); banner.remove(); });
    reject.addEventListener('click', function () {
      const none = {};
      cfg.categories.forEach(function (item) { none[item.id] = !!item.required; });
      save(none, cfg, 'reject_all');
      banner.remove();
    });
    customize.addEventListener('click', function () { openPanel(cfg, currentChoice); });
    actions.append(accept, reject, customize);
    banner.append(textBlock, actions);
    document.body.append(banner);
  }
  function addStyles() {
    if (document.getElementById('aman-cmp-style')) return;
    const style = make('style'); style.id = 'aman-cmp-style';
    if (SDK_SCRIPT && SDK_SCRIPT.nonce) style.nonce = SDK_SCRIPT.nonce;
    style.textContent = `
      .aman-banner,.aman-dialog,.aman-status{font-family:Arial,Helvetica,sans-serif;color:#18231f;box-sizing:border-box}
      .aman-banner *,.aman-dialog *{box-sizing:border-box}
      .aman-banner{position:fixed;z-index:2147483000;left:18px;right:18px;bottom:18px;max-width:980px;margin:auto;background:#fff;border:1px solid #dfe6df;border-radius:14px;padding:18px;box-shadow:0 12px 36px #15241b30;display:flex;align-items:center;justify-content:space-between;gap:18px}
      .aman-copy{display:grid;gap:6px;max-width:560px}.aman-title{font-size:15px}.aman-message{font-size:12px;line-height:1.5;color:#59665e}.aman-link{justify-self:start;border:0;background:transparent;padding:2px 0;color:var(--aman-color,#176447);text-decoration:underline;font-size:11px;cursor:pointer}
      .aman-actions,.aman-dialog-actions{display:flex;gap:8px;flex-wrap:wrap}.aman-button{min-height:40px;padding:9px 13px;border-radius:8px;border:1px solid #cbd5cd;background:#fff;color:#203228;font-size:12px;font-weight:600;cursor:pointer}.aman-button:focus-visible,.aman-close:focus-visible{outline:3px solid #8dbb9b;outline-offset:2px}.aman-primary{background:var(--aman-color,#176447);border-color:var(--aman-color,#176447);color:#fff}.aman-overlay{position:fixed;z-index:2147483001;inset:0;background:#10201680;display:grid;place-items:center;padding:18px}.aman-dialog{width:min(100%,500px);max-height:min(90vh,700px);overflow:auto;background:#fff;border-radius:15px;padding:20px;box-shadow:0 20px 60px #0003}.aman-dialog-head{display:flex;align-items:center;justify-content:space-between;gap:14px}.aman-dialog h2{font-size:18px;margin:0}.aman-close{border:0;background:#f2f5f2;border-radius:8px;width:32px;height:32px;font-size:20px;cursor:pointer}.aman-dialog-note{font-size:12px;line-height:1.5;color:#59665e}.aman-options{border-top:1px solid #e7ebe5}.aman-option{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:13px 2px;border-bottom:1px solid #e7ebe5;cursor:pointer}.aman-option-copy{display:grid;gap:5px}.aman-option-copy strong{font-size:12px}.aman-option-copy small{font-size:11px;line-height:1.4;color:#75807b}.aman-option input{accent-color:var(--aman-color,#176447);width:18px;height:18px}.aman-dialog-actions{justify-content:flex-end;margin-top:16px}.aman-manage{position:fixed;z-index:2147482999;left:15px;bottom:15px;border:1px solid #cbd5cd;border-radius:999px;background:#fff;padding:10px 14px;color:#203228;font:600 11px Arial,sans-serif;box-shadow:0 4px 16px #15241b1a;cursor:pointer}.aman-demo-status,.aman-status{min-height:18px;color:#176447;font:12px Arial,sans-serif;text-align:center;margin:10px}.aman-demo-tag-state{font:11px Arial,sans-serif;color:#5b675f}
      .aman-details{border-top:1px solid #e7ebe5;padding:12px 0;font-size:11px}.aman-details summary{font-weight:700;cursor:pointer;color:#31483a}.aman-notice-list{display:grid;grid-template-columns:minmax(100px,.5fr) 1fr;gap:7px 12px;margin:12px 0 0}.aman-notice-list dt{font-weight:650;color:#55635a}.aman-notice-list dd{margin:0;color:#657169;line-height:1.45;overflow-wrap:anywhere}
      @media(max-width:640px){.aman-banner{left:10px;right:10px;bottom:10px;display:block;padding:15px}.aman-actions{display:grid;grid-template-columns:1fr 1fr;margin-top:12px}.aman-actions .aman-primary{grid-column:1/-1}.aman-button{min-height:42px}.aman-copy{max-width:none}}
    `;
    document.head.append(style);
  }
  async function init() {
    let cfg = config();
    addStyles();
    document.documentElement.style.setProperty('--aman-color', cfg.color || DEFAULTS.color);
    if (cfg.apiBaseUrl && cfg.propertyId) {
      try { cfg = await loadPublishedPolicy(cfg); }
      catch (_) {
        renderStatus(t(cfg).unavailable, cfg.locale);
        document.dispatchEvent(new CustomEvent('aman:initialization-error', {
          detail: { propertyId: cfg.propertyId || null }
        }));
        return;
      }
    }
    const choice = currentChoice(cfg);
    scheduleChoiceExpiry(cfg, choice);
    observeManagedTags(cfg);
    observeChoiceChanges(cfg);
    applyTags(cfg, choice);
    if (!choice) renderBanner(cfg, null);
    const manage = make('button', 'aman-manage', t(cfg).manage);
    manage.type = 'button'; manage.addEventListener('click', function () { openPanel(cfg, currentChoice(cfg)); });
    document.body.append(manage);
    window.AmanCMP = Object.assign(window.AmanCMP || {}, {
      openPreferences: function () { openPanel(cfg, currentChoice(cfg)); },
      getChoice: function () { return currentChoice(cfg); },
      saveChoice: function (purposes) { return save(purposes || {}, cfg); }
    });
  }
  window.AmanCMP = Object.assign(window.AmanCMP || {}, {
    setConfig: function (value) { return write(STORAGE_CONFIG, value); },
    getConfig: config,
    clearDemoData: clearDemoData
  });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})(window, document);
