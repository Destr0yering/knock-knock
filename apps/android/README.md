# Knock Knock Android

Native Kotlin/Jetpack Compose client for the Knock Knock household visitor workflow.

## Local build

```powershell
cd apps\android
.\gradlew.bat lintDebug testDebugUnitTest assembleDebug
```

The debug build defaults to the Android emulator loopback address (`10.0.2.2:8000`) and uses
the local demo session. It contains no Ring, AWS, Rekognition, Cognito, or FCM credentials.

Modules are intentionally separated into app assembly, core model/network/database/UI, and
feature packages so production Cognito and AWS adapters can replace the demo boundaries without
rewriting screens.

