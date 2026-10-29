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

rootProject.name = "DoorMemo"

include(":app")
include(":core:model")
include(":core:network")
include(":core:database")
include(":core:ui")
include(":core:camera")
include(":core:vision")
include(":core:privacy")
include(":core:evidence")
include(":feature:timeline")
include(":feature:review")
