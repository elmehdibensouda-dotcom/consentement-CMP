// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AmanConsent",
    platforms: [.iOS(.v16)],
    products: [.library(name: "AmanConsent", targets: ["AmanConsent"])],
    targets: [
        .target(
            name: "AmanConsent",
            path: "mobile/ios/Sources/AmanConsent",
            resources: [.process("PrivacyInfo.xcprivacy")]
        )
    ]
)
