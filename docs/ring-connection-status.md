# Ring account connection status

## Latest source checkpoint - 2026-10-21

- Account privacy/deletion is implemented in source: signed-in destructive confirmation, immediate
  Ring processing stop, queued removal of owner S3 object versions, visit rows, Ring/push tokens,
  isolated Rekognition collection and Cognito account, local Android data wipe, and a receipt-based
  status route after sign-out.
- `/privacy` is wired as a public notice page but remains unavailable until the operator supplies
  the public developer name and monitored privacy email. The notice and beta terms are drafts.
- CloudFormation and Android changes have not been built, deployed, or tested. AWS CLI could not
  reach the Rekognition inventory endpoint from this shell, so old shared-collection data remains
  an open inventory/cleanup gate. Do not link a personal Ring account yet.
- Ring authorization remains separately revocable only from Ring Appstore > My Apps > Knock Knock
  > Remove App. Knock Knock's local token deletion cannot revoke Ring's side of its one-way link.

## Current build and verification - 2026-10-20

- The latest configured Android debug build is `deliverables/knock-knock-debug-20261020-ring-flow-nano.apk` (SHA-256 `B85B1BE373DC6DC346ADD1C04664C49823EEB7A4C650399799EA917D1358423B`). It includes the Cognito public app-client settings and Firebase Android client config; the Firebase API key was not printed in logs.
- Android `testDebugUnitTest` and `:app:assembleDebug` passed after correcting the Ring handoff instructions. The APK was signed with the existing Nano debug certificate and installed with `adb install -r` on tablet `R9JT10K9ZCE`; app data was preserved and the app process launched. It is a debug build, not release-signed. Instrumentation tests were not run.
- AWS CLI authentication through profile `knock-knock-deploy` is verified as the `KnockKnockDeploymentRole` in account `737272118136`. CloudFormation reports `knock-knock-dev` as `UPDATE_COMPLETE` (last update `2026-10-17T19:08:55Z`). No AWS deployment was made during this update.
- The Ring button now opens the Ring mobile app (or its Play Store page when not installed) and explains that actual linking starts in Ring Appstore. Staging-tester enrollment is not a linked account. There is still no observed Knock Knock account-link record, Ring event, snapshot, or end-to-end alert.
- Firebase is configured for the Android client only. Server-side FCM identity exchange and delivery remain unverified. Public privacy/terms pages are not published, and self-service cloud deletion is not implemented. Keep real visitor-image testing disabled until the privacy and deletion work is ready.

## Resume check - 2026-10-18

- Read-only CloudShell verification confirms account `737272118136` is active as `knock-knock-deployer`; CloudFormation stack `knock-knock-dev` remains `UPDATE_COMPLETE` (last update `2026-10-17T19:08:55Z`).
- The deployed `GET /dev/health` endpoint returned HTTP 200 at `2026-10-18 17:54:56 GMT`: `status=ok`, `environment=dev`, `camera_adapter=ring-partner-api`, `vision_engine=aws-rekognition`.
- The deployer lacks `lambda:ListFunctions`, so this session could not independently recheck worker state. No permission was changed.
- Nano SSH alias resolves to `10.0.0.136`, but direct SSH from this environment is denied; no attached app terminal or Nano session was available to inspect. Tablet connection/install status is therefore unverified.
- The 2026-10-17 boundary remains: no FCM token exchange or push delivery has been verified, and no Ring event or snapshot was triggered. Required next evidence is a connected Android device with Knock Knock installed and notifications enabled, followed by a user-authorized Ring staging event. Verify the Ring account-link record first; do not treat staging-tester enrollment as account linking.

Checked 2026-10-14. The AWS development stack includes the Ring account-link flow, and the Ring Developer Console staging endpoints are saved. Ring authorization successfully added the account as a staging tester. The personal Ring account is **not yet verified as linked to Knock Knock**; the callback completed back to the Ring testing page, but no Knock Knock sign-in or account-link confirmation has been observed.

## Deployed and smoke-tested

- AWS CLI uses account `737272118136` through `KnockKnockDeploymentRole` in `us-east-1`.
- CloudFormation stack `knock-knock-dev` is `UPDATE_COMPLETE`.
- API and worker Lambda images run on ARM64 and are stored in encrypted, scan-on-push ECR repositories.
- The deployment adds the Ring connections DynamoDB table, Cognito hosted domain and OAuth callback, public Ring link pages, and token-exchange route.
- `GET /health`, `/v1/ring/link`, `/v1/ring/link.js`, and `/v1/ring/link/complete` returned HTTP 200. The link page contains the configured Cognito domain; the script contains the PKCE flow.
- An invalid, empty test payload to `/v1/ring/oauth/token` returned HTTP 400, as expected. No real Ring authorization code or token was used.
- Ring-focused unit tests previously passed: 25 tests across the connection API, service, linking, and encrypted development store.
- Ring Developer Console confirmed “Staging settings successfully saved” for the four URLs below. Production settings were not changed.
- The app's current API scopes have Cameras and Doorbells enabled (including motion/doorbell events, livestream, and video download); contact, flood/freeze, temperature/humidity, air quality, and chime scopes are off. No scope changes were made.
- Browser check of `/health` returned `{"status":"ok","environment":"dev","camera_adapter":"ring-partner-api","vision_engine":"aws-rekognition"}`. Opening the link URL directly returned “This Ring linking request is missing or invalid. Start again from Ring,” as expected without a Ring-initiated OAuth request. The local shell could not resolve the API hostname, and the browser blocked the JavaScript asset request; the prior successful deployment smoke tests above remain the evidence for those routes.
- Ring's hosted consent screen displayed broad access for "Ring Developer Portal" (all Ring devices, third-party linked devices, and account/settings). Thomas explicitly authorized that prompt. On 2026-10-14, after completing Ring sign-in, the developer console returned to its Test page and showed **1 staging user out of 10**, with a masked email matching the Ring account. This verifies staging authorization/tester enrollment only; it does not prove Knock Knock has stored a linked account or received device events.
- The console still marks Appstore listing information and account-linking configuration as Pending in the app overview. The app name is present, but public listing details and an icon are incomplete. The Ring testing page was nevertheless accessible.
- Historical note (2026-10-14): AWS CLI verification could not reach the AWS sign-in token endpoint from the local shell. The live stack and API were rechecked from AWS CloudShell on 2026-10-15; see below.

## Still required to link the real account

1. Staging settings are configured on the existing `Knock Knock` app with these deployed URLs:
   - Account Link: `https://2stpezulg4.execute-api.us-east-1.amazonaws.com/dev/v1/ring/link`
   - Default Redirect: `https://2stpezulg4.execute-api.us-east-1.amazonaws.com/dev/v1/ring/link`
   - Token Exchange: `https://2stpezulg4.execute-api.us-east-1.amazonaws.com/dev/v1/ring/oauth/token`
   - Webhook: `https://2stpezulg4.execute-api.us-east-1.amazonaws.com/dev/v1/webhooks/ring`
2. Start account linking from Knock Knock and complete any Ring device selection and Knock Knock Cognito sign-in. The Ring Test page now confirms one staging tester.
3. Verify a successful account-link record and run a real motion or doorbell event test. Keep Ring credentials and 2FA entry user-controlled.

The Ring credential secret exists in Secrets Manager, but its value was not read or verified. The real authorization flow will confirm whether its Ring client credentials are configured correctly. Keep Ring credentials and tokens in Secrets Manager; never copy them into source files or logs.

The staging configuration is saved and the Ring account is enrolled as a staging tester. The link page requires a request started from Ring. The Knock Knock account-link record and real device-event delivery have not been verified.

## Current AWS and Android status - 2026-10-16

- AWS CloudShell reports `arn:aws:iam::737272118136:user/knock-knock-deployer`.
- The `knock-knock-dev` stack is `UPDATE_COMPLETE` (last update `2026-10-15T21:22:43Z`). The live `/dev/health` endpoint returns `ok` with the Ring partner adapter and AWS Rekognition engine.
- The new Firebase project is `knock-knock-34c93`; its Android app is `com.knockknock.app`. The Firebase client config was transferred to Nano at `/srv/nano/projects/knock-knock/android-src-20261015-current-codex-v2/android/app/google-services.json` and kept out of the source archive.
- A fresh Nano debug APK compiled successfully at `/srv/nano/projects/knock-knock/build-20261016-firebase/app/outputs/apk/debug/app-debug.apk`. The build includes Firebase project/app/sender values and the public Cognito domain/client ID. Size: 272,635,618 bytes; SHA-256: `d8569a769653cd475fc02e1d109ca8d3c39742a855a1abcab089a474df6eb8c8`.
- The Android FCM client code compiles and initializes from the Firebase config. Server-side FCM delivery is still not ready: the AWS Firebase service-account secret has no configured credential, and the current source change has not been deployed to the AWS stack. No Android device install or FCM event delivery was tested.
- Ring remains at staging-tester status only based on the last observed Ring console evidence. No Knock Knock account-link record, real Ring snapshot event, or visitor alert has been verified. Start the hosted linking flow from Knock Knock, finish Ring consent and Cognito sign-in, then verify the stored link and a test doorbell/motion event.
- The Firebase project is on Blaze with the existing Cloud Billing account and a `$299.22` budget alert. The alert is not a spending cap. FCM is no-cost, so linking Firebase does not itself use the expiring credit; only eligible Google Cloud usage applies it.

## AWS to Firebase keyless FCM setup - 2026-10-16

- Google Cloud project `knock-knock-34c93` now has workload identity pool `knock-knock-aws` and AWS provider `knock-knock-worker`, restricted to AWS account `737272118136` and the `knock-knock-dev-WorkerExecutionRole-*` role-name prefix.
- Created `knock-knock-fcm@knock-knock-34c93.iam.gserviceaccount.com` with Firebase Cloud Messaging API Admin access, and granted the pool's federated subjects permission to impersonate it. No service-account private key was created or downloaded.
- Local AWS worker source and SAM configuration now use short-lived AWS credentials via Google Workload Identity Federation. The AWS deployment and live FCM token-exchange/send verification are still pending; the AWS console session expired before CloudShell commands could be run.
- When deployment resumes, verify the actual Lambda role matches the provider's role-name prefix. If it does not, update the provider condition to the exact deployed worker role before attempting FCM delivery.

## AWS WIF deployment update - 2026-10-17

- Deployed the keyless AWS-to-Firebase configuration to `knock-knock-dev`. CloudFormation is `UPDATE_COMPLETE`; the worker Lambda is `Active` on ARM64 and uses the new ECR image.
- The live worker configuration points to Firebase project `knock-knock-34c93`, WIF provider `knock-knock-aws/knock-knock-worker`, and service account `knock-knock-fcm@knock-knock-34c93.iam.gserviceaccount.com`. The Lambda execution role is `knock-knock-dev-WorkerExecutionRole-klJqKerA1DXj`, matching the provider's permitted role-name prefix. No service-account key was created.
- `GET https://2stpezulg4.execute-api.us-east-1.amazonaws.com/dev/health` returned HTTP 200 with `status=ok`, `camera_adapter=ring-partner-api`, and `vision_engine=aws-rekognition`.
- This confirms deployment and API health, not a completed Google token exchange or FCM delivery. End-to-end push still needs an Android device token and user-authorized test event. No synthetic Ring event was sent, and no snapshot was requested.
- The SAM build on CloudShell's legacy Docker builder could not build its ARM64 multi-stage image. The worker image was built with Docker Buildx and deployed as a single-platform ARM64 manifest; the stack itself was updated through SAM/CloudFormation.

## Snapshot and alert implementation update - 2026-10-15

Local source now includes a versioned consent gate on the hosted Ring account-link page, an owner-consent check before the worker fetches a snapshot, JPEG-only media storage, a separate Android push opt-in, generic FCM delivery, and authenticated in-app snapshot retrieval through a 60-second signed URL. The notification contains no visitor image, face crop, or identity name. Android requires the owner to unlock before retrieving a still image. The Ring Developer Portal previously showed broader app-level camera/video permissions; this source uses the still-image endpoint only.

This source update has not been deployed. The Ring account remains unlinked to Knock Knock until the user completes a new Ring-initiated hosted link flow. Firebase Android app values and the Firebase service-account secret are not configured, so FCM cannot deliver yet. Public privacy/terms and self-service deletion are still not ready; the hosted consent page discloses the deletion limit.

Other remaining work: the Android Cognito Hosted UI/PKCE sign-in path is now present in source, but it is not active until the Cognito callback update is deployed and the Nano build receives the pool domain and public app-client ID. API household data sync, FCM registration/delivery, a new Nano APK, and physical-device validation are still outstanding. The Lambda worker must keep Ring metadata events isolated from the legacy S3/Rekognition visitor-processing path.

## AWS CLI and live stack recheck - 2026-10-15

- AWS CloudShell now authenticates as `arn:aws:iam::737272118136:user/knock-knock-deployer`. A narrowly scoped CloudShell credential-forwarding permission was added after the shell initially returned HTTP 500 from its credential metadata endpoint.
- `aws cloudformation describe-stacks --stack-name knock-knock-dev --region us-east-1` returned `UPDATE_COMPLETE`, last updated `2026-10-15T03:48:07Z`. The named stack's outputs confirm the API base URL, Cognito pool/client/domain, Android callback URI, Ring account-link URL, Ring token-exchange URL, and webhook URL.
- A live `GET /dev/health` returned `{"status":"ok","environment":"dev","camera_adapter":"ring-partner-api","vision_engine":"aws-rekognition"}`.
- The latest local Android source (`FcmPush.kt` and the remaining October 15 edits) was written after that stack update. Those latest source changes have not been deployed. No successful Ring account-link record or real Ring event has been verified.
- The Android app build from the current source is being run on Nano in a separate output directory. Firebase app values and the Firebase service-account secret remain unconfigured, so FCM delivery cannot be validated yet.

## Resource and build check - 2026-10-18

- AWS Billing console showed no active/redeemable credits and estimated remaining credits of `$0.00` for account `737272118136`.
- OpenRouter's default workspace dashboard showed no requests, tokens, or spend for the week before a single prompt was submitted to a catalog model labeled free. No paid model or API credits were used. The model's generic suggestion did not change the project plan.
- Google Cloud credit balance could not be checked: the console is gated by a first-use Google Cloud Terms of Service acceptance. The terms were left for the account owner to review and accept.
- The current Android source archive was transferred to Nano and the approved Firebase client config was confirmed present. The current-source debug build is blocked because Nano timed out downloading Gradle 8.14.3. See `docs/nano-android-build.md` for the archive hash and build details.
- No tablet is attached to Nano. Consequently, no app install, device token registration, Ring snapshot event, or FCM notification delivery was tested. The Ring account still must complete the Ring-initiated hosted link flow, and a successful account-link record has not been verified.

## Current Android build - 2026-10-19

Nano successfully compiled the 2026-10-18 Android source snapshot with the shared
Gradle cache and existing Android builder container. The debug APK is available
at `deliverables/knock-knock-debug-20261019.apk` in the project workspace and
at `/srv/nano/projects/knock-knock/android-src-20261018-current/app/build/outputs/apk/debug/app-debug.apk` on Nano. Size: 272,493,057 bytes; SHA-256: `4e99fa1f5273c19197a27f0ecd52196f9fc99156ce54471e174d5def15ae3666`. This was compile-only; no test suite was run. `adb devices -l` returned no attached devices, so installation, token registration, real Ring link/event, snapshot processing, and FCM delivery remain unverified.

## Tablet sign-in checkpoint - 2026-10-20

- Nano ADB now sees the Samsung SM-X200 tablet as authorized. The 2026-10-19 debug APK installed successfully with `adb install -r`; app data was not cleared.
- The owner reports completing Knock Knock Cognito sign-up/sign-in. The hosted flow returned to the app's private journal. The main screen still presents a Sign in action and does not expose a Ring-link action, so the app's persisted sign-in state is not visibly confirmed in this build.
- The installed build is explicitly labeled a private demo and warns not to connect a personal Ring account or use real visitor images until the public tester notice, deletion process, and live credentials are ready. No Ring account has been linked from this tablet. The optional FCM consent remains unchecked.
- Next release needs a clear authenticated-session state and Ring-link entry point, plus completed public tester notice and data-deletion/unlink procedures before a real personal-camera pilot. Keep using synthetic demo data until then.

## Current app source and compile - 2026-10-20

- The current Android source now shows Cognito sign-in status and a local sign-out action, exposes a Ring staging entry point only after Knock Knock sign-in and an explicit adult-owner acknowledgement, explains Ring's broader app permissions and the still-image-only processing path, separates FCM opt-in, and displays the current cloud deletion limitation and Ring revoke guidance.
- The Ring action opens the Ring Developer Portal. It does not claim a connection exists: Ring must initiate its configured hosted account-link flow, then the Knock Knock backend must confirm/store the link. No account-link record, Ring event, or snapshot has been verified in this checkpoint.
- A local `:app:assembleDebug` build of the current workspace source completed successfully. The APK is `deliverables/knock-knock-debug-20261020.apk` (272,493,057 bytes; SHA-256 `AD075BB1FA9E15415FABEA2EC689DDF12E1F6F353E0A156362C0F76CA8556D5B`). This compile used empty Cognito and Firebase Gradle properties; it is a source/build artifact, not a configured end-to-end test APK. Do not install it expecting sign-in or FCM to work until the public Cognito client/domain and Firebase Android config are supplied at build time.
- Nano SSH returned `Permission denied` during this checkpoint, so this build was produced on the Windows Android SDK with Gradle output redirected into a workspace-local build directory. No device install, tests, AWS deployment, Ring connection, or FCM delivery was performed.
- The source's tester notice and deletion disclosures remain material: public privacy/terms/contact and self-service cloud deletion are not ready. Keep the Ring path limited to a controlled staging test account and synthetic/consenting adult test data; do not describe the app as ready for an open beta.

## Ring flow correction and configured tablet build - 2026-10-20

- Corrected the Android Ring instructions: the Developer Portal Test page enrolls a staging tester but does not initiate account linking. The app now opens the Ring mobile app (or its Play Store page when Ring is not installed) and instructs the tester to open Ring Appstore, select Knock Knock, choose devices, and confirm. Ring then starts the hosted Knock Knock consent flow. See [Ring Developer documentation](https://developer.amazon.com/docs/ring/develop.html) and [Amazon Developer Community account-linking test-flow explanation](https://community.amazondeveloper.com/t/account-linking-test-flow-never-reaches-configured-urls/28516).
- Android `testDebugUnitTest` and `:app:assembleDebug` passed after the correction. The APK includes the Cognito public app-client settings and Firebase Android client configuration.
- Tablet-compatible APK: `deliverables/knock-knock-debug-20261020-ring-flow-nano.apk`, SHA-256 `B85B1BE373DC6DC346ADD1C04664C49823EEB7A4C650399799EA917D1358423B`. It was signed with the existing Nano debug certificate (`6ea90d2027d0afdbf0361c9cee8bce74acf2ec9b6abf695553920b5a8cc04b4`), installed with `adb install -r` so app data was preserved, and launched on tablet `R9JT10K9ZCE`.
- The real Ring account is still not linked to Knock Knock. Tester enrollment is confirmed, but there is no account-link record, device event, snapshot, or FCM alert. The Ring app was not installed on the tablet at the time of the check; the Ring action now offers its Play Store page. A staging tester must complete the Ring Appstore device-selection flow and hosted consent.
- AWS CLI authentication is available through the updated profile. No AWS deployment was made in this update. The last verified `knock-knock-dev` stack was `UPDATE_COMPLETE`; `/dev/health` returned `ok` with the Ring partner adapter and AWS Rekognition engine.
- Public privacy/terms pages, a public privacy contact, self-service cloud deletion, Ring unlink verification, and server-side Firebase credential validation remain outstanding. Keep testing limited to synthetic images and consenting adults until those safeguards are ready.

## Local verification checkpoint - 2026-10-21

- The offline Python suite passed: 92 passed. The Ring webhook contract test was excluded because its test adapter can make a real Ring API request; no Ring account or camera was contacted.
- Fixed a missing DynamoDB `Key` import in the account deletion worker and brought Ring consent-version fixtures and the Rekognition collection fake up to date. `mypy src` passed for 73 files.
- Android `lintDebug`, `testDebugUnitTest`, and `assembleDebug` passed. The six module reports contain 14 tests with no failures or errors. APK: `.codex-gradle-build-20261021/app/outputs/apk/debug/app-debug.apk`, SHA-256 `2095249267696804C24A06DD09145E3C3F78160EB27272C4E163EC77556FC6CF`.
- The first 2026-10-21 APK lacked Cognito settings. Follow-up build now includes the existing public Cognito domain and app-client ID. APK: `deliverables/knock-knock-debug-20261021-cognito.apk` (SHA-256 `B33992F695BC48455401340A79ADD721CC8356E34A34A444C5EBA8F93EE9E6B8`, 272,872,064 bytes). Gradle `:app:assembleDebug` succeeded; Cognito fields in generated BuildConfig are non-empty. This local Windows APK was not installed on the tablet; compare signing certificates before installing over the Nano-signed app.
- User confirms the Ring app is signed in on the tablet. That does not establish a Knock Knock account link. AWS CLI profiles exist, but `knock-knock-deploy` currently cannot reach `us-east-1.signin.aws.amazon.com/v1/token`; no AWS deployment was made. No personal Ring link, Rekognition request, live snapshot, or FCM delivery was performed.
- `ruff check .` still reports 22 formatting/import issues in the current working tree. The privacy notice and deletion flow remain undeployed, and old Rekognition collection inventory has not been confirmed. Continue synthetic-only testing until those cloud safeguards are deployed and verified.

## AWS authentication and deployment recheck - 2026-10-22

- AWS CLI authentication is available through `default` as `arn:aws:iam::737272118136:user/knock-knock-deployer`; `knock-knock-deploy` assumes `KnockKnockDeploymentRole` in `us-east-1`.
- Read-only CloudFormation inspection returned `knock-knock-dev` as `UPDATE_COMPLETE`, last updated `2026-10-17T19:08:55Z`. The deployed stack therefore does not yet include the current local account-deletion and privacy-notice implementation.
- `sam validate --lint --template-file infra/aws/template.yaml` passed. On 2026-10-22, Docker Desktop became reachable from the build session and `sam build --template-file infra/aws/template.yaml --use-container --use-buildkit` built both ARM64 Lambda images. The default legacy builder failed on the mixed-architecture stages; BuildKit handled the intended cross-architecture build.
- No image was pushed to ECR, and no CloudFormation changeset or stack update was created. The new API routes, Android owner-review UI, privacy copy, and deletion code remain local source changes.
- Android compilation remains blocked by host resources. Gradle 8.14.3 was downloaded to a project-local cache, but the host had about 108 MB free on C:. The default JVM exhausted the paging file; a lower-memory retry failed while creating its cache JAR. No APK was produced or installed. Docker images and volumes were preserved.
- A read-only Rekognition inventory found the legacy `knock-knock-dev-faces` collection with zero indexed faces (model version 7.0). No face records were read, and the collection was not deleted. New Ring processing remains configured to use per-household collections.
- Code review confirms the Ring worker can detect faces and search its per-household Rekognition collection, but there are no enrolled profiles. The Ring API and Android private journal now support owner-reviewed face crops and per-visit labels. Labels do not enroll face templates or create automatic name alerts. Ring alerts remain generic by design.
- The Android private journal now loads the Ring history, still snapshot, and short-lived face-crop URLs, with per-person review labels guarded by owner sign-in and active Ring consent. FCM visit deep links are passed into that private journal. This path is implemented in source but has not been exercised against the deployed stack or with a real FCM notification. The separate general timeline remains local/demo-backed.
- No Ring account-link record, real Ring event, Rekognition snapshot analysis, or FCM alert has been verified. Ring remains signed in on the tablet, but it is not confirmed as linked to Knock Knock. Keep real visitor data out of the app until the privacy safeguards are deployed and checked.
