# Aman Consent Android SDK

This Gradle project contains the `aman-consent` Android library module and a small integration sample app. The SDK currently targets Android API 23+ and reads the public, published Aman policy for one property. It stores choices in app-private `SharedPreferences`; it does not upload them automatically. An explicit API call can report a user-submitted choice after the client approves the collection model.

## Build locally

Requirements: JDK 17, Android SDK platform 36, and Gradle 9.6. This repository does not include the Gradle wrapper JAR or launcher scripts, so use an installed Gradle or configure Android Studio with those tools.

```sh
gradle :aman-consent:assembleRelease
gradle :sample:assembleDebug
```

Le workflow GitHub Actions `Product validation` compile ces deux cibles. Un lancement manuel du workflow joint l’AAR, l’APK d’exemple et le tarball React Native dans un artefact de prévisualisation conservé 14 jours. Vérifier `SHA256SUMS` avec `shasum -a 256 -c SHA256SUMS` sur macOS ou `sha256sum -c SHA256SUMS` sur Linux, puis consulter `BUILD-INFO.txt` pour confirmer le commit source et l’exécution. Ces fichiers permettent de détecter une corruption après téléchargement; ils ne sont pas signés comme release ni publiés dans un dépôt Maven.

The library AAR is produced at `aman-consent/build/outputs/aar/aman-consent-release.aar`. To create a local Maven repository for inspection or internal distribution:

```sh
gradle :aman-consent:publish
```

The local publication is written below `aman-consent/build/repository/`; change the repository block and credentials through the consuming organization's approved artifact repository before distributing releases.

## Integrate from an Android application

For a source checkout, include `:aman-consent` as a Gradle project module. For an internal artifact repository, use the coordinates `ma.aman:aman-consent-android:0.1.0` after publishing a reviewed release. The app must have network access to the published policy endpoint; the library manifest declares Android's `INTERNET` permission. Remote policy endpoints must use HTTPS. HTTP is accepted only for loopback development hosts (`localhost`, `127.0.0.1`, and `::1`).

Avant d’utiliser ce code, désactive l’auto-initialisation et l’auto-collecte de chaque SDK facultatif dans sa configuration Android. Le callback intervient après le démarrage de l’application ; `startAnalyticsIfNotStarted()` doit initialiser le SDK seulement si l’état est autorisé. `stopAnalyticsIfSupported()` ne peut pas annuler les données déjà envoyées ni décharger une bibliothèque native.

```kotlin
private val policyClient = AmanConsentAPIClient(applicationContext)
private var consent: AmanConsentManager? = null
private var policyRequestId = 0L

override fun onResume() {
    super.onResume()
    consent?.refreshExpiredDecision()
    // Démarrer fermé. Les SDK facultatifs doivent déjà être configurés sans auto-initialisation.
    stopAnalyticsIfSupported()
    val requestId = ++policyRequestId
    policyClient.fetchPublishedPolicy("https://cmp.example.ma", "PROPERTY_ID") { result ->
        runOnUiThread {
            if (requestId != policyRequestId) return@runOnUiThread
            result.onSuccess { policy ->
                val current = consent ?: AmanConsentManager(applicationContext, policy).also { created ->
                    consent = created
                    created.addEffectivePurposeStatesChangedListener { states ->
                        runOnUiThread {
                            if (states["analytics"] == true) startAnalyticsIfNotStarted()
                            else stopAnalyticsIfSupported()
                        }
                    }
                }
                current.updatePolicy(policy)
                if (current.decision == null) current.showConsentDialog(this)
                if (current.isAllowed("analytics")) startAnalyticsIfNotStarted()
            }.onFailure {
                consent?.markPolicyUnavailable()
                stopAnalyticsIfSupported()
                showPolicyRetry()
            }
        }
    }
}
```

Policy and decision API callbacks run on the Android main thread by default. All `AmanConsentAPIClient` instances share one single-thread network executor by default, so recreating an `Activity` does not leave one worker thread per instance and requests retain their execution order. Pass a custom `executor` when the host needs a different network scheduling policy, or a custom `callbackExecutor` when it needs another callback thread; network work always stays off the UI thread. Effective-state callbacks run on the thread that saved the choice or called `updatePolicy`; dispatch UI and SDK lifecycle work to the main thread. The host app is responsible for wiring each purpose to its actual SDK start/stop lifecycle and for describing third-party SDK practices in its platform disclosures. `initiallyEnabled` explicitly controls the state before a valid visitor choice; `consentRequired` separately indicates that a positive choice must precede activation. Legacy policies without `initiallyEnabled` start optional purposes disabled. The controller and its legal/DPO team must validate the classification and initial state before publication; these settings are not a legal classification by Aman. Aman cannot unload a native library that the host initialized earlier.

Before caching or applying a policy, the client rejects unknown schema versions, unsupported languages or purposes, contradictory purpose rules, and retention periods outside the shared schema limits. If `defaultLanguage` is absent, the first declared language is used.

The client uses its last valid cache only for transport errors or temporary HTTP responses (`408`, `425`, `429`, or `5xx`). A non-temporary response (including `404`) or invalid policy clears the cached policy and returns `Result.failure`. When a fetch fails, call `markPolicyUnavailable()` on the existing manager and stop optional SDKs; the method clears the saved choice, dismisses an open consent dialog, and makes optional `isAllowed(...)` checks return `false` until a valid `updatePolicy(...)`. Show a retry path. A valid cached policy is returned as success for temporary outages.

Without the optional `language` argument, `showConsentDialog` uses `defaultLanguage` from the published policy (`fr` or `ar`). The host application can still pass a language explicitly when its own language preference should take precedence.

Call `showConsentDialog` on the Android main thread. Repeated calls while the same consent dialog is visible are ignored, which lets an app safely request the dialog from overlapping policy refresh callbacks without stacking duplicate windows.

Translated notice content is read from `noticeTranslations.fr` and `noticeTranslations.ar`; the dialog selects the block matching its display language and falls back to the legacy `notice` field. The client must supply and review its content in every language it offers.

`addEffectivePurposeStatesChangedListener` receives the effective state after a saved choice and after `updatePolicy`. If a newly fetched policy invalidates the saved choice, it sends the new policy defaults so the host can stop or start SDKs accordingly. This state callback is not a user decision and must not be uploaded as one. Apply `isAllowed(...)` once after manager creation because listener registration does not immediately invoke the listener.

The manager schedules an effective-state update when a saved choice expires while the process is active. Also refresh it when the app returns to the foreground so an expiry during suspension is applied before the host resumes optional SDKs:

```kotlin
override fun onResume() {
    super.onResume()
    consentManager?.refreshExpiredDecision()
}
```

Connect `addEffectivePurposeStatesChangedListener` to the actual start/stop calls for each optional SDK. Expiration clears the local choice and notifies this state listener, but does not call `addConsentChangedListener`; do not upload it as a new visitor decision.

After fetching a newer published policy, update the existing manager so the state listener can reconcile the host SDKs:

```kotlin
policyClient.fetchPublishedPolicy(apiBaseUrl, propertyId) { result ->
    result.onSuccess { refreshedPolicy ->
        runOnUiThread { consent.updatePolicy(refreshedPolicy) }
    }
}
```

If the policy version or property changes while the native consent dialog is open, the manager dismisses that stale dialog. The host can then reopen it using the updated policy and its defaults.

### Optional central decision reporting

Only after the client approves the visitor notice and collection design, the app may explicitly report each submitted choice from the decision listener:

```kotlin
consent.addConsentChangedListener { decision ->
    policyClient.recordDecision("https://cmp.example.ma", decision) { upload ->
        upload.onFailure { error ->
            // Report technical delivery status without logging purpose values.
        }
    }
}
```

The call uses an event-specific random ID so retrying the same local decision is idempotent. It does not attach an account or persistent device ID. The API stores the purpose booleans and server receipt time; it does not verify identity, screen display or app authenticity. These client-reported events do not constitute a legal proof by themselves, and network errors leave the local decision intact.

The `sample` app lets an integrator enter an API URL and property ID, fetch a published Android policy, display the consent dialog, and inspect the analytics decision. It refreshes the policy when the activity returns to the foreground and updates the existing manager so a newly published version invalidates the previous choice. If no valid policy is available, it marks the manager unavailable, clears the saved choice, and tells the integrator to leave optional SDKs stopped. Its analytics action is intentionally a placeholder; it does not include a third-party analytics library.

## Current integration limits

- Source API and UI are an MVP starter, not yet security-reviewed or approved for a bank production app.
- No artifact has been built or published from this checkout; release signing, reproducible builds, SBOM, vulnerability scanning, and compatibility matrix remain to be established.
- Consent decisions persist locally. Optional central reporting is a separate `addConsentChangedListener` app call; effective-state listeners also fire on policy changes but are not decision events. There is no retry queue, cross-device synchronization, public rate limiting or production deployment support.
- Validate Android version, accessibility, network/offline behavior and each third-party SDK's revocation behavior in the target app before a pilot.
