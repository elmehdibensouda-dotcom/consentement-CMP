package ma.aman.consent

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.DialogInterface
import android.os.Handler
import android.os.Looper
import android.view.View
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executor
import java.util.concurrent.Executors
import java.util.concurrent.CopyOnWriteArrayList
import java.lang.ref.WeakReference

data class AmanLocalizedText(val fr: String, val ar: String) {
    fun value(language: String): String = if (language.lowercase().startsWith("ar")) ar else fr
}

data class AmanPurpose(
    val id: String,
    val label: AmanLocalizedText,
    val description: AmanLocalizedText,
    val required: Boolean,
    val consentRequired: Boolean,
    val channels: List<String>,
    val vendors: List<String> = emptyList()
)

data class AmanPrivacyNotice(
    val controllerName: String,
    val contact: String,
    val processingReference: String,
    val dataCategories: List<String>,
    val recipients: List<String>,
    val transfers: List<String>
) {
    fun summary(isArabic: Boolean): String = buildString {
        append(if (isArabic) "معلومات حول المعالجة" else "Informations sur le traitement")
        append("\n\n")
        append(if (isArabic) "المسؤول" else "Responsable").append(": ").append(controllerName)
        append("\n").append(if (isArabic) "جهة الاتصال" else "Contact").append(": ").append(contact)
        append("\n").append(if (isArabic) "مرجع اللجنة الوطنية" else "Référence CNDP").append(": ").append(processingReference)
        append("\n").append(if (isArabic) "فئات البيانات" else "Données concernées").append(": ").append(dataCategories.joinToString(", "))
        append("\n").append(if (isArabic) "المستلمون" else "Destinataires").append(": ").append(recipients.joinToString(", "))
        append("\n").append(if (isArabic) "التحويلات" else "Transferts").append(": ").append(transfers.joinToString(", "))
    }
}

private fun JSONObject.toPrivacyNotice() = AmanPrivacyNotice(
    controllerName = getString("controllerName"),
    contact = getString("contact"),
    processingReference = getString("processingReference"),
    dataCategories = getJSONArray("dataCategories").strings(),
    recipients = getJSONArray("recipients").strings(),
    transfers = getJSONArray("transfers").strings()
)

data class AmanConsentPolicy(
    val propertyId: String,
    val policyVersion: String,
    val purposes: List<AmanPurpose>,
    val retentionDays: Int,
    val notice: AmanPrivacyNotice? = null,
    val status: String = "published",
    val defaultLanguage: String = "fr",
    val noticeTranslations: Map<String, AmanPrivacyNotice> = emptyMap(),
    val schemaVersion: Int = 1,
    val languages: List<String> = listOf("fr", "ar")
) {
    fun noticeForLanguage(language: String): AmanPrivacyNotice? {
        val key = if (language.lowercase().startsWith("ar")) "ar" else "fr"
        return noticeTranslations[key] ?: notice
    }

    companion object {
        fun fromJson(json: String): AmanConsentPolicy {
            val root = JSONObject(json)
            val purposesJson = root.getJSONArray("purposes")
            val purposes = (0 until purposesJson.length()).map { index ->
                val item = purposesJson.getJSONObject(index)
                val vendors = item.optJSONArray("vendors")?.strings().orEmpty()
                AmanPurpose(
                    id = item.getString("id"),
                    label = item.getJSONObject("label").toLocalizedText(),
                    description = item.getJSONObject("description").toLocalizedText(),
                    required = item.getBoolean("required"),
                    consentRequired = item.getBoolean("consentRequired"),
                    channels = item.getJSONArray("channels").strings(),
                    vendors = vendors
                )
            }
            val notice = root.optJSONObject("notice")?.toPrivacyNotice()
            val translations = root.optJSONObject("noticeTranslations")?.let { objectValue ->
                listOf("fr", "ar").mapNotNull { language ->
                    objectValue.optJSONObject(language)?.let { language to it.toPrivacyNotice() }
                }.toMap()
            }.orEmpty()
            val languages = root.getJSONArray("languages").strings()
            return AmanConsentPolicy(
                propertyId = root.getString("propertyId"),
                policyVersion = root.getString("policyVersion"),
                purposes = purposes,
                retentionDays = root.getInt("retentionDays"),
                notice = notice,
                noticeTranslations = translations,
                status = root.getString("status"),
                defaultLanguage = root.optString("defaultLanguage", languages.firstOrNull() ?: "fr"),
                schemaVersion = root.getInt("schemaVersion"),
                languages = languages
            )
        }
    }
}

data class AmanConsentDecision(
    val propertyId: String,
    val policyVersion: String,
    val capturedAtMillis: Long,
    val expiresAtMillis: Long,
    val channel: String,
    val purposes: Map<String, Boolean>,
    val eventId: String? = null,
    val action: String? = null
)

enum class AmanConsentAction(val wireValue: String) {
    ACCEPT_ALL("accept_all"),
    REJECT_ALL("reject_all"),
    CUSTOM("custom")
}

private fun JSONObject.toLocalizedText() = AmanLocalizedText(getString("fr"), getString("ar"))
private fun JSONArray.strings(): List<String> = (0 until length()).map { getString(it) }

class AmanConsentManager(
    context: Context,
    policy: AmanConsentPolicy,
    private val clockMillis: () -> Long = System::currentTimeMillis
) {
    private val preferences = context.applicationContext.getSharedPreferences("aman_consent", Context.MODE_PRIVATE)
    private val expiryHandler = Handler(Looper.getMainLooper())
    private var expiryRunnable: Runnable? = null
    @Volatile private var activeConsentDialog: AlertDialog? = null
    private val listeners = CopyOnWriteArrayList<(AmanConsentDecision) -> Unit>()
    private val effectivePurposeListeners = CopyOnWriteArrayList<(Map<String, Boolean>) -> Unit>()
    var policy: AmanConsentPolicy = policy
        private set
    var decision: AmanConsentDecision? = null
        private set
    @Volatile private var policyAvailable = true
    val activePurposes: List<AmanPurpose>
        get() = if (policy.status == "published") policy.purposes.filter { "android" in it.channels } else emptyList()
    val effectivePurposeStates: Map<String, Boolean>
        get() = activePurposes.associate { it.id to isAllowed(it.id) }

    init { restore() }

    private val storageKey: String get() = "property:${policy.propertyId}"

    @Synchronized
    fun updatePolicy(updated: AmanConsentPolicy) {
        val previousPropertyId = policy.propertyId
        val changed = policy.policyVersion != updated.policyVersion
        policy = updated
        policyAvailable = true
        if (previousPropertyId != updated.propertyId) {
            // A manager can be reused for another property, but its saved choice must stay scoped to that property.
            restore()
        } else if (changed) {
            preferences.edit().remove(storageKey).apply()
            decision = null
        } else restore()
        scheduleExpiryRefresh()
        effectivePurposeListeners.forEach { it(effectivePurposeStates) }
    }

    fun isAllowed(purposeId: String): Boolean {
        val purpose = activePurposes.firstOrNull { it.id == purposeId } ?: return false
        if (purpose.required) return true
        if (!policyAvailable) return false
        val current = decision
        if (current == null || current.propertyId != policy.propertyId || current.channel != "android" ||
            current.policyVersion != policy.policyVersion || current.expiresAtMillis <= clockMillis()) {
            return !purpose.consentRequired
        }
        return current.purposes[purposeId] ?: !purpose.consentRequired
    }

    fun acceptAll() = saveChoices(activePurposes.associate { it.id to true }, AmanConsentAction.ACCEPT_ALL)
    fun rejectOptional() = saveChoices(activePurposes.associate { it.id to it.required }, AmanConsentAction.REJECT_ALL)

    @Synchronized
    fun saveChoices(requested: Map<String, Boolean>) = saveChoices(requested, AmanConsentAction.CUSTOM)

    @Synchronized
    fun saveChoices(requested: Map<String, Boolean>, action: AmanConsentAction) {
        if (!policyAvailable) return
        val capturedAt = clockMillis()
        val normalized = activePurposes.associate { purpose ->
            purpose.id to (purpose.required || (requested[purpose.id] ?: !purpose.consentRequired))
        }
        val optionalPurposes = activePurposes.filterNot { it.required }
        val recordedAction = when (action) {
            AmanConsentAction.ACCEPT_ALL -> if (optionalPurposes.all { normalized[it.id] == true }) action else AmanConsentAction.CUSTOM
            AmanConsentAction.REJECT_ALL -> if (optionalPurposes.none { normalized[it.id] == true }) action else AmanConsentAction.CUSTOM
            AmanConsentAction.CUSTOM -> action
        }
        val updated = AmanConsentDecision(
            propertyId = policy.propertyId,
            policyVersion = policy.policyVersion,
            capturedAtMillis = capturedAt,
            expiresAtMillis = capturedAt + policy.retentionDays.coerceAtLeast(1) * 86_400_000L,
            channel = "android",
            purposes = normalized,
            eventId = java.util.UUID.randomUUID().toString(),
            action = recordedAction.wireValue
        )
        decision = updated
        val encoded = JSONObject().apply {
            put("propertyId", updated.propertyId)
            put("policyVersion", updated.policyVersion)
            put("capturedAtMillis", updated.capturedAtMillis)
            put("expiresAtMillis", updated.expiresAtMillis)
            put("channel", updated.channel)
            put("purposes", JSONObject(updated.purposes))
            put("eventId", updated.eventId.orEmpty())
            put("action", updated.action.orEmpty())
        }
        preferences.edit().putString(storageKey, encoded.toString()).apply()
        scheduleExpiryRefresh()
        listeners.forEach { it(updated) }
        effectivePurposeListeners.forEach { it(effectivePurposeStates) }
    }

    /** Reconciles expired local choices with host SDKs. This is a state update, not a new user decision. */
    @Synchronized
    fun refreshExpiredDecision(): Boolean {
        val current = decision ?: return false
        if (current.expiresAtMillis > clockMillis()) {
            scheduleExpiryRefresh()
            return false
        }
        preferences.edit().remove(storageKey).apply()
        decision = null
        scheduleExpiryRefresh()
        effectivePurposeListeners.forEach { it(effectivePurposeStates) }
        return true
    }

    /** Disables optional purposes and clears the saved choice until updatePolicy receives a valid policy. */
    @Synchronized
    fun markPolicyUnavailable() {
        policyAvailable = false
        val dialog = activeConsentDialog
        activeConsentDialog = null
        if (dialog != null) expiryHandler.post { dialog.dismiss() }
        preferences.edit().remove(storageKey).apply()
        decision = null
        scheduleExpiryRefresh()
        effectivePurposeListeners.forEach { it(effectivePurposeStates) }
    }

    fun addConsentChangedListener(listener: (AmanConsentDecision) -> Unit) { listeners.add(listener) }
    fun removeConsentChangedListener(listener: (AmanConsentDecision) -> Unit) { listeners.remove(listener) }
    /** Observes effective purpose states after choices and policy changes; this is not a decision/audit event. */
    fun addEffectivePurposeStatesChangedListener(listener: (Map<String, Boolean>) -> Unit) {
        effectivePurposeListeners.add(listener)
    }
    fun removeEffectivePurposeStatesChangedListener(listener: (Map<String, Boolean>) -> Unit) {
        effectivePurposeListeners.remove(listener)
    }

    fun showConsentDialog(activity: Activity, language: String? = null) {
        if (!policyAvailable || activeConsentDialog?.isShowing == true) return
        val selectedLanguage = language ?: policy.defaultLanguage
        val isArabic = selectedLanguage.lowercase().startsWith("ar")
        val active = activePurposes
        val labels = active.map {
            val vendorText = if (it.vendors.isEmpty()) "" else if (isArabic) {
                " — الموردون المرتبطون (للاسترشاد): ${it.vendors.joinToString(", ")}"
            } else {
                " — Fournisseurs associés (indicatif) : ${it.vendors.joinToString(", ")}"
            }
            "${it.label.value(selectedLanguage)} — ${it.description.value(selectedLanguage)}$vendorText"
        }.toTypedArray()
        val choices = policy.purposes.associate { it.id to isAllowed(it.id) }.toMutableMap()
        val checked = active.map { isAllowed(it.id) }.toBooleanArray()
        val builder = AlertDialog.Builder(activity)
            .setTitle(if (isArabic) "تفضيلاتك" else "Vos préférences")
            .setMessage(buildString {
                append(if (isArabic) "اختر الفئات التي تسمح بها." else "Choisissez les catégories que vous autorisez.")
                policy.noticeForLanguage(selectedLanguage)?.let { append("\n\n").append(it.summary(isArabic)) }
            })
            .setMultiChoiceItems(labels, checked) { dialogInterface: DialogInterface, which: Int, selected: Boolean ->
                val purpose = active[which]
                if (!purpose.required) choices[purpose.id] = selected
                else (dialogInterface as? AlertDialog)?.listView?.setItemChecked(which, true)
            }
            .setPositiveButton(if (isArabic) "قبول الكل" else "Tout accepter") { _, _ -> acceptAll() }
            .setNegativeButton(if (isArabic) "رفض الكل" else "Tout refuser") { _, _ -> rejectOptional() }
            .setNeutralButton(if (isArabic) "حفظ اختياراتي" else "Enregistrer mes choix") { _, _ -> saveChoices(choices) }
        val dialog = builder.create()
        activeConsentDialog = dialog
        dialog.setOnDismissListener {
            if (activeConsentDialog === dialog) activeConsentDialog = null
        }
        dialog.setOnShowListener {
            dialog.window?.decorView?.layoutDirection = if (isArabic) View.LAYOUT_DIRECTION_RTL else View.LAYOUT_DIRECTION_LTR
        }
        dialog.show()
    }

    @Synchronized
    private fun restore() {
        val raw = preferences.getString(storageKey, null)
        if (raw == null) {
            decision = null
            scheduleExpiryRefresh()
            return
        }
        try {
            val json = JSONObject(raw)
            val purposesJson = json.getJSONObject("purposes")
            val purposes = policy.purposes.associate { purpose ->
                purpose.id to purposesJson.optBoolean(purpose.id, !purpose.consentRequired)
            }
            val stored = AmanConsentDecision(
                propertyId = json.getString("propertyId"),
                policyVersion = json.getString("policyVersion"),
                capturedAtMillis = json.getLong("capturedAtMillis"),
                expiresAtMillis = json.getLong("expiresAtMillis"),
                channel = json.getString("channel"),
                purposes = purposes,
                eventId = json.optString("eventId").takeIf { it.isNotBlank() && it != "null" },
                action = json.optString("action").takeIf { it.isNotBlank() && it != "null" }
            )
            if (stored.propertyId != policy.propertyId || stored.channel != "android" ||
                stored.policyVersion != policy.policyVersion || !isValidStoredDecision(stored)) {
                preferences.edit().remove(storageKey).apply()
                decision = null
            } else decision = stored
        } catch (_: Exception) {
            preferences.edit().remove(storageKey).apply()
            decision = null
        }
        scheduleExpiryRefresh()
    }

    private fun isValidStoredDecision(stored: AmanConsentDecision): Boolean {
        val currentTime = clockMillis()
        val active = activePurposes
        val optional = active.filterNot { it.required }
        val expectedPurposeIds = active.map { it.id }.toSet()
        val duration = stored.expiresAtMillis - stored.capturedAtMillis
        if (stored.capturedAtMillis < 0 || stored.capturedAtMillis > currentTime + 60_000L ||
            stored.expiresAtMillis <= currentTime || duration <= 0 ||
            duration > policy.retentionDays.toLong() * 86_400_000L ||
            stored.purposes.keys != expectedPurposeIds ||
            active.any { it.required && stored.purposes[it.id] != true } ||
            (stored.eventId != null && runCatching { java.util.UUID.fromString(stored.eventId) }.isFailure)) {
            return false
        }
        return when (stored.action) {
            "accept_all" -> optional.all { stored.purposes[it.id] == true }
            "reject_all" -> optional.all { stored.purposes[it.id] == false }
            null, "custom" -> true
            else -> false
        }
    }

    private fun scheduleExpiryRefresh() {
        expiryRunnable?.let(expiryHandler::removeCallbacks)
        expiryRunnable = null
        val current = decision ?: return
        val delay = current.expiresAtMillis - clockMillis()
        if (delay <= 0) {
            refreshExpiredDecision()
            return
        }
        val manager = WeakReference(this)
        val task = Runnable { manager.get()?.refreshExpiredDecision() }
        expiryRunnable = task
        expiryHandler.postDelayed(task, delay)
    }
}

/** Fetches policies off the UI thread and delivers results on the main thread by default. */
class AmanConsentAPIClient(
    context: Context,
    private val executor: Executor = Executors.newSingleThreadExecutor(),
    private val callbackExecutor: Executor = Executor { command ->
        Handler(Looper.getMainLooper()).post(command)
        Unit
    }
) {
    private val preferences = context.applicationContext.getSharedPreferences("aman_consent", Context.MODE_PRIVATE)

    fun fetchPublishedPolicy(
        baseUrl: String,
        propertyId: String,
        channel: String = "android",
        callback: (Result<AmanConsentPolicy>) -> Unit
    ) {
        executor.execute {
            val cacheKey = "policy:$propertyId:$channel"
            val cachedJson = preferences.getString(cacheKey, null)
            val cachedEtag = preferences.getString("$cacheKey:etag", null)
            var connection: HttpURLConnection? = null
            try {
                require(channel in setOf("android", "ios", "web")) { "Unsupported Aman channel" }
                require(propertyId.matches(Regex("[A-Za-z0-9_-]{1,128}"))) { "Invalid Aman property ID" }
                val base = URL(baseUrl)
                val host = base.host.lowercase().removePrefix("[").removeSuffix("]")
                val loopback = host in setOf("localhost", "127.0.0.1", "::1")
                require(host.isNotBlank() && base.userInfo.isNullOrEmpty() && base.query == null && base.ref == null &&
                    (base.protocol.equals("https", ignoreCase = true) ||
                        (base.protocol.equals("http", ignoreCase = true) && loopback))) {
                    "Aman policy requests require HTTPS except for loopback development hosts"
                }
                val endpoint = "${baseUrl.trimEnd('/')}/v1/public/properties/$propertyId/policy"
                connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 5_000
                    readTimeout = 5_000
                    useCaches = false
                    instanceFollowRedirects = false
                    if (!cachedEtag.isNullOrBlank()) setRequestProperty("If-None-Match", cachedEtag)
                }
                val code = connection.responseCode
                if (code == HttpURLConnection.HTTP_NOT_MODIFIED && !cachedJson.isNullOrBlank()) {
                    try {
                        val cachedPolicy = AmanConsentPolicy.fromJson(cachedJson)
                        validateFetchedPolicy(cachedPolicy, propertyId, channel)
                        callbackExecutor.execute { callback(Result.success(cachedPolicy)) }
                    } catch (error: Exception) {
                        preferences.edit().remove(cacheKey).remove("$cacheKey:etag").apply()
                        callbackExecutor.execute { callback(Result.failure(error)) }
                    }
                    return@execute
                }
                if (code != HttpURLConnection.HTTP_OK) {
                    val temporaryFailure = code == 408 || code == 425 || code == 429 || code in 500..599
                    if (temporaryFailure && !cachedJson.isNullOrBlank()) {
                        try {
                            val cachedPolicy = AmanConsentPolicy.fromJson(cachedJson)
                            validateFetchedPolicy(cachedPolicy, propertyId, channel)
                            callbackExecutor.execute { callback(Result.success(cachedPolicy)) }
                        } catch (error: Exception) {
                            preferences.edit().remove(cacheKey).remove("$cacheKey:etag").apply()
                            callbackExecutor.execute { callback(Result.failure(error)) }
                        }
                    } else {
                        if (!temporaryFailure) {
                            preferences.edit().remove(cacheKey).remove("$cacheKey:etag").apply()
                        }
                        callbackExecutor.execute {
                            callback(Result.failure(IllegalStateException("Aman policy endpoint returned HTTP $code")))
                        }
                    }
                    return@execute
                }
                val raw = connection.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
                val policy = try {
                    AmanConsentPolicy.fromJson(raw).also { validateFetchedPolicy(it, propertyId, channel) }
                } catch (error: Exception) {
                    preferences.edit().remove(cacheKey).remove("$cacheKey:etag").apply()
                    callbackExecutor.execute { callback(Result.failure(error)) }
                    return@execute
                }
                preferences.edit()
                    .putString(cacheKey, raw)
                    .putString("$cacheKey:etag", connection.getHeaderField("ETag"))
                    .apply()
                callbackExecutor.execute { callback(Result.success(policy)) }
            } catch (error: IOException) {
                if (!cachedJson.isNullOrBlank()) {
                    try {
                        val cachedPolicy = AmanConsentPolicy.fromJson(cachedJson)
                        validateFetchedPolicy(cachedPolicy, propertyId, channel)
                        callbackExecutor.execute { callback(Result.success(cachedPolicy)) }
                    } catch (cacheError: Exception) {
                        preferences.edit().remove(cacheKey).remove("$cacheKey:etag").apply()
                        callbackExecutor.execute { callback(Result.failure(cacheError)) }
                    }
                } else callbackExecutor.execute { callback(Result.failure(error)) }
            } catch (error: Exception) {
                callbackExecutor.execute { callback(Result.failure(error)) }
            } finally {
                connection?.disconnect()
            }
        }
    }

    /** Upload an explicit choice without account or device identifiers. Call only after client review. */
    fun recordDecision(
        baseUrl: String,
        decision: AmanConsentDecision,
        callback: (Result<Unit>) -> Unit
    ) {
        executor.execute {
            var connection: HttpURLConnection? = null
            var failure: Throwable? = null
            try {
                require(decision.propertyId.matches(Regex("[A-Za-z0-9_-]{1,128}"))) { "Invalid Aman property ID" }
                require(decision.channel in setOf("android", "ios", "web")) { "Unsupported Aman channel" }
                val base = URL(baseUrl)
                val host = base.host.lowercase().removePrefix("[").removeSuffix("]")
                val loopback = host in setOf("localhost", "127.0.0.1", "::1")
                require(host.isNotBlank() && base.userInfo.isNullOrEmpty() && base.query == null && base.ref == null &&
                    (base.protocol.equals("https", ignoreCase = true) ||
                        (base.protocol.equals("http", ignoreCase = true) && loopback))) {
                    "Aman decision uploads require HTTPS except for loopback development hosts"
                }
                val eventId = decision.eventId ?: java.util.UUID.randomUUID().toString()
                val payload = JSONObject().apply {
                    put("eventId", eventId)
                    put("policyVersion", decision.policyVersion)
                    put("channel", decision.channel)
                    put("action", decision.action ?: "custom")
                    put("purposes", JSONObject(decision.purposes))
                }.toString().toByteArray(Charsets.UTF_8)
                val endpoint = "${baseUrl.trimEnd('/')}/v1/public/properties/${decision.propertyId}/consent-events"
                connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                    requestMethod = "POST"
                    connectTimeout = 5_000
                    readTimeout = 5_000
                    useCaches = false
                    instanceFollowRedirects = false
                    doOutput = true
                    setRequestProperty("Content-Type", "application/json")
                    setRequestProperty("Cookie", "")
                    setFixedLengthStreamingMode(payload.size)
                }
                connection.outputStream.use { it.write(payload) }
                val code = connection.responseCode
                if (code !in 200..299) throw IOException("Aman consent event endpoint returned HTTP $code")
            } catch (error: Exception) {
                failure = error
            } finally {
                connection?.disconnect()
            }
            val error = failure
            if (error == null) callbackExecutor.execute { callback(Result.success(Unit)) }
            else callbackExecutor.execute { callback(Result.failure(error)) }
        }
    }

    private fun validateFetchedPolicy(policy: AmanConsentPolicy, propertyId: String, channel: String) {
        require(policy.schemaVersion == 1) { "Unsupported Aman policy schema version" }
        require(policy.status == "published") { "Aman policy is not published" }
        require(policy.propertyId == propertyId) { "Aman policy belongs to another property" }
        require(policy.purposes.map { it.id }.distinct().size == policy.purposes.size) {
            "Aman policy contains duplicate purpose IDs"
        }
        require(policy.languages.isNotEmpty() && policy.languages.distinct().size == policy.languages.size &&
            policy.languages.all { it in setOf("fr", "ar") } && policy.defaultLanguage in policy.languages &&
            (policy.notice != null || policy.noticeTranslations.isNotEmpty()) &&
            policy.noticeTranslations.keys.all { it in policy.languages }) {
            "Aman policy has unsupported or incomplete language configuration"
        }
        require(policy.retentionDays in 1..3650 && policy.purposes.all { purpose ->
            purpose.id.matches(Regex("[a-z][a-z0-9_-]{1,63}")) && purpose.channels.isNotEmpty() &&
                purpose.channels.all { it in setOf("web", "ios", "android") } &&
                !(purpose.required && purpose.consentRequired)
        }) { "Aman policy does not match the supported policy schema" }
        require(policy.purposes.any { channel in it.channels }) { "Aman policy has no purpose for $channel" }
    }
}
