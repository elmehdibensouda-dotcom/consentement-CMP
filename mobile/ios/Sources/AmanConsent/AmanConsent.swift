import Foundation
import SwiftUI

private final class AmanRedirectBlocker: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

public struct AmanLocalizedText: Codable, Equatable {
    public let fr: String
    public let ar: String

    public init(fr: String, ar: String) {
        self.fr = fr
        self.ar = ar
    }

    public func value(for language: String) -> String {
        language.lowercased().hasPrefix("ar") ? ar : fr
    }
}

public struct AmanPurpose: Codable, Equatable, Identifiable {
    public let id: String
    public let label: AmanLocalizedText
    public let description: AmanLocalizedText
    public let required: Bool
    public let consentRequired: Bool
    public let channels: [String]
    public let vendors: [String]?

    public init(id: String, label: AmanLocalizedText, description: AmanLocalizedText,
                required: Bool, consentRequired: Bool, channels: [String], vendors: [String]? = nil) {
        self.id = id
        self.label = label
        self.description = description
        self.required = required
        self.consentRequired = consentRequired
        self.channels = channels
        self.vendors = vendors
    }
}

public struct AmanPrivacyNotice: Codable, Equatable {
    public let controllerName: String
    public let contact: String
    public let processingReference: String
    public let dataCategories: [String]
    public let recipients: [String]
    public let transfers: [String]
}

public struct AmanConsentPolicy: Codable, Equatable {
    public let schemaVersion: Int
    public let propertyId: String
    public let policyVersion: String
    public let status: String
    public let purposes: [AmanPurpose]
    public let languages: [String]
    public let defaultLanguage: String?
    public let retentionDays: Int
    public let notice: AmanPrivacyNotice?
    public let noticeTranslations: [String: AmanPrivacyNotice]?

    public init(schemaVersion: Int = 1, propertyId: String, policyVersion: String, status: String = "published",
                purposes: [AmanPurpose], languages: [String] = ["fr", "ar"], defaultLanguage: String? = "fr",
                retentionDays: Int, notice: AmanPrivacyNotice? = nil,
                noticeTranslations: [String: AmanPrivacyNotice]? = nil) {
        self.schemaVersion = schemaVersion
        self.propertyId = propertyId
        self.policyVersion = policyVersion
        self.status = status
        self.purposes = purposes
        self.languages = languages
        self.defaultLanguage = defaultLanguage
        self.retentionDays = retentionDays
        self.notice = notice
        self.noticeTranslations = noticeTranslations
    }

    public func localizedNotice(for language: String) -> AmanPrivacyNotice? {
        let key = language.lowercased().hasPrefix("ar") ? "ar" : "fr"
        return noticeTranslations?[key] ?? notice
    }
}

public struct AmanConsentDecision: Codable, Equatable {
    public let eventId: String?
    public let action: AmanConsentAction?
    public let propertyId: String
    public let policyVersion: String
    public let capturedAt: Date
    public let expiresAt: Date
    public let channel: String
    public let purposes: [String: Bool]
}

public enum AmanConsentAction: String, Codable, Equatable {
    case acceptAll = "accept_all"
    case rejectAll = "reject_all"
    case custom
}

public enum AmanConsentAPIError: Error {
    case invalidURL
    case insecureTransport
    case invalidResponse
    case policyUnavailable(Int)
    case unsupportedSchemaVersion
    case unpublishedPolicy
    case wrongProperty
    case unsupportedChannel
    case unsupportedLanguage
    case duplicatePurposeId
    case decisionUploadRejected(Int)
}

/// Fetches the public, published policy for one app property and keeps the last
/// valid response on-device for offline startup. Decision uploads require an
/// explicit call to `recordDecision` by the integrating application.
public final class AmanConsentAPIClient {
    private let defaults: UserDefaults
    private let session: URLSession
    private let redirectBlocker = AmanRedirectBlocker()

    public init(defaults: UserDefaults = .standard, session: URLSession? = nil) {
        self.defaults = defaults
        if let session {
            self.session = session
        } else {
            let configuration = URLSessionConfiguration.ephemeral
            configuration.httpCookieStorage = nil
            configuration.httpShouldSetCookies = false
            configuration.urlCredentialStorage = nil
            self.session = URLSession(configuration: configuration)
        }
    }

    public func fetchPolicy(baseURL: URL, propertyId: String, channel: String = "ios") async throws -> AmanConsentPolicy {
        guard isSecureBaseURL(baseURL) else { throw AmanConsentAPIError.insecureTransport }
        guard (1...128).contains(propertyId.count),
              propertyId.range(of: "^[A-Za-z0-9_-]+$", options: .regularExpression) != nil,
              ["ios", "android", "web"].contains(channel),
              let url = URL(string: "/v1/public/properties/\(propertyId)/policy", relativeTo: baseURL) else {
            throw AmanConsentAPIError.invalidURL
        }
        let cacheKey = "aman.policy.\(propertyId).\(channel)"
        let cached: CachedPolicy? = defaults.data(forKey: cacheKey).flatMap { try? JSONDecoder().decode(CachedPolicy.self, from: $0) }
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.httpShouldHandleCookies = false
        if let etag = cached?.etag { request.setValue(etag, forHTTPHeaderField: "If-None-Match") }

        do {
            let (data, response) = try await session.data(for: request, delegate: redirectBlocker)
            guard let http = response as? HTTPURLResponse else { throw AmanConsentAPIError.invalidResponse }
            guard let responseURL = http.url, isSecureBaseURL(responseURL) else {
                defaults.removeObject(forKey: cacheKey)
                throw AmanConsentAPIError.insecureTransport
            }
            if http.statusCode == 304, let cached {
                do {
                    try validate(cached.policy, propertyId: propertyId, channel: channel)
                    return cached.policy
                } catch {
                    defaults.removeObject(forKey: cacheKey)
                    throw error
                }
            }
            guard http.statusCode == 200 else {
                let temporaryFailure = http.statusCode == 408 || http.statusCode == 425 ||
                    http.statusCode == 429 || (500...599).contains(http.statusCode)
                if temporaryFailure, let cached {
                    do {
                        try validate(cached.policy, propertyId: propertyId, channel: channel)
                        return cached.policy
                    } catch {
                        defaults.removeObject(forKey: cacheKey)
                        throw error
                    }
                }
                if !temporaryFailure { defaults.removeObject(forKey: cacheKey) }
                throw AmanConsentAPIError.policyUnavailable(http.statusCode)
            }
            let policy: AmanConsentPolicy
            do {
                policy = try JSONDecoder().decode(AmanConsentPolicy.self, from: data)
                try validate(policy, propertyId: propertyId, channel: channel)
            } catch {
                defaults.removeObject(forKey: cacheKey)
                throw AmanConsentAPIError.invalidResponse
            }
            let value = CachedPolicy(etag: http.value(forHTTPHeaderField: "ETag"), policy: policy)
            if let saved = try? JSONEncoder().encode(value) { defaults.set(saved, forKey: cacheKey) }
            return policy
        } catch let error as URLError {
            if let cached {
                do {
                    try validate(cached.policy, propertyId: propertyId, channel: channel)
                    return cached.policy
                } catch {
                    defaults.removeObject(forKey: cacheKey)
                    throw error
                }
            }
            throw error
        }
    }

    /// Sends one user-submitted decision without account or device identifiers.
    /// The client application must enable this only after reviewing its notice and data-processing design.
    public func recordDecision(_ decision: AmanConsentDecision, baseURL: URL) async throws {
        guard isSecureBaseURL(baseURL) else { throw AmanConsentAPIError.insecureTransport }
        guard (1...128).contains(decision.propertyId.count),
              decision.propertyId.range(of: "^[A-Za-z0-9_-]+$", options: .regularExpression) != nil,
              ["ios", "android", "web"].contains(decision.channel),
              let url = URL(string: "/v1/public/properties/\(decision.propertyId)/consent-events", relativeTo: baseURL)?.absoluteURL else {
            throw AmanConsentAPIError.invalidURL
        }
        let payload = DecisionEventBody(
            eventId: decision.eventId ?? UUID().uuidString.lowercased(),
            policyVersion: decision.policyVersion,
            channel: decision.channel,
            action: decision.action?.rawValue ?? AmanConsentAction.custom.rawValue,
            purposes: decision.purposes
        )
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 10
        request.httpShouldHandleCookies = false
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder().encode(payload)
        let (_, response) = try await session.data(for: request, delegate: redirectBlocker)
        guard let http = response as? HTTPURLResponse else { throw AmanConsentAPIError.invalidResponse }
        guard let responseURL = http.url, isSecureBaseURL(responseURL), responseURL.host == url.host,
              responseURL.port == url.port,
              (200..<300).contains(http.statusCode) else {
            throw AmanConsentAPIError.decisionUploadRejected(http.statusCode)
        }
    }

    private func validate(_ policy: AmanConsentPolicy, propertyId: String, channel: String) throws {
        guard policy.schemaVersion == 1 else { throw AmanConsentAPIError.unsupportedSchemaVersion }
        guard policy.status == "published" else { throw AmanConsentAPIError.unpublishedPolicy }
        guard policy.propertyId == propertyId else { throw AmanConsentAPIError.wrongProperty }
        let purposeIds = policy.purposes.map(\.id)
        guard Set(purposeIds).count == purposeIds.count else { throw AmanConsentAPIError.duplicatePurposeId }
        guard !policy.languages.isEmpty,
              Set(policy.languages).count == policy.languages.count,
              policy.languages.allSatisfy({ ["fr", "ar"].contains($0) }),
              policy.defaultLanguage.map({ policy.languages.contains($0) }) ?? true,
              (policy.notice != nil || !(policy.noticeTranslations?.isEmpty ?? true)),
              (policy.noticeTranslations?.keys.allSatisfy({ policy.languages.contains($0) }) ?? true) else {
            throw AmanConsentAPIError.unsupportedLanguage
        }
        guard (1...3650).contains(policy.retentionDays),
              policy.purposes.allSatisfy({ purpose in
                  purpose.id.range(of: "^[a-z][a-z0-9_-]{1,63}$", options: .regularExpression) != nil
                      && !purpose.channels.isEmpty
                      && purpose.channels.allSatisfy({ ["web", "ios", "android"].contains($0) })
                      && !(purpose.required && purpose.consentRequired)
              }) else { throw AmanConsentAPIError.invalidResponse }
        guard policy.purposes.contains(where: { $0.channels.contains(channel) }) else {
            throw AmanConsentAPIError.unsupportedChannel
        }
    }

    private func isSecureBaseURL(_ url: URL) -> Bool {
        guard let scheme = url.scheme?.lowercased(),
              let host = url.host?.lowercased(),
              url.user == nil,
              url.password == nil,
              url.query == nil,
              url.fragment == nil else { return false }
        if scheme == "https" { return true }
        let loopback = ["localhost", "127.0.0.1", "::1", "[::1]"].contains(host)
        return scheme == "http" && loopback
    }

    private struct CachedPolicy: Codable {
        let etag: String?
        let policy: AmanConsentPolicy
    }

    private struct DecisionEventBody: Encodable {
        let eventId: String
        let policyVersion: String
        let channel: String
        let action: String
        let purposes: [String: Bool]
    }
}

@MainActor
public final class AmanConsentManager: ObservableObject {
    @Published public private(set) var policy: AmanConsentPolicy
    @Published public private(set) var decision: AmanConsentDecision?
    @Published public private(set) var policyAvailable = true

    private let defaults: UserDefaults
    private let now: () -> Date
    private var expiryTimer: Timer?
    private var storageKey: String { "aman.consent.\(policy.propertyId)" }
    public var activePurposes: [AmanPurpose] {
        guard policy.status == "published" else { return [] }
        return policy.purposes.filter { $0.channels.contains("ios") }
    }
    /// Effective states for the current policy, including configured defaults when no saved choice is valid.
    public var effectivePurposeStates: [String: Bool] {
        Dictionary(uniqueKeysWithValues: activePurposes.map { ($0.id, isAllowed($0.id)) })
    }
    public var onConsentChanged: ((AmanConsentDecision) -> Void)?
    /// Fires when effective states change because of a saved choice or policy update. This is not a consent event.
    public var onEffectivePurposeStatesChanged: (([String: Bool]) -> Void)?

    public init(policy: AmanConsentPolicy, defaults: UserDefaults = .standard, now: @escaping () -> Date = Date.init) {
        self.policy = policy
        self.defaults = defaults
        self.now = now
        self.decision = nil
        restoreDecision()
        scheduleExpiryRefresh()
    }

    public func updatePolicy(_ updated: AmanConsentPolicy) {
        let previousPropertyId = policy.propertyId
        let previousVersion = policy.policyVersion
        policy = updated
        policyAvailable = true
        if previousPropertyId != updated.propertyId {
            restoreDecision()
        } else if previousVersion != updated.policyVersion {
            defaults.removeObject(forKey: storageKey)
            decision = nil
        } else {
            restoreDecision()
        }
        scheduleExpiryRefresh()
        onEffectivePurposeStatesChanged?(effectivePurposeStates)
    }

    public func isAllowed(_ purposeId: String) -> Bool {
        guard let purpose = activePurposes.first(where: { $0.id == purposeId }) else { return false }
        if purpose.required { return true }
        guard policyAvailable else { return false }
        guard let decision, decision.propertyId == policy.propertyId, decision.channel == "ios",
              decision.policyVersion == policy.policyVersion, decision.expiresAt > now() else {
            return !purpose.consentRequired
        }
        return decision.purposes[purposeId] ?? !purpose.consentRequired
    }

    public func acceptAll() { saveChoices(Dictionary(uniqueKeysWithValues: activePurposes.map { ($0.id, true) }), action: .acceptAll) }
    public func rejectOptional() {
        saveChoices(Dictionary(uniqueKeysWithValues: activePurposes.map { ($0.id, $0.required) }), action: .rejectAll)
    }

    public func saveChoices(_ requested: [String: Bool], action: AmanConsentAction = .custom) {
        guard policyAvailable else { return }
        let choices = Dictionary(uniqueKeysWithValues: activePurposes.map { purpose in
            (purpose.id, purpose.required || (requested[purpose.id] ?? !purpose.consentRequired))
        })
        let optionalPurposes = activePurposes.filter { !$0.required }
        let recordedAction: AmanConsentAction
        switch action {
        case .acceptAll:
            recordedAction = optionalPurposes.allSatisfy { choices[$0.id] == true } ? action : .custom
        case .rejectAll:
            recordedAction = optionalPurposes.allSatisfy { choices[$0.id] == false } ? action : .custom
        case .custom:
            recordedAction = action
        }
        let capturedAt = now()
        let updated = AmanConsentDecision(
            eventId: UUID().uuidString.lowercased(),
            action: recordedAction,
            propertyId: policy.propertyId,
            policyVersion: policy.policyVersion,
            capturedAt: capturedAt,
            expiresAt: capturedAt.addingTimeInterval(TimeInterval(policy.retentionDays) * 86_400),
            channel: "ios",
            purposes: choices
        )
        decision = updated
        if let data = try? JSONEncoder().encode(updated) { defaults.set(data, forKey: storageKey) }
        scheduleExpiryRefresh()
        onConsentChanged?(updated)
        onEffectivePurposeStatesChanged?(effectivePurposeStates)
    }

    /// Reconciles an expired local choice with host SDKs. This is a state update, not a new user decision.
    @discardableResult
    public func refreshExpiredDecision() -> Bool {
        guard let current = decision else { return false }
        guard current.expiresAt <= now() else {
            scheduleExpiryRefresh()
            return false
        }
        expiryTimer?.invalidate()
        expiryTimer = nil
        defaults.removeObject(forKey: storageKey)
        decision = nil
        onEffectivePurposeStatesChanged?(effectivePurposeStates)
        return true
    }

    /// Disables optional purposes and clears the saved choice until updatePolicy receives a valid policy.
    public func markPolicyUnavailable() {
        policyAvailable = false
        expiryTimer?.invalidate()
        expiryTimer = nil
        defaults.removeObject(forKey: storageKey)
        decision = nil
        onEffectivePurposeStatesChanged?(effectivePurposeStates)
    }

    private func scheduleExpiryRefresh() {
        expiryTimer?.invalidate()
        expiryTimer = nil
        guard let current = decision else { return }
        let delay = current.expiresAt.timeIntervalSince(now())
        guard delay > 0 else {
            refreshExpiredDecision()
            return
        }
        let timer = Timer(timeInterval: delay, repeats: false) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.refreshExpiredDecision()
            }
        }
        expiryTimer = timer
        RunLoop.main.add(timer, forMode: .common)
    }

    private func restoreDecision() {
        guard let data = defaults.data(forKey: storageKey),
              let stored = try? JSONDecoder().decode(AmanConsentDecision.self, from: data),
              stored.propertyId == policy.propertyId,
              stored.channel == "ios",
              stored.policyVersion == policy.policyVersion,
              isValidStoredDecision(stored) else {
            defaults.removeObject(forKey: storageKey)
            decision = nil
            return
        }
        decision = stored
    }

    private func isValidStoredDecision(_ stored: AmanConsentDecision) -> Bool {
        let currentTime = now()
        let active = activePurposes
        let purposeIds = Set(active.map(\.id))
        let optional = active.filter { !$0.required }
        let duration = stored.expiresAt.timeIntervalSince(stored.capturedAt)
        guard stored.capturedAt.timeIntervalSince1970 >= 0,
              stored.capturedAt <= currentTime.addingTimeInterval(60),
              stored.expiresAt > currentTime,
              duration > 0,
              duration <= TimeInterval(policy.retentionDays) * 86_400,
              Set(stored.purposes.keys) == purposeIds,
              active.allSatisfy({ !$0.required || stored.purposes[$0.id] == true }),
              stored.eventId.map({ UUID(uuidString: $0) != nil }) ?? true else {
            return false
        }
        switch stored.action {
        case .some(.acceptAll): return optional.allSatisfy { stored.purposes[$0.id] == true }
        case .some(.rejectAll): return optional.allSatisfy { stored.purposes[$0.id] == false }
        case .some(.custom), .none: return true
        }
    }
}

public struct AmanConsentSheet: View {
    @ObservedObject private var manager: AmanConsentManager
    @Environment(\.dismiss) private var dismiss
    private let language: String
    @State private var choices: [String: Bool]

    public init(manager: AmanConsentManager, language: String? = nil) {
        self.manager = manager
        self.language = language ?? manager.policy.defaultLanguage ?? manager.policy.languages.first ?? "fr"
        let initial = Dictionary(uniqueKeysWithValues: manager.activePurposes.map { ($0.id, manager.isAllowed($0.id)) })
        _choices = State(initialValue: initial)
    }

    private var isArabic: Bool { language.lowercased().hasPrefix("ar") }
    private func copy(_ french: String, _ arabic: String) -> String { isArabic ? arabic : french }

    public var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    Text(copy("Choisissez les catégories que vous autorisez.", "اختر الفئات التي تسمح بها."))
                        .font(.subheadline).foregroundStyle(.secondary)
                    if !manager.policyAvailable {
                        Text(copy("La politique n’est pas disponible. Les finalités optionnelles restent désactivées.",
                                  "السياسة غير متاحة. ستظل الأغراض الاختيارية معطلة."))
                            .font(.callout).foregroundStyle(.red)
                    }
                    ForEach(manager.activePurposes) { purpose in
                        Toggle(isOn: Binding(
                            get: { choices[purpose.id] ?? false },
                            set: { choices[purpose.id] = $0 }
                        )) {
                            VStack(alignment: .leading, spacing: 5) {
                                Text(purpose.label.value(for: language)).font(.headline)
                                Text(purpose.description.value(for: language)).font(.caption).foregroundStyle(.secondary)
                                if let vendors = purpose.vendors, !vendors.isEmpty {
                                    Text(copy("Fournisseurs associés (indicatif) : ", "الموردون المرتبطون (للاسترشاد): ") + vendors.joined(separator: ", "))
                                        .font(.caption2).foregroundStyle(.secondary)
                                }
                            }
                        }
                        .disabled(purpose.required)
                        Divider()
                    }
                    if let notice = manager.policy.localizedNotice(for: language) {
                        DisclosureGroup(copy("Informations sur le traitement", "معلومات حول المعالجة")) {
                            VStack(alignment: .leading, spacing: 8) {
                                noticeRow(copy("Responsable", "المسؤول"), notice.controllerName)
                                noticeRow(copy("Contact", "جهة الاتصال"), notice.contact)
                                noticeRow(copy("Référence CNDP", "مرجع اللجنة الوطنية"), notice.processingReference)
                                noticeRow(copy("Données concernées", "فئات البيانات"), notice.dataCategories.joined(separator: ", "))
                                noticeRow(copy("Destinataires", "المستلمون"), notice.recipients.joined(separator: ", "))
                                noticeRow(copy("Transferts", "التحويلات"), notice.transfers.joined(separator: ", "))
                            }
                            .padding(.top, 8)
                        }
                        .font(.footnote)
                    }
                    HStack {
                        Button(copy("Tout refuser", "رفض الكل")) { manager.rejectOptional(); dismiss() }
                            .buttonStyle(.bordered)
                        Spacer()
                        Button(copy("Tout accepter", "قبول الكل")) { manager.acceptAll(); dismiss() }
                            .buttonStyle(.borderedProminent)
                    }
                    Button(copy("Enregistrer mes choix", "حفظ اختياراتي")) { manager.saveChoices(choices); dismiss() }
                        .frame(maxWidth: .infinity)
                }
                .padding()
                .disabled(!manager.policyAvailable)
            }
            .navigationTitle(copy("Vos préférences", "تفضيلاتك"))
            .navigationBarTitleDisplayMode(.inline)
            .environment(\.layoutDirection, isArabic ? .rightToLeft : .leftToRight)
            .onChange(of: manager.policy.policyVersion) { _ in
                choices = manager.effectivePurposeStates
            }
            .onChange(of: manager.policy.propertyId) { _ in
                choices = manager.effectivePurposeStates
            }
            .onChange(of: manager.policyAvailable) { _ in
                choices = manager.effectivePurposeStates
            }
        }
    }

    private func noticeRow(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).fontWeight(.semibold)
            Text(value).textSelection(.enabled)
        }
    }
}
