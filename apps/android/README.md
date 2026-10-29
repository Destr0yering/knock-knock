# DoorMemo Android

Native Kotlin/Jetpack Compose client for the DoorMemo household visitor workflow.

## Local build

```powershell
cd apps\android
.\gradlew.bat lintDebug testDebugUnitTest assembleDebug
```

The debug build defaults to the configured DoorMemo development API. Override it with the
`apiBaseUrl` Gradle property when building for another environment. Cognito Hosted UI sign-in
uses authorization code + PKCE; access, ID, refresh tokens, and the temporary
PKCE verifier are encrypted with an Android Keystore AES-GCM key. No Cognito client secret is used.

For FCM builds, provide these Gradle properties: `firebaseProjectId`, `firebaseApplicationId`,
`firebaseApiKey`, and `firebaseSenderId`. These are Firebase client configuration identifiers,
not server credentials. The Firebase service-account JSON belongs in the AWS Firebase Secrets
Manager secret; never put its private key in Android or source control. Generic push registration
stays disabled until Firebase client configuration is present. The API URL defaults to the current
dev API and can be overridden with `apiBaseUrl`.

To configure sign-in, deploy the AWS template with the registered native callback
`knockknock://auth/callback`, then pass the Cognito domain and public app-client ID as Gradle
properties when building:

```powershell
./gradlew :app:assembleDebug `
  -PcognitoDomainUrl=https://YOUR_DOMAIN.auth.us-east-1.amazoncognito.com `
  -PcognitoClientId=YOUR_PUBLIC_APP_CLIENT_ID
```

These are public client settings, not secrets. The default Gradle values are empty, so the app
shows an unconfigured status and does not start an OAuth flow until both are supplied. The Ring
account-link callback remains separately configured in CloudFormation.

Modules are intentionally separated into app assembly, core model/network/database/UI, and
feature packages so production Cognito and AWS adapters can replace the demo boundaries without
rewriting screens.

