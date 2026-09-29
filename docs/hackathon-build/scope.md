# Project Scope

## Project Name Candidates

- **Knock Knock** (selected)
- DoorSense
- Familiar Door

Tagline: **Know who's at the door before the knock knock!**

## One-Line Summary

Knock Knock is a privacy-conscious Android companion for Ring that turns doorbell freeze frames into human-confirmed familiar-person suggestions, unknown-visitor tags, timely alerts, and a searchable household visit history.

## Target User

The hackathon MVP serves a homeowner or household member who wants fast context about who is at the door without surrendering identity decisions to an opaque model. The future product may serve small businesses, but business administration is outside this submission.

## Problem

Doorbell notifications show that something happened but often leave the user to reopen footage, remember prior visits, and manually establish context. Existing alerts can become noise, while autonomous facial identification creates privacy and trust risks. Households need a clear event record that learns only from identities they explicitly verify and makes uncertainty visible.

## Core Workflow

1. A Ring motion or doorbell event arrives through the official Ring API or simulator. During development and fallback testing, the same pipeline accepts an uploaded freeze frame.
2. The camera adapter normalizes the media into a common visitor-event input.
3. The swappable vision engine detects a face and returns either a possible familiar profile with confidence or `unknown`.
4. The Android app alerts the user and presents the freeze frame, event time, source, and suggestion.
5. The user confirms the suggestion, corrects it, or categorizes and tags the visitor as unknown, delivery, service, neighbor, or another household-defined label.
6. The verified result becomes part of the local visit history and may improve later suggestions.
7. The user can search, filter, review, and propose relabeling stored visitor events and familiar profiles; security history is governed by fixed retention rather than manual deletion.

The user is always the identity authority. A model suggestion never unlocks a door or causes an access-control action in the MVP.

## What We Are Building

- An Android application focused on daily private-family use.
- A modular camera-adapter layer with an official Ring API/simulator implementation and an uploaded-frame test implementation.
- A common event-processing pipeline for motion/ding events and freeze frames.
- A replaceable face-identification interface, initially backed by AWS services for the AWS Builder mini challenge, with a local/mock implementation for offline development and deterministic demos.
- Familiar-person enrollment based on user-verified images and labels.
- Confidence-aware suggestions that clearly distinguish possible matches from verified identities.
- Unknown-visitor categorization and custom tagging.
- Android alerts linking directly to the event review screen.
- A searchable, filterable visitor timeline with timestamps, source, confidence, verification status, and user notes.
- Clear fixed-retention disclosures, administrator-reviewed relabeling, and the ability to disable cloud processing.
- Repeatable test fixtures, setup instructions, and a demo mode that uses known sample frames without depending on a live visitor.
- Documentation of Ring and AWS integration, developer friction, privacy boundaries, and limitations.

## What We Are Not Building

- Automatic unlocking, locking, gate operation, alarm control, or any autonomous access decision.
- A claim of infallible facial recognition or definitive identity without user confirmation.
- Continuous surveillance, live location tracking, emotion inference, demographic classification, or criminal-risk scoring.
- A complete business dashboard, employee attendance system, customer analytics platform, or multi-site administration.
- Appstore production certification or a public commercial launch before the hackathon deadline.
- Training a custom foundation model or building a large-scale face dataset.
- Dependence on a physical Ring device; the official simulator is the required judging path, while a real device is optional.

These items are deferred to keep the demonstration credible, testable, privacy-conscious, and complete before submission.

## Inspiration And References

- Familiar-face alert products demonstrate the value of concise identity context, but Knock Knock makes user verification and uncertainty central rather than treating model output as fact.
- Ring's event timeline provides a familiar model for reviewing door activity; Knock Knock enriches that timeline with verified household meaning and searchable tags.
- Local-first security systems show why retention and deletion controls matter for sensitive home imagery; Knock Knock keeps adapters and storage modular so cloud processing can be replaced or disabled.

## Time Budget And Delivery Guardrails

The official submission deadline is **October 23, 2026 at 12:00 PM Pacific / 3:00 PM Eastern**. The working schedule is:

- Core Android workflow complete by October 12.
- Official Ring simulator/API integration complete by October 16.
- Reliability, privacy, and end-to-end testing October 17–20.
- Demo recording and documentation October 21.
- Submission targeted for October 22, leaving October 23 as emergency buffer.

The official requirements do not specify a separate Amazon Appstore approval or testing window. The repository must include working Ring integration, and the demo must show the project through a Ring simulator or actual device.

## Demo Path

1. Trigger a Ring simulator motion or ding event.
2. Show the Android alert and open the captured freeze frame.
3. Demonstrate a familiar-person suggestion with visible confidence, then confirm or correct it.
4. Trigger or upload an unknown visitor frame and tag it as a delivery or custom category.
5. Open the visitor history, filter by identity/category, and inspect the verified audit trail.
6. Save a photo before expiry and show the immutable relabeling audit trail.
7. Briefly show the adapter boundary and AWS integration so judges can see that Ring and AWS are used in working code.

The public English demo video will remain under three minutes and lead with the end-to-end workflow.

## Submission Story

Most doorbell applications stop at motion alerts and footage. Knock Knock turns those raw events into useful household memory while keeping people—not AI—in charge of identity. It uses official Ring technology for event capture, a swappable vision engine for AI-assisted matching, and a privacy-first Android experience for verification, alerts, and history. This goes beyond a basic Ring notification by delivering a caretaking-oriented context layer that is technically modular, demonstrable without special hardware, and positioned for future access-control and business integrations without placing those higher-risk features in the MVP.
