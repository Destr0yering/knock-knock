pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "KnockKnock"

include(":app")
include(":core:model")
include(":core:network")
include(":core:database")
include(":core:ui")
include(":feature:timeline")
include(":feature:review")
