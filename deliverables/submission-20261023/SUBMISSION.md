# Knock Knock

**Tagline:** Visitor awareness with household control: separate people, explicit uncertainty, and owner-reviewed identity suggestions.

## Inspiration
A motion alert tells a household that something happened. Understanding who arrived together still takes attention and judgment. We built a visitor-awareness prototype that treats every person separately and keeps a household member, rather than a model score, in charge of identity decisions.

## What it does
Knock Knock includes an Android companion and a modular Python backend for Ring-style visitor events. The demonstrated synthetic workflow ingests a three-person arrival, returns a generic learning-period alert, separates advisory, unknown, and face-undetected results, accepts a member's label proposal, rejects that member's attempt to approve it, and lets the owner approve the change with an attributable audit record.

The source also contains an official Ring API adapter, signed webhook handling and account-linking routes, snapshot processing, an AWS Rekognition adapter, Android authentication and push integration, consent checks, and account-deletion work. These integrations have different validation states. The video is an actual deterministic backend run, not a demonstration of a linked personal Ring account or live facial recognition.

## How we built it
Android uses Kotlin, Jetpack Compose, Room, and Firebase messaging. The Python backend uses FastAPI with replaceable camera, vision, queue, media, and repository adapters. AWS SAM defines API Gateway, Lambda, SQS and a dead-letter queue, Rekognition, private S3 storage, DynamoDB, Cognito, Secrets Manager, and CloudWatch resources.

Ring events are intended to enter through the official signed-event boundary and queue bounded still-image processing. Recognition remains advisory. The current Ring snapshot workflow does not enroll a person's face merely because someone types a visit label, and it does not promise automatic named alerts.

Codex assisted with architecture, Android and backend implementation, infrastructure, debugging, documentation, and build work. Nano offloaded storage and Android compilation. The submitted demo uses deterministic synthetic fixtures; it does not send personal images to an AI video model.

## Demonstration and validation
On October 23, we executed `scripts/run_local_demo.py` in the existing Nano API container checkpoint dated October 15. The captured output shows a three-person event, the generic alert, a member approval receiving HTTP 403, an owner approval succeeding, saved-media state, and audit events. The exact captured result is included with the video materials.

The latest Android source assembled on Nano on October 23. Its debug APK passed archive integrity and APK v2 signature verification. Its SHA-256 is `36e83f4b18f2ef75ce90d90709964d020ac537369b126179cb92afa45a5e624f`. That new APK was not installed or exercised end to end as part of the final build check.

Earlier project checks and their dates are recorded in `docs/hackathon-build/build-notes.md`. We do not claim that those earlier test results validate every subsequent source change.

## What remains unverified
Personal Ring account linking, a real Ring snapshot reaching Rekognition, and end-to-end FCM delivery have not been demonstrated. Ring staging-tester enrollment is not proof of account linking. Public privacy materials and self-service cloud deletion exist in current source but their updated deployment and real-device behavior remain pending. Real visitor-data testing should wait for those safeguards to be deployed and checked.

The video demonstrates a custom deterministic Ring-style fixture path, not the official Ring Playground or a physical Ring device. This may limit eligibility under the organizer's requirement to show the Ring integration working. We make no claim that this limitation is waived.

## Challenges
The most significant friction was distinguishing tester enrollment from completed Ring account linking, keeping Cognito and Firebase configuration consistent across builds, and building the Android dependency graph on Nano's ARM machine using an emulated x86 toolchain. A temporary direct network route resolved Maven access; the VPN route was restored afterward. Separating source implementation, deployment, and observed behavior helped keep the final claims accurate.

## What we learned and what's next
Recognition uncertainty and household authorization must be first-class product behavior. Next steps are deployment and deletion verification, a hosted Ring consent test, real still-image processing with consenting adults, and an observed Android push alert. We also want a simpler Ring developer onboarding path and a clear diagnostic that distinguishes tester enrollment from an active app link.

## Source and testing
Repository: https://github.com/Destr0yering/knock-knock

Use the current submission branch when reviewing later changes: https://github.com/Destr0yering/knock-knock/tree/codex/knock-knock-mvp

The repository includes an MIT license. To reproduce the synthetic demo, install the documented Python dependencies and run `python scripts/run_local_demo.py` from the repository root. Do not supply personal Ring credentials or private visitor images for that demo.

## Product feedback
**Tools and use:** Ring API contracts for linking and signed events; AWS SAM, Lambda, API Gateway, SQS, Rekognition, S3, DynamoDB, Cognito, and CloudWatch for the serverless architecture; Kotlin/Compose/Room and Firebase messaging for Android. Codex supported implementation and integration work, with Nano handling storage and builds.

**What worked well:** Modular interfaces made it possible to exercise household review and authorization with synthetic data. AWS infrastructure as code made the intended deployment reviewable. Compose supported explicit unknown and face-undetected states.

**What needs improvement:** Ring staging enrollment and account-link completion need clearer, separate status indicators and an end-to-end example. Cloud credentials, OAuth configuration, and Firebase federation were difficult to diagnose across hosts. Android builds were especially slow under emulation.

**Onboarding:** We reached a configured staging tester and deployed development endpoints, but did not verify a personal account link. A guided test that proves callback, token exchange, event delivery, snapshot retrieval, and push delivery would improve onboarding.

**Would we build with it again:** Yes, with simulator-first integration, a documented credential handoff, and explicit deployment checkpoints. We would finish privacy/deletion validation before onboarding households with real visitor data.

## Form answers requiring participant input
Country of residence, age eligibility, jurisdiction eligibility, and employee restrictions must be answered by Thomas. They have not been inferred. Upload the finished video publicly to YouTube or Vimeo and paste that URL into Devpost; a local MP4 is not a hosted video URL.

Primary track: Ring. AWS Builder: documented AWS integration in source; live recognition remains unverified. Open Source: MIT-licensed repository. GitHub username: Destr0yering. Project timing: new project started during the hackathon, with subsequent work recorded in Git history.
