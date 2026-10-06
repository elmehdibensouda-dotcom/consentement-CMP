plugins {
    id("com.android.application")
}

android {
    namespace = "ma.aman.consent.sample"
    compileSdk = 36

    defaultConfig {
        applicationId = "ma.aman.consent.sample"
        minSdk = 23
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}

dependencies {
    implementation(project(":aman-consent"))
}
