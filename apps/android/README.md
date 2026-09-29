# Knock Knock Android client

The Android application is a presentation client for the backend API. It will display the live
visitor inbox, ask the user to confirm or correct suggested identities, enroll profiles, and show
visit history. It must not contain Ring client secrets, HMAC keys, AWS credentials, or biometric
templates. Those stay behind the backend ports defined in `src/knock_knock/ports/`.

The initial repository focuses on the testable service boundary. A Kotlin/Jetpack Compose client
can be added here once the API contracts are accepted.

