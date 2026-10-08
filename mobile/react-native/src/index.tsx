import React, { useEffect, useState } from 'react';
import {
  AppState,
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

export type AmanLanguage = 'fr' | 'ar';
export type AmanChannel = 'ios' | 'android';
export type AmanStorage = {
  getItem(key: string): Promise<string | null>;
  setItem(key: string, value: string): Promise<void>;
  removeItem(key: string): Promise<void>;
};

type LocalizedText = { fr: string; ar: string };
type PrivacyNotice = {
  controllerName: string;
  contact: string;
  processingReference: string;
  dataCategories: string[];
  recipients: string[];
  transfers: string[];
};
export type AmanPurpose = {
  id: string;
  label: LocalizedText;
  description: LocalizedText;
  required: boolean;
  consentRequired: boolean;
  channels: AmanChannel[];
  vendors?: string[];
};
export type AmanPolicy = {
  schemaVersion: 1;
  propertyId: string;
  policyVersion: string;
  status: 'published';
  purposes: AmanPurpose[];
  languages: AmanLanguage[];
  defaultLanguage?: AmanLanguage;
  retentionDays: number;
  notice: PrivacyNotice;
  noticeTranslations?: Record<AmanLanguage, PrivacyNotice>;
};
export type AmanDecision = {
  propertyId: string;
  policyVersion: string;
  capturedAt: number;
  expiresAt: number;
  channel: AmanChannel;
  action: 'accept_all' | 'reject_all' | 'custom';
  eventId: string;
  purposes: Record<string, boolean>;
};

export type AmanConsentClientOptions = {
  baseUrl: string;
  propertyId: string;
  channel: AmanChannel;
  storage: AmanStorage;
  fetcher?: typeof fetch;
};

const strings = {
  fr: {
    title: 'Vos préférences',
    intro: 'Choisissez les catégories que vous autorisez sur cette application.',
    manage: 'Gérer mes préférences',
    accept: 'Tout accepter',
    reject: 'Tout refuser',
    personalize: 'Personnaliser',
    save: 'Enregistrer mes choix',
    details: 'Informations sur le traitement',
    controller: 'Responsable de traitement',
    contact: 'Contact',
    reference: 'Référence CNDP',
    categories: 'Catégories de données',
    recipients: 'Destinataires',
    transfers: 'Transferts à l’étranger',
    necessary: 'Nécessaire selon le réglage du client',
    choice: 'Inactif jusqu’au choix positif selon le réglage du client',
    active: 'Actif par défaut et révocable',
    loading: 'Chargement des préférences…',
    retry: 'Réessayer',
    storageWarning: 'Votre choix est appliqué dans cette session, mais le stockage local est indisponible. Il pourra être redemandé après la fermeture de l’application.',
  },
  ar: {
    title: 'تفضيلاتك',
    intro: 'اختر الفئات التي تسمح بها في هذا التطبيق.',
    manage: 'إدارة تفضيلاتي',
    accept: 'قبول الكل',
    reject: 'رفض الكل',
    personalize: 'تخصيص',
    save: 'حفظ اختياراتي',
    details: 'معلومات حول المعالجة',
    controller: 'المسؤول عن المعالجة',
    contact: 'جهة الاتصال',
    reference: 'مرجع CNDP',
    categories: 'فئات البيانات',
    recipients: 'الجهات المستفيدة',
    transfers: 'التحويلات إلى الخارج',
    necessary: 'ضروري حسب إعدادات العميل',
    choice: 'يتطلب اختيارًا إيجابيًا حسب إعدادات العميل',
    active: 'نشط افتراضيًا وقابل للرفض',
    loading: 'جارٍ تحميل التفضيلات…',
    retry: 'إعادة المحاولة',
    storageWarning: 'تم تطبيق اختيارك خلال هذه الجلسة، لكن التخزين المحلي غير متاح. قد يُطلب منك الاختيار مجددًا بعد إغلاق التطبيق.',
  },
} as const;

function validateBaseUrl(value: string): string {
  const url = new URL(value);
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) ||
      url.username || url.password || url.search || url.hash) {
    throw new Error('Aman requires an HTTPS API URL (HTTP is allowed only on loopback during development).');
  }
  return url.toString().replace(/\/$/, '');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isText(value: unknown, maxLength: number): value is string {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= maxLength;
}

function isTextList(value: unknown): value is string[] {
  return Array.isArray(value) && value.length > 0 && value.length <= 32 &&
    value.every((item) => isText(item, 200));
}

function isPrivacyNotice(value: unknown): value is PrivacyNotice {
  return isRecord(value) && isText(value.controllerName, 200) &&
    isText(value.contact, 256) && isText(value.processingReference, 120) &&
    isTextList(value.dataCategories) && isTextList(value.recipients) && isTextList(value.transfers);
}

function validatePolicy(value: unknown, propertyId: string, channel: AmanChannel): AmanPolicy {
  if (!isRecord(value) || value.schemaVersion !== 1 || value.status !== 'published' ||
      value.propertyId !== propertyId || typeof value.policyVersion !== 'string' ||
      value.policyVersion.length < 1 || value.policyVersion.length > 64 ||
      !Array.isArray(value.purposes) || value.purposes.length === 0 || value.purposes.length > 64 ||
      !Array.isArray(value.languages) || value.languages.length === 0 || value.languages.length > 2 ||
      !Number.isInteger(value.retentionDays) || (value.retentionDays as number) < 1 ||
      (value.retentionDays as number) > 3650 || !isPrivacyNotice(value.notice)) {
    throw new Error('Aman returned an invalid or unpublished consent policy.');
  }
  const languages = value.languages as unknown[];
  if (languages.some((language) => language !== 'fr' && language !== 'ar') ||
      new Set(languages).size !== languages.length ||
      (value.defaultLanguage !== undefined && !languages.includes(value.defaultLanguage))) {
    throw new Error('Aman policy language settings are invalid.');
  }
  if (value.noticeTranslations !== undefined) {
    const translations = value.noticeTranslations;
    if (!isRecord(translations) || Object.keys(translations).some((key) => key !== 'fr' && key !== 'ar') ||
        Object.keys(translations).some((key) => !languages.includes(key)) ||
        !isPrivacyNotice(translations.fr) || !isPrivacyNotice(translations.ar)) {
      throw new Error('Aman policy notice translations are invalid.');
    }
  }
  const purposeIds = new Set<string>();
  for (const entry of value.purposes) {
    if (!isRecord(entry) || typeof entry.id !== 'string' ||
        !/^[a-z][a-z0-9_-]{1,63}$/.test(entry.id) || purposeIds.has(entry.id) ||
        !isRecord(entry.label) || !isRecord(entry.description) ||
        !isText(entry.label.fr, 120) || !isText(entry.label.ar, 120) ||
        !isText(entry.description.fr, 600) || !isText(entry.description.ar, 600) ||
        typeof entry.required !== 'boolean' || typeof entry.consentRequired !== 'boolean' ||
        (entry.required && entry.consentRequired) || !Array.isArray(entry.channels) ||
        entry.channels.length === 0 || entry.channels.length > 3 ||
        new Set(entry.channels).size !== entry.channels.length || !entry.channels.includes(channel) ||
        entry.channels.some((item) => !['web', 'ios', 'android'].includes(String(item))) ||
        (entry.vendors !== undefined && (!Array.isArray(entry.vendors) || entry.vendors.length > 32 ||
          entry.vendors.some((vendor) => !isText(vendor, 128))))) {
      throw new Error('Aman policy contains an invalid purpose for this app.');
    }
    purposeIds.add(entry.id);
  }
  return value as unknown as AmanPolicy;
}

function validateDecision(value: unknown, policy: AmanPolicy, channel: AmanChannel): AmanDecision {
  if (!isRecord(value) || value.propertyId !== policy.propertyId || value.policyVersion !== policy.policyVersion ||
      value.channel !== channel || typeof value.eventId !== 'string' ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value.eventId) ||
      !['accept_all', 'reject_all', 'custom'].includes(String(value.action)) ||
      !Number.isSafeInteger(value.capturedAt) || !Number.isSafeInteger(value.expiresAt) ||
      (value.expiresAt as number) <= (value.capturedAt as number) || !isRecord(value.purposes)) {
    throw new Error('The saved consent decision is invalid.');
  }
  const capturedAt = value.capturedAt as number;
  const expiresAt = value.expiresAt as number;
  const maximumRetention = policy.retentionDays * 86400000;
  if (capturedAt < 0 || capturedAt > Date.now() + 60_000 ||
      expiresAt - capturedAt > maximumRetention) {
    throw new Error('The saved consent decision is outside the policy retention window.');
  }
  const active = policy.purposes.filter((purpose) => purpose.channels.includes(channel));
  const choices = value.purposes;
  if (Object.keys(choices).length !== active.length ||
      active.some((purpose) => typeof choices[purpose.id] !== 'boolean' ||
        (purpose.required && choices[purpose.id] !== true))) {
    throw new Error('The saved consent decision does not match the published policy.');
  }
  const optionalValues = active.filter((purpose) => !purpose.required).map((purpose) => choices[purpose.id]);
  if ((value.action === 'accept_all' && optionalValues.some((allowed) => allowed !== true)) ||
      (value.action === 'reject_all' && optionalValues.some((allowed) => allowed !== false))) {
    throw new Error('The saved consent action does not match its purpose choices.');
  }
  return value as unknown as AmanDecision;
}

function randomEventId(): string {
  // The API requires a UUID v4. This identifier is only an idempotency key,
  // never an authentication secret or persistent visitor identifier.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (letter) => {
    const random = Math.floor(Math.random() * 16);
    return (letter === 'x' ? random : (random & 0x3) | 0x8).toString(16);
  });
}

/** Loads a published policy and keeps visitor choices in the host app's private storage. */
export class AmanConsentClient {
  readonly baseUrl: string;
  readonly propertyId: string;
  readonly channel: AmanChannel;
  private readonly storage: AmanStorage;
  private readonly fetcher: typeof fetch;
  private policyLoadPromise: Promise<AmanPolicy> | null = null;
  private policyValue: AmanPolicy | null = null;
  private decisionValue: AmanDecision | null = null;
  private decisionStoredDurablyValue = true;
  private listeners = new Set<() => void>();
  private decisionListeners = new Set<(decision: AmanDecision) => void>();

  constructor(options: AmanConsentClientOptions) {
    this.baseUrl = validateBaseUrl(options.baseUrl);
    if (!/^[A-Za-z0-9_-]{1,128}$/.test(options.propertyId)) throw new Error('Invalid Aman property ID.');
    this.propertyId = options.propertyId;
    this.channel = options.channel;
    this.storage = options.storage;
    this.fetcher = options.fetcher ?? fetch;
  }

  get policy(): AmanPolicy | null { return this.policyValue; }
  get decision(): AmanDecision | null { return this.decisionValue; }
  get decisionStoredDurably(): boolean { return this.decisionStoredDurablyValue; }

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onDecision(listener: (decision: AmanDecision) => void): () => void {
    this.decisionListeners.add(listener);
    return () => this.decisionListeners.delete(listener);
  }

  private notify() { this.listeners.forEach((listener) => listener()); }
  private get policyKey() { return `aman.policy.v1.${this.channel}.${this.propertyId}`; }
  private get decisionKey() { return `aman.choice.v1.${this.channel}.${this.propertyId}`; }

  async loadPolicy(): Promise<AmanPolicy> {
    if (this.policyLoadPromise) return this.policyLoadPromise;
    const pending = this.loadPolicyOnce();
    this.policyLoadPromise = pending;
    try {
      return await pending;
    } finally {
      if (this.policyLoadPromise === pending) this.policyLoadPromise = null;
    }
  }

  private async loadPolicyOnce(): Promise<AmanPolicy> {
    let cachedRaw: string | null = null;
    try { cachedRaw = await this.storage.getItem(this.policyKey); } catch { /* Fetch a fresh policy if the cache adapter is unavailable. */ }
    let cached: AmanPolicy | null = null;
    if (cachedRaw) {
      try { cached = validatePolicy(JSON.parse(cachedRaw), this.propertyId, this.channel); } catch { cached = null; }
    }
    let policy: AmanPolicy | null = null;
    let fetchedFresh = false;
    let response: Response | null = null;
    try {
      response = await this.fetcher(`${this.baseUrl}/v1/public/properties/${encodeURIComponent(this.propertyId)}/policy`, {
        method: 'GET', credentials: 'omit', cache: 'no-store', redirect: 'error',
        headers: { Accept: 'application/json' },
      });
    } catch (error) {
      if (this.policyValue) policy = this.policyValue;
      else if (cached) policy = cached;
      else throw error;
    }
    if (response) {
      if (!response.ok) {
        const temporaryFailure = response.status === 408 || response.status === 425 ||
          response.status === 429 || response.status >= 500;
        if (temporaryFailure) {
          if (this.policyValue) policy = this.policyValue;
          else if (cached) policy = cached;
          else throw new Error(`Aman policy request failed (${response.status}).`);
        } else {
          await this.clearPolicyAndDecision();
          throw new Error(`Aman policy request failed (${response.status}).`);
        }
      } else {
        try {
          policy = validatePolicy(await response.json(), this.propertyId, this.channel);
          fetchedFresh = true;
        } catch (error) {
          await this.clearPolicyAndDecision();
          throw error;
        }
      }
    }
    if (!policy) throw new Error('Aman could not load a published consent policy.');
    const previousVersion = this.policyValue?.policyVersion ?? cached?.policyVersion;
    this.policyValue = policy;
    if (previousVersion && previousVersion !== policy.policyVersion) {
      this.decisionValue = null;
      try { await this.storage.removeItem(this.decisionKey); } catch { /* The old choice remains inactive in memory. */ }
    }
    if (fetchedFresh) {
      // A cache write failure must not replace a fresh server policy with stale cached content.
      try { await this.storage.setItem(this.policyKey, JSON.stringify(policy)); } catch { /* Keep the fresh policy in memory. */ }
    }
    await this.restoreDecision(policy);
    this.notify();
    return policy;
  }

  private async clearPolicyAndDecision() {
    this.policyValue = null;
    this.decisionValue = null;
    try { await this.storage.removeItem(this.policyKey); } catch { /* Keep the in-memory client fail-closed. */ }
    try { await this.storage.removeItem(this.decisionKey); } catch { /* Keep the in-memory client fail-closed. */ }
    this.notify();
  }

  private async restoreDecision(policy: AmanPolicy) {
    const inMemoryDecision = this.decisionValue;
    if (inMemoryDecision && !this.decisionStoredDurablyValue) {
      this.restoreInMemoryDecision(inMemoryDecision, policy);
      this.decisionStoredDurablyValue = false;
      return;
    }
    let raw: string | null;
    try { raw = await this.storage.getItem(this.decisionKey); } catch {
      this.restoreInMemoryDecision(inMemoryDecision, policy);
      this.decisionStoredDurablyValue = false;
      return;
    }
    if (!raw) {
      this.decisionValue = null;
      this.decisionStoredDurablyValue = true;
      return;
    }
    this.decisionStoredDurablyValue = true;
    try {
      const saved = validateDecision(JSON.parse(raw), policy, this.channel);
      if (saved.expiresAt <= Date.now()) throw new Error('stale choice');
      this.decisionValue = saved;
      this.decisionStoredDurablyValue = true;
    } catch {
      this.decisionValue = null;
      try { await this.storage.removeItem(this.decisionKey); } catch { /* Invalid choices are not used in memory. */ }
    }
  }

  private restoreInMemoryDecision(decision: AmanDecision | null, policy: AmanPolicy): void {
    if (!decision) {
      this.decisionValue = null;
      return;
    }
    try {
      const validated = validateDecision(decision, policy, this.channel);
      if (validated.expiresAt <= Date.now()) throw new Error('stale choice');
      this.decisionValue = validated;
    } catch {
      this.decisionValue = null;
    }
  }

  isAllowed(purposeId: string): boolean {
    const purpose = this.policyValue?.purposes.find((item) => item.id === purposeId && item.channels.includes(this.channel));
    if (!purpose) return false;
    if (purpose.required) return true;
    const decision = this.decisionValue;
    if (!decision || decision.expiresAt <= Date.now()) return !purpose.consentRequired;
    return decision.purposes[purposeId] ?? !purpose.consentRequired;
  }

  effectivePurposeStates(): Record<string, boolean> {
    return Object.fromEntries((this.policyValue?.purposes ?? [])
      .filter((purpose) => purpose.channels.includes(this.channel))
      .map((purpose) => [purpose.id, this.isAllowed(purpose.id)]));
  }

  async refreshExpiredDecision(): Promise<boolean> {
    if (!this.decisionValue || this.decisionValue.expiresAt > Date.now()) return false;
    this.decisionValue = null;
    try {
      await this.storage.removeItem(this.decisionKey);
      this.decisionStoredDurablyValue = true;
    } catch {
      this.decisionStoredDurablyValue = false;
      /* Expired choices stay inactive in memory. */
    }
    this.notify();
    return true;
  }

  acceptAll(): Promise<AmanDecision> {
    return this.saveChoices(Object.fromEntries((this.policyValue?.purposes ?? []).map((purpose) => [purpose.id, true])), 'accept_all');
  }

  rejectOptional(): Promise<AmanDecision> {
    return this.saveChoices(Object.fromEntries((this.policyValue?.purposes ?? []).map((purpose) => [purpose.id, purpose.required])), 'reject_all');
  }

  async saveChoices(choices: Record<string, boolean>, action: AmanDecision['action'] = 'custom'): Promise<AmanDecision> {
    const policy = this.policyValue;
    if (!policy) throw new Error('Load the published Aman policy before saving a choice.');
    const purposes = Object.fromEntries(policy.purposes.filter((purpose) => purpose.channels.includes(this.channel)).map((purpose) => [
      purpose.id, purpose.required || (typeof choices[purpose.id] === 'boolean' ? choices[purpose.id] : !purpose.consentRequired),
    ]));
    const optionalPurposes = policy.purposes.filter((purpose) =>
      purpose.channels.includes(this.channel) && !purpose.required);
    const recordedAction = action === 'accept_all' && optionalPurposes.every((purpose) => purposes[purpose.id])
      ? 'accept_all'
      : action === 'reject_all' && optionalPurposes.every((purpose) => !purposes[purpose.id])
        ? 'reject_all'
        : 'custom';
    const capturedAt = Date.now();
    const decision: AmanDecision = {
      propertyId: this.propertyId, policyVersion: policy.policyVersion, capturedAt,
      expiresAt: capturedAt + policy.retentionDays * 86400000, channel: this.channel,
      action: recordedAction, eventId: randomEventId(), purposes,
    };
    validateDecision(decision, policy, this.channel);
    try {
      await this.storage.setItem(this.decisionKey, JSON.stringify(decision));
      this.decisionStoredDurablyValue = true;
    } catch {
      this.decisionStoredDurablyValue = false;
    }
    this.decisionValue = decision;
    this.notify();
    this.decisionListeners.forEach((listener) => listener(decision));
    return decision;
  }

  /** Optional, explicit upload. Call only after the client has approved its collection design. */
  async recordDecision(decision: AmanDecision = this.decisionValue as AmanDecision): Promise<void> {
    if (!decision) throw new Error('There is no visitor decision to report.');
    const policy = this.policyValue;
    if (!policy) throw new Error('Load the published Aman policy before reporting a decision.');
    validateDecision(decision, policy, this.channel);
    if (decision.expiresAt <= Date.now()) throw new Error('The consent decision has expired.');
    const response = await this.fetcher(`${this.baseUrl}/v1/public/properties/${encodeURIComponent(this.propertyId)}/consent-events`, {
      method: 'POST', credentials: 'omit', redirect: 'error',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ eventId: decision.eventId, policyVersion: decision.policyVersion,
        channel: decision.channel, action: decision.action, purposes: decision.purposes }),
    });
    if (!response.ok) throw new Error(`Aman decision report failed (${response.status}).`);
  }
}

export type AmanConsentBannerProps = {
  client: AmanConsentClient;
  language?: AmanLanguage;
  onLoadError?: (error: Error) => void;
};

/** A native React Native preference panel. It does not render tags or upload decisions itself. */
export function AmanConsentBanner({ client, language, onLoadError }: AmanConsentBannerProps) {
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [open, setOpen] = useState(!client.decision);
  const [choices, setChoices] = useState<Record<string, boolean>>({});
  useEffect(() => {
    const unsubscribe = client.subscribe(() => setRevision((current) => current + 1));
    client.loadPolicy().then(() => {
      setError(null);
      setOpen(!client.decision);
    }).catch((reason: unknown) => {
      const message = reason instanceof Error ? reason.message : 'Unable to load consent preferences.';
      setError(message);
      onLoadError?.(new Error(message));
    });
    return unsubscribe;
  }, [client, onLoadError]);
  useEffect(() => {
    const refresh = () => { void client.refreshExpiredDecision(); };
    const decision = client.decision;
    const timeout = decision ? setTimeout(refresh, Math.max(0, decision.expiresAt - Date.now())) : undefined;
    return () => {
      if (timeout) clearTimeout(timeout);
    };
  }, [client, revision]);
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (state) => {
      if (state !== 'active') return;
      void (async () => {
        try {
          await client.refreshExpiredDecision();
          await client.loadPolicy();
          setError(null);
        } catch (reason) {
          const message = reason instanceof Error ? reason.message : 'Unable to load consent preferences.';
          setError(message);
          onLoadError?.(new Error(message));
        }
      })();
    });
    return () => subscription.remove();
  }, [client, onLoadError]);
  useEffect(() => {
    if (!client.decision && client.policy) setOpen(true);
  }, [client, revision]);
  const policy = client.policy;
  const lang = language ?? policy?.defaultLanguage ?? policy?.languages[0] ?? 'fr';
  const t = strings[lang];
  const rtl = lang === 'ar';
  if (client.decision && !open) return (
    <View>
      {!client.decisionStoredDurably && <View style={styles.storageWarning} accessibilityRole="alert"><Text style={styles.storageWarningText}>{t.storageWarning}</Text></View>}
      <Pressable accessibilityRole="button" onPress={() => {
        setChoices(client.decision?.purposes ?? client.effectivePurposeStates());
        setEditing(true);
        setOpen(true);
      }} style={styles.manageButton}>
        <Text style={styles.manageText}>{t.manage}</Text>
      </Pressable>
    </View>
  );

  const save = async (action: AmanDecision['action']) => {
    try {
      if (action === 'accept_all') await client.acceptAll();
      else if (action === 'reject_all') await client.rejectOptional();
      else await client.saveChoices(choices, 'custom');
      setError(null);
      setEditing(false);
      setOpen(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to save this choice.');
    }
  };
  if (error && !policy) return (
    <View style={styles.card} accessibilityRole="alert">
      <Text style={styles.body}>{error}</Text>
      <Pressable accessibilityRole="button" onPress={() => {
        setError(null);
        void client.loadPolicy().then(() => {
          setError(null);
          setOpen(!client.decision);
        }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Policy unavailable.'));
      }}><Text style={styles.link}>{t.retry}</Text></Pressable>
    </View>
  );
  if (!policy) return <View style={styles.loading}><ActivityIndicator /><Text>{t.loading}</Text></View>;
  const activePurposes = policy.purposes.filter((purpose) => purpose.channels.includes(client.channel));
  const notice = policy.noticeTranslations?.[lang] ?? policy.notice;
  return (
    <ScrollView style={styles.card} contentContainerStyle={styles.content} accessibilityLabel={t.title}>
      {client.decision && !client.decisionStoredDurably && <View style={styles.storageWarning} accessibilityRole="alert"><Text style={styles.storageWarningText}>{t.storageWarning}</Text></View>}
      <View style={styles.copy}>
        <Text style={[styles.title, rtl && styles.textRtl]}>{t.title}</Text>
        <Text style={[styles.body, rtl && styles.textRtl]}>{t.intro}</Text>
        {error ? <Text accessibilityRole="alert" style={styles.error}>{error}</Text> : null}
      </View>
      {editing && activePurposes.map((purpose) => (
        <View key={purpose.id} style={[styles.purpose, rtl && styles.rtl]}>
          <View style={styles.purposeCopy}>
            <Text style={[styles.label, rtl && styles.textRtl]}>{purpose.label[lang]}</Text>
            <Text style={[styles.description, rtl && styles.textRtl]}>{purpose.description[lang]}</Text>
            <Text style={[styles.hint, rtl && styles.textRtl]}>{purpose.required ? t.necessary : purpose.consentRequired ? t.choice : t.active}</Text>
          </View>
          <Pressable
            accessibilityRole="switch"
            accessibilityLabel={purpose.label[lang]}
            accessibilityState={{ checked: purpose.required || (choices[purpose.id] ?? client.isAllowed(purpose.id)), disabled: purpose.required }}
            disabled={purpose.required}
            onPress={() => setChoices((current) => ({ ...current, [purpose.id]: !(current[purpose.id] ?? client.isAllowed(purpose.id)) }))}
            style={[styles.switch, (purpose.required || (choices[purpose.id] ?? client.isAllowed(purpose.id))) && styles.switchOn]}
          ><Text style={styles.switchText}>{(purpose.required || (choices[purpose.id] ?? client.isAllowed(purpose.id))) ? '✓' : '×'}</Text></Pressable>
        </View>
      ))}
      <View style={styles.notice}>
        <Text style={[styles.label, rtl && styles.textRtl]}>{t.details}</Text>
        {[[t.controller, notice.controllerName], [t.contact, notice.contact], [t.reference, notice.processingReference],
          [t.categories, notice.dataCategories.join(' · ')], [t.recipients, notice.recipients.join(' · ')],
          [t.transfers, notice.transfers.join(' · ')]]
          .map(([label, value]) => <Text key={label} style={[styles.description, rtl && styles.textRtl]}>{label}: {value}</Text>)}
      </View>
      <View style={[styles.actions, rtl && styles.rtl]}>
        {editing ? <>
          <Pressable accessibilityRole="button" onPress={() => save('custom')} style={[styles.button, styles.primary]}><Text style={styles.primaryText}>{t.save}</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={() => save('reject_all')} style={styles.button}><Text>{t.reject}</Text></Pressable>
        </> : <>
          <Pressable accessibilityRole="button" onPress={() => save('reject_all')} style={styles.button}><Text>{t.reject}</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={() => setEditing(true)} style={styles.button}><Text>{t.personalize}</Text></Pressable>
          <Pressable accessibilityRole="button" onPress={() => save('accept_all')} style={[styles.button, styles.primary]}><Text style={styles.primaryText}>{t.accept}</Text></Pressable>
        </>}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#fff', borderColor: '#d8e2da', borderRadius: 14, borderWidth: 1, margin: 16, maxHeight: '90%', padding: 18 },
  content: { gap: 14 },
  loading: { alignItems: 'center', flexDirection: 'row', gap: 10, padding: 18 },
  copy: { gap: 8 },
  title: { color: '#18231f', fontSize: 20, fontWeight: '700' },
  body: { color: '#46524c', fontSize: 14, lineHeight: 21 },
  purpose: { alignItems: 'center', borderTopColor: '#e8eee9', borderTopWidth: 1, flexDirection: 'row', gap: 12, paddingVertical: 12 },
  purposeCopy: { flex: 1, gap: 4 },
  label: { color: '#26362d', fontSize: 13, fontWeight: '600' },
  description: { color: '#58655e', fontSize: 12, lineHeight: 18 },
  hint: { color: '#75807b', fontSize: 10 },
  rtl: { flexDirection: 'row-reverse' },
  textRtl: { textAlign: 'right' },
  switch: { alignItems: 'center', borderColor: '#abb6af', borderRadius: 16, borderWidth: 1, height: 32, justifyContent: 'center', width: 48 },
  switchOn: { backgroundColor: '#176447', borderColor: '#176447' },
  switchText: { color: '#fff', fontWeight: '700' },
  notice: { backgroundColor: '#f5f7f4', borderRadius: 10, gap: 6, padding: 12 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'flex-end' },
  button: { alignItems: 'center', borderColor: '#cbd6cd', borderRadius: 8, borderWidth: 1, justifyContent: 'center', minHeight: 42, paddingHorizontal: 12 },
  primary: { backgroundColor: '#176447', borderColor: '#176447' },
  primaryText: { color: '#fff', fontWeight: '700' },
  link: { color: '#176447', fontWeight: '700', paddingTop: 10 },
  error: { color: '#a53c38', fontSize: 12 },
  manageButton: { alignSelf: 'flex-start', borderColor: '#cbd6cd', borderRadius: 8, borderWidth: 1, margin: 12, paddingHorizontal: 12, paddingVertical: 9 },
  manageText: { color: '#176447', fontSize: 12, fontWeight: '600' },
  storageWarning: { backgroundColor: '#fff8e8', borderColor: '#e7d9ad', borderRadius: 8, borderWidth: 1, marginBottom: 10, padding: 10 },
  storageWarningText: { color: '#705821', fontSize: 12, lineHeight: 18 },
});
