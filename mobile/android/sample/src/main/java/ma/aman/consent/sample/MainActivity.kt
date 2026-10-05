package ma.aman.consent.sample

import android.app.Activity
import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import ma.aman.consent.AmanConsentAPIClient
import ma.aman.consent.AmanConsentManager

class MainActivity : Activity() {
    private lateinit var apiBaseUrl: EditText
    private lateinit var propertyId: EditText
    private lateinit var status: TextView
    private lateinit var apiClient: AmanConsentAPIClient
    private var manager: AmanConsentManager? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        apiClient = AmanConsentAPIClient(applicationContext)

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 32, 24, 24)
            layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
        }
        content.addView(TextView(this).apply {
            text = "Aman · exemple d’intégration Android"
            textSize = 21f
        })
        content.addView(TextView(this).apply {
            text = "Saisis l’URL de l’API et l’identifiant d’une propriété Android publiée. Le SDK charge la politique et conserve les choix sur l’appareil."
            setPadding(0, 12, 0, 16)
        })
        apiBaseUrl = EditText(this).apply {
            hint = "https://cmp.example.ma"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI
            setSingleLine(true)
        }
        propertyId = EditText(this).apply {
            hint = "Identifiant de propriété"
            setSingleLine(true)
        }
        status = TextView(this).apply {
            text = "Politique non chargée."
            setPadding(0, 16, 0, 16)
        }
        content.addView(apiBaseUrl)
        content.addView(propertyId)
        content.addView(Button(this).apply {
            text = "Charger la politique publiée"
            setOnClickListener { loadPolicy() }
        })
        content.addView(Button(this).apply {
            text = "Gérer mes préférences"
            setOnClickListener {
                val current = manager
                if (current == null) status.text = "Charge d’abord une politique publiée."
                else current.showConsentDialog(this@MainActivity)
            }
        })
        content.addView(status)
        setContentView(content)
    }

    override fun onResume() {
        super.onResume()
        manager?.refreshExpiredDecision()
    }

    private fun loadPolicy() {
        val base = apiBaseUrl.text.toString().trim()
        val id = propertyId.text.toString().trim()
        if (base.isEmpty() || id.isEmpty()) {
            status.text = "Renseigne l’URL de l’API et l’identifiant de propriété."
            return
        }
        status.text = "Chargement…"
        apiClient.fetchPublishedPolicy(base, id) { result ->
            runOnUiThread {
                result.onSuccess { policy ->
                    val current = AmanConsentManager(applicationContext, policy)
                    manager = current
                    current.addConsentChangedListener { decision ->
                        runOnUiThread { renderIntegrationState(current, decision.policyVersion) }
                    }
                    current.addEffectivePurposeStatesChangedListener {
                        runOnUiThread { renderIntegrationState(current, current.policy.policyVersion) }
                    }
                    renderIntegrationState(current, policy.policyVersion)
                    if (current.decision == null) current.showConsentDialog(this)
                }.onFailure { error ->
                    manager = null
                    status.text = "Impossible de charger la politique : ${error.message ?: "erreur inconnue"}"
                }
            }
        }
    }

    private fun renderIntegrationState(current: AmanConsentManager, version: String) {
        val allowed = current.isAllowed("analytics")
        val action = if (allowed) "Le point d’intégration analytics est autorisé." else "Le point d’intégration analytics reste désactivé."
        status.text = "Politique $version · $action\nRelie cette décision à l’initialisation et à l’arrêt effectifs de tes SDK."
    }
}
