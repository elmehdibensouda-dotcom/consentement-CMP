import org.gradle.api.publish.maven.MavenPublication

plugins {
    id("com.android.library")
    id("maven-publish")
}

group = "ma.aman"
version = "0.1.0"

android {
    namespace = "ma.aman.consent"
    compileSdk = 37

    defaultConfig {
        minSdk = 23
        consumerProguardFiles("consumer-rules.pro")
    }

    publishing {
        singleVariant("release") { withSourcesJar() }
    }
}

publishing {
    publications {
        register<MavenPublication>("release") {
            groupId = "ma.aman"
            artifactId = "aman-consent-android"
            version = project.version.toString()
            afterEvaluate { from(components["release"]) }
        }
    }
    repositories {
        maven {
            name = "localBuild"
            url = uri(layout.buildDirectory.dir("repository"))
        }
    }
}
