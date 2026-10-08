# Aman Consent — SDK iOS

Le package Swift expose un client de politique, un gestionnaire de choix local et une feuille SwiftUI FR/AR. Il cible iOS 16+ et Swift 5.9+. Il s’agit d’une source de démarrage : aucun binaire signé ou publié n’est fourni.

## Ajouter le package

Dans Xcode, utiliser **File → Add Package Dependencies…** puis indiquer l’URL Git du dépôt privé ALAMANE (l’accès au dépôt est requis), ou ajouter le chemin local du dossier `mobile/ios` après avoir cloné le dépôt. Sélectionner le produit `AmanConsent` dans la cible de l’application. Le manifeste à la racine expose le package iOS pour l’URL distante ; le manifeste `mobile/ios/Package.swift` reste disponible pour une intégration locale. Les deux incluent `PrivacyInfo.xcprivacy` comme ressource du package. L’équipe intégratrice doit examiner les exigences de manifeste Apple pour l’application complète et tous ses SDK. Pour un pilote, épingler une révision examinée ; une release versionnée et signée reste à établir.

## Charger une politique et afficher les choix

Le client récupère la politique publiée de la propriété et conserve la dernière version valide sur l’appareil pour les démarrages hors ligne. Le cache ne sert qu’en cas d’erreur réseau ou de réponse temporaire (`408`, `425`, `429` ou `5xx`). Une réponse non temporaire (dont `404`) ou une politique invalide efface le cache et retourne une erreur ; l’application hôte doit alors arrêter ses SDK optionnels et demander une nouvelle tentative. Sa session réseau par défaut est éphémère, sans cookie ni identifiants de connexion partagés avec l’application hôte, et refuse les redirections pour le chargement comme pour l’envoi. Le gestionnaire conserve le choix dans `UserDefaults`. Il ne l’envoie pas automatiquement à Aman ; le client peut appeler explicitement l’API d’envoi après validation de son modèle de collecte.

Avant de mettre une politique en cache ou de l’appliquer, le client rejette les versions de schéma inconnues, les langues ou finalités non prises en charge, les règles de finalité contradictoires et les durées hors limites du schéma. Si `defaultLanguage` est absent, la première langue déclarée dans la politique est utilisée.

```swift
import AmanConsent
import SwiftUI

@MainActor
struct ConsentSetupView: View {
    @State private var manager: AmanConsentManager?
    @State private var showingPreferences = false
    @State private var errorMessage: String?
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        VStack {
            if let errorMessage {
                Text(errorMessage)
            } else if let manager {
                Button("Gérer mes préférences") {
                    showingPreferences = true
                }
                .sheet(isPresented: $showingPreferences) {
                    AmanConsentSheet(manager: manager)
                }
            } else {
                ProgressView("Chargement des préférences…")
            }
        }
        .task { await loadConsentPolicy() }
        .onChange(of: scenePhase) { phase in
            guard phase == .active else { return }
            Task { await refreshConsentPolicy() }
        }
    }

    private func loadConsentPolicy() async {
        // Démarrer fermé : aucune finalité optionnelle avant une politique valide.
        applyAnalyticsChoice(false)
        do {
            let client = AmanConsentAPIClient()
            let apiBaseURL = URL(string: "https://cmp.example.ma")!
            let policy = try await client.fetchPolicy(
                baseURL: apiBaseURL,
                propertyId: "PROPERTY_ID",
                channel: "ios"
            )
            errorMessage = nil
            let consentManager = AmanConsentManager(policy: policy)
            consentManager.onEffectivePurposeStatesChanged = { states in
                applyAnalyticsChoice(states["analytics"] == true)
                // Ne pas traiter ce callback d’état comme un nouvel événement de décision.
            }
            manager = consentManager
            if consentManager.decision == nil {
                showingPreferences = true
            }
            applyAnalyticsChoice(consentManager.isAllowed("analytics"))
        } catch {
            manager?.markPolicyUnavailable()
            showingPreferences = false
            applyAnalyticsChoice(false)
            errorMessage = "Impossible de charger la politique de préférences."
        }
    }

    private func refreshConsentPolicy() async {
        guard let manager else {
            await loadConsentPolicy()
            return
        }
        do {
            let client = AmanConsentAPIClient()
            let apiBaseURL = URL(string: "https://cmp.example.ma")!
            let policy = try await client.fetchPolicy(
                baseURL: apiBaseURL,
                propertyId: "PROPERTY_ID",
                channel: "ios"
            )
            manager.updatePolicy(policy)
            errorMessage = nil
            applyAnalyticsChoice(manager.isAllowed("analytics"))
        } catch {
            manager.markPolicyUnavailable()
            showingPreferences = false
            applyAnalyticsChoice(false)
            errorMessage = "Aucune politique valide n’est disponible ; les SDK optionnels restent arrêtés."
        }
    }

    private func applyAnalyticsChoice(_ allowed: Bool) {
        if allowed {
            startAnalyticsIfNeeded()
        } else {
            stopAnalyticsIfSupported()
        }
    }

    private func startAnalyticsIfNeeded() { /* Connecter le SDK réel du client ici. */ }
    private func stopAnalyticsIfSupported() { /* Utiliser l’API d’arrêt du fournisseur si disponible. */ }
}
```

Le code d’exemple laisse volontairement l’API du fournisseur en fonctions de remplacement. Le client doit raccorder chaque finalité à son propre SDK et empêcher son initialisation avant le choix applicable. Désactive l’auto-initialisation et l’auto-collecte dans la configuration native du fournisseur : le callback de l’application intervient après le démarrage et un arrêt tardif ne peut pas effacer un envoi déjà effectué. Aman ne peut pas désinitialiser une bibliothèque native déjà lancée.

Sans paramètre `language`, `AmanConsentSheet` reprend `defaultLanguage` de la politique publiée (`fr` ou `ar`). L’application hôte peut fournir explicitement une langue pour adapter l’écran à sa propre préférence de langue.

Les champs de notice traduits se trouvent dans `noticeTranslations.fr` et `noticeTranslations.ar`. La feuille choisit le bloc correspondant à la langue affichée ; elle accepte aussi l’ancien champ `notice` comme solution de repli. Le client doit fournir et faire relire les contenus pour chaque langue proposée.

`onEffectivePurposeStatesChanged` signale l’état effectif après un choix enregistré et après `updatePolicy(_:)`. Quand une nouvelle politique invalide un ancien choix, le callback transmet les valeurs de départ de la nouvelle version afin que l’application puisse arrêter ou démarrer ses SDK en conséquence. Il ne représente pas un nouveau choix du visiteur et ne doit pas être envoyé comme événement de consentement. L’application doit aussi appliquer une première fois `isAllowed(_:)` après avoir créé le gestionnaire.

Si `fetchPolicy` échoue, aucune politique exploitable n’est disponible : appeler `markPolicyUnavailable()` sur le gestionnaire existant et désactiver les finalités optionnelles. Cette méthode efface le choix enregistré et fait renvoyer `false` par `isAllowed(_:)` pour les finalités optionnelles, jusqu’à ce que `updatePolicy(_:)` reçoive une politique valide. `AmanConsentSheet` affiche alors un message et désactive ses contrôles. Les pannes réseau et réponses temporaires avec un cache valide sont déjà retournées comme une politique valide par le client.

### Remontée facultative des décisions

Après validation de l’information visiteur et du traitement par le client, l’application peut transmettre chaque décision explicite depuis `onConsentChanged`. L’API réutilise l’identifiant d’événement aléatoire stocké avec la décision afin de rendre les répétitions idempotentes. Le gestionnaire reste local-first ; une erreur réseau ne modifie pas le choix local.

```swift
consentManager.onConsentChanged = { decision in
    applyAnalyticsChoice(decision.purposes["analytics"] == true)
    Task {
        do {
            try await client.recordDecision(decision, baseURL: apiBaseURL)
        } catch {
            // Journaliser un statut technique sans consigner le détail des choix.
        }
    }
}
```

Ne branche pas cet appel avant d’avoir approuvé la collecte et ajouté l’information correspondante dans la notice du client. L’API stocke les booléens par finalité et l’heure de réception ; elle ne vérifie ni identité, ni affichage de l’écran, ni authenticité du binaire. Les événements ne forment donc pas seuls une preuve juridique.

Le manifeste fourni déclare cette capacité conditionnelle comme interaction produit non liée à une identité et utilisée pour des agrégats analytiques, conformément aux catégories techniques Apple. La déclaration de l’application doit refléter son intégration réelle : le client doit confirmer cette classification, notamment si son serveur peut rapprocher l’événement d’un compte ou d’une autre donnée.

## Choix et cycle de vie

- `AmanConsentManager.isAllowed(_:)` respecte le choix enregistré, sinon applique `initiallyEnabled` explicitement configuré par finalité. Une finalité nécessaire reste active. `consentRequired` indique qu’un choix positif doit précéder l’activation ; les deux réglages ne sont pas déduits l’un de l’autre. Les politiques historiques sans `initiallyEnabled` sont traitées comme désactivées avant un choix. Le responsable et son équipe juridique / DPO doivent valider le classement et l’état initial avant publication ; ce mécanisme ne constitue pas une qualification juridique par Aman.
- `acceptAll()`, `rejectOptional()` et `saveChoices(_:)` enregistrent localement une décision typée et appellent `onConsentChanged` ainsi que `onEffectivePurposeStatesChanged`. L’envoi central requiert un appel séparé à `AmanConsentAPIClient.recordDecision`.
- `updatePolicy(_:)` applique la nouvelle politique et notifie `onEffectivePurposeStatesChanged` ; une nouvelle version invalide le choix précédent de cette propriété et l’application doit synchroniser ses SDK tiers avec les nouveaux états. Les choix restent isolés par `propertyId`.
- Si une politique ou sa propriété change pendant que `AmanConsentSheet` est visible, le formulaire recharge les états effectifs de la politique reçue afin de ne pas conserver des cases de l’ancienne version.
- Le gestionnaire programme une notification d’état quand un choix expire pendant que le processus est actif. L’application hôte doit aussi appeler `refreshExpiredDecision()` au retour au premier plan, puis relier `onEffectivePurposeStatesChanged` à l’arrêt / redémarrage effectif des SDK tiers. L’expiration efface le choix local et n’appelle pas `onConsentChanged` : elle ne doit pas être transmise comme un nouveau choix visiteur.
- Après avoir récupéré une nouvelle version, appeler explicitement `updatePolicy(_:)` sur le gestionnaire existant pour appliquer cette synchronisation :

  ```swift
  let refreshedPolicy = try await client.fetchPolicy(
      baseURL: apiBaseURL,
      propertyId: propertyId,
      channel: "ios"
  )
  consentManager.updatePolicy(refreshedPolicy)
  ```

- `AmanConsentSheet` affiche les finalités de canal `ios`, les informations disponibles dans l’avis et les actions accepter, refuser ou personnaliser. Son contenu défile pour garder les actions accessibles lorsque la politique comporte de nombreuses finalités ou une notice détaillée.
- Si la politique ne peut pas être chargée et qu’aucune version en cache n’est disponible, l’application doit garder les SDK optionnels arrêtés et prévoir un parcours de reprise adapté.

## Points à valider dans l’application hôte

- Les URL de service distantes doivent utiliser HTTPS. HTTP est accepté seulement pour les hôtes loopback de développement.
- Raccorder le choix de retrait à la capacité d’arrêt de chaque fournisseur ; un SDK tiers peut ne pas offrir de désinitialisation.
- L’interface intégrée ici ne remplace pas une demande système Apple. Évaluer séparément les règles App Tracking Transparency selon les usages de l’application.
- Vérifier les textes FR/AR avec des traducteurs et utilisateurs, le RTL, VoiceOver, Dynamic Type, le mode hors ligne et les versions iOS prises en charge.
- Examiner le Privacy Manifest de la bibliothèque avec celui de l’app, ses autres SDK, les exigences de déclaration Apple, le modèle de données et la politique de confidentialité du client.
- Ne pas activer une intégration de production avant revue sécurité et juridique, accord d’hébergement/transfert, contrat et publication signée du package.

## État de distribution

Ce dépôt ne produit pas encore de release distribuable. Il reste à compiler dans Xcode, intégrer à une application d’exemple, faire les revues de code et sécurité, établir la signature et la provenance des builds, publier dans le dépôt d’artefacts choisi par le client et maintenir une matrice de compatibilité. La remontée centralisée est une option appelée par l’application et reste soumise au cadrage du client.
