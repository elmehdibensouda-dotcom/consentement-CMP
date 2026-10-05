// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "AmanConsent",
    platforms: [.iOS(.v16)],
    products: [.library(name: "AmanConsent", targets: ["AmanConsent"])],
    targets: [
        .target(name: "AmanConsent", resources: [.process("PrivacyInfo.xcprivacy")])
    ]
)
