# Knock Knock controlled tester readiness

Status: internal draft for the limited synthetic-data pilot. This is not a public
privacy policy, a contract, or legal advice. Updated October 21, 2026: deletion and
privacy-notice code is prepared but not deployed or end-to-end verified.

## Current source checkpoint - 2026-10-21

- The API now has a signed-in `DELETE` account-deletion request, immediate household processing
  tombstone, asynchronous SQS worker, receipt-only public status endpoint, and Cognito deletion
  after cleanup. Active household S3 object versions, DynamoDB visit rows, push/Ring tokens, and the
  owner's Rekognition collection are included. Android erases its local databases, vault, account
  tokens and preferences after the server accepts the request.
- Ring event processing is blocked by the tombstone. Ring account removal is still a separate user
  action at Ring Appstore > My Apps > Knock Knock > Remove App.
- A public `/privacy` page is wired and configured for Got2Get2Work and
  got2get2worksupport@gmail.com. Confirm the mailbox is monitored; the page still requires an
  infrastructure deployment and privacy review before it is public.
- AWS has not accepted the infrastructure update yet. The AWS CLI's read-only Rekognition inventory
  check could not reach AWS from this shell; old shared-collection faces therefore remain an
  inventory/cleanup gate. New Ring processing uses owner-isolated collections, and generic,
  unscoped API enrollment/visitor routes are disabled in the Ring service.
- The source change has not been built, deployed, or tested. Keep real Ring data disabled until
  deployment, the deletion flow, public notice and legacy collection cleanup are confirmed.

## Pilot boundary

- Test the Android workflow with the built-in synthetic visitors and generated demo images.
- Do not connect a personal Ring account or upload, capture, enroll, or share a real person's
  face image until the public-facing privacy notice, tester terms, consent flow, data deletion
  route, Firebase setup, and Ring staging path have been reviewed and enabled.
- Never use covertly captured footage. The tester must own or administer the camera, have
  authority to connect it, and notify household members and visitors before any real capture.
- Limit pilot invitations to adults who can consent for themselves; the production household
  policy's 13+ minimum is not a substitute for parental consent or child privacy review.
- Keep the synthetic demo mode available if the Ring, network, or cloud path fails.

## Tester briefing checklist

Before a live-data pilot, provide each tester with:

1. The app's public privacy policy and beta terms, including developer identity and a working
   privacy contact.
2. A prominent in-app notice describing face detection/recognition, images and clips, event
   metadata, cloud processing, AWS/Ring/notification providers, and retention.
3. Separate affirmative choices for biometric processing and optional push notifications.
   Declining must not be treated as consent; explain the demo-only alternative.
4. A clear Ring account unlink/revoke procedure and a working account/data deletion-request path.
5. The fixed retention behavior: unsaved photos/crops for 30 days, saved images until the
   approved deletion process, visit logs for one year, and profile/audit retention details.
6. Instructions to use consenting household participants and staged visitors, avoid minors,
   neighbors, passersby, and sensitive locations, and stop capture if someone objects.
7. A privacy incident/contact route and a process to stop processing, revoke credentials, and
   respond to an accidental capture.

## Product and policy decisions still open

- Confirm the deployed deletion worker, all S3 versions, DynamoDB rows, tokens, Rekognition
  collection, Cognito account, and signed-out receipt flow.
- Confirm the monitored privacy contact mailbox and the public operator name are accurate.
- Publish a stable, public, non-editable privacy policy URL before Play testing that collects
  real user data; keep the in-app policy version and Play Console Data Safety answers aligned.
- Have qualified counsel review facial/biometric processing and notices for each pilot location.
- Keep acceptance of the synthetic-demo notice distinct from consent to process real people or
  biometric data. The Android source records only the former.

## Current readiness

### Verified on 2026-10-20

- Android unit tests and `:app:assembleDebug` passed after correcting the Ring entry instructions. The configured, Nano-signed APK is `deliverables/knock-knock-debug-20261020-ring-flow-nano.apk` (SHA-256 `B85B1BE373DC6DC346ADD1C04664C49823EEB7A4C650399799EA917D1358423B`). It was installed in place on tablet `R9JT10K9ZCE` and launched; existing app data was preserved.
- The app now starts the linking handoff in the Ring mobile app and explains that actual linking begins in Ring Appstore. Ring Developer Portal staging enrollment is not proof of a linked account. No Knock Knock account-link record, Ring event, snapshot, or FCM delivery has been verified.
- AWS CLI authentication works with the updated profile. The last verified `knock-knock-dev` stack was `UPDATE_COMPLETE`; `/dev/health` reported the Ring partner adapter and AWS Rekognition engine. No AWS deployment was made in this update.
- The Android Firebase client is configured, but live FCM delivery and the server-side Firebase identity exchange remain unverified. Cognito sign-in is compiled into the app but has not been confirmed in a live device session.
- Public privacy notice and tester terms remain drafts pending the developer's chosen public identity and privacy contact. The deletion source flow now covers new owner-scoped Ring records, but is not deployed; the legacy shared Rekognition collection needs inventory. Keep this for technical review and synthetic/demo testing, not external live-data testing or an open beta.
- Keep pilot use to synthetic images until a real-camera pilot has published privacy terms, a working deletion/unlink process, and an explicit, reviewed biometric-consent flow. For any controlled account-link exercise, use only a Ring account/device administered by the tester and consenting adults.

- Internal privacy inventory and retention design: present in `privacy-and-retention.md`.
- The app includes a separate Ring consent gate, separate Android push opt-in, generic lock-screen alerts, authenticated snapshot retrieval, and consented-token revocation. These features have not all been validated end to end against live services.

## Deployment and Ring identity status - 2026-10-22

- AWS authentication is restored, but the dev stack remains at its 2026-10-17 deployment. The latest privacy notice, account-deletion worker, and owner-reviewed per-visit labeling are local source changes. SAM template lint validation and a local `sam build --use-container --use-buildkit` both passed for the ARM64 API and worker images. Nothing was deployed.
- The read-only Rekognition inventory found the legacy shared `knock-knock-dev-faces` collection with zero indexed faces. It was not deleted. New Ring events are configured to use a per-household collection.
- The cloud Ring worker can detect faces and search an owner's collection. The Ring API and Android private journal now include owner-reviewed face crops and per-visit labels, guarded by owner authentication, active Ring consent, deletion status, household ownership, and short-lived signed URLs. These labels annotate one visit only; they do not enroll a face template or enable automatic name alerts. FCM remains generic by design and includes no name or image.
- Android's private journal source calls `/v1/ring/visits`, fetches the short-lived signed snapshot and face-crop URLs, gates review behind device unlock, and keeps decoded bitmaps in memory. A Ring FCM deep link is wired to that view. The path remains unverified against the deployed stack and a real notification; the general timeline remains local/demo-backed.
- No Ring account-link record, live event, snapshot, Rekognition analysis, deletion job, or FCM delivery has been verified. The latest API and Android changes are local source only. Keep the personal Ring account and real visitor images out of the application until the stack and app are rebuilt and deployed and the safeguards are exercised.
- Android compilation remains unverified. The Gradle distribution was downloaded, but the host has about 108 MB of free C: space; Gradle's JVM first exhausted the paging file and its low-memory retry failed while creating a cache JAR. No APK was produced or installed. Docker images and volumes were left intact.

## Suggested tester invitation

> I'm preparing a limited test of Knock Knock, an Android app that helps organize doorbell
> visits. Would you be interested in a short feedback session using synthetic demo events? No
> Ring connection or real visitor footage is needed for this session. If we later invite you to a
> live Ring test, we'll first share the data practices, consent flow, retention schedule, and
> unlink/deletion instructions.

