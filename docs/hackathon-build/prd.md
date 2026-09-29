# Product Requirements Document

## Product Summary

Knock Knock is an Android companion for Ring that helps a household understand who visited without treating an AI prediction as fact. It receives Ring motion and doorbell events, reports how many people are visible, collects useful face images from associated clips, and asks a human to identify each detected person for that visit. Over time, confirmed usage builds familiar-person profiles that support cautious identity suggestions, alerts, and a durable visitor history.

The product follows a trust-building model. During the first 30 days, notifications never name a person; they report only that visitors were detected and how many people were found. Users review events and identify people, allowing the system to gather multiple confirmed facial examples from clips. After the learning period, the app may include a tentative familiar-person suggestion only when confidence is high. Low-confidence results remain generic and every identity remains reviewable.

The Ring account owner is the sole household administrator. Invited household members aged 13 or older share access to the household's visitor data but cannot directly administer profiles or household membership. Identity changes are attributed and preserved in an immutable profile-modification log.

## Product Principles

1. **Humans establish identity.** AI output is always a suggestion until confirmed.
2. **Trust is earned through use.** The app learns from confirmations, corrections, merges, and relabeling instead of making named alerts immediately.
3. **Uncertainty is visible.** Low confidence, missing faces, and incomplete processing are clearly labeled.
4. **A visit can contain multiple people.** Each detected person is reviewed independently while remaining linked to one visit.
5. **Security history is durable.** Profile changes are attributable, visitor records remain available for one year, and retention schedules cannot be weakened by household members.
6. **Sensitive media is minimized.** Unsaved visitor photos expire automatically after 30 days; only explicitly saved photos persist.

## Target Users And Roles

### Ring account owner / household administrator

The adult Ring account owner establishes the Knock Knock household, connects Ring, invites or removes members, creates and maintains familiar-person profiles, approves identity changes, and reviews the complete visitor history and audit trail.

### Household member

An invited person aged 13 or older who can receive visitor alerts, review visits, identify people for a visit, choose an existing profile, and propose a new or corrected identity. A member cannot invite or remove users, alter retention, delete security records, or directly modify the canonical familiar-person profile without administrator approval.

### Visitor

A person appearing in Ring media. Visitors are not app users. The app may associate a visitor with a familiar profile only after household verification and must not infer sensitive traits, emotions, criminality, or demographics.

## Core User Journey

### First run

1. The Ring account owner opens Knock Knock and sees a concise explanation of visitor recognition, the 30-day learning period, shared household access, and fixed data-retention rules.
2. The owner confirms that household app users must be at least 13 years old.
3. The owner connects a Ring account or enters demo mode using the Ring simulator and supplied sample events.
4. The app explains that initial alerts will remain generic until the learning period ends.
5. The owner lands on an empty visitor timeline with a visible action to run a demo event or wait for Ring activity.

### Visit review during the learning period

1. Ring motion or a doorbell press creates a visit.
2. The app analyzes the freeze frame and associated usable clip frames.
3. A notification says “Visitor detected” and includes the number of people detected, but no names.
4. Opening the notification displays the visit time, Ring source, primary image, processing state, and one review card per detected person.
5. For each person, the user selects an existing profile, proposes a new profile, marks the person unknown, or records that no usable face was detected.
6. A proposed new or corrected profile is routed to the administrator for approval.
7. The completed visit appears in the shared timeline, and its confirmations become learning feedback.

### Visit review after the learning period

1. High-confidence matches may produce an alert such as “Possible match: Sarah,” together with the detected-person count.
2. Low-confidence matches, unknown people, multiple ambiguous matches, and face-undetected events remain generic.
3. Opening the alert always provides the same person-by-person confirmation workflow.
4. Confirmations and corrections update future matching behavior and create attributable audit entries.

### History review

1. A household user opens the shared visitor timeline.
2. The user can filter by date, confirmed profile, unknown visitor, delivery/service label, face-undetected status, verification status, and saved-photo status.
3. Opening a visit shows all detected people, the decisions made for each person, the responsible household user, and the relevant profile-modification history.
4. Visitor logs remain available for one year. Unsaved photos disappear after 30 days, leaving the text event record and audit history intact.

## Epics And User Stories

### Epic 1: Household onboarding and access

- As the Ring account owner, I want to create one Knock Knock household so that Ring events and visitor records have a clear administrative owner.
- As the owner, I want to invite or remove household members aged 13 or older so that trusted people can review shared visits.
- As a household member, I want to see the same current visitor timeline so that the household has one consistent record.

Acceptance criteria:

- First launch clearly identifies the owner as the sole administrator.
- Before inviting a member, the interface states that app users must be at least 13 years old.
- Only the owner sees controls for inviting or removing members.
- Removing a member ends future access but does not erase that member’s historical audit entries.
- All active members see the same visit identities, labels, and verification states.
- The MVP supports one household per connected Ring owner and does not expose multi-site or business controls.

### Epic 2: Ring visit intake and person counting

- As a household user, I want Ring motion and doorbell activity converted into a visit so that I have one record to review.
- As a household user, I want the alert to report how many people were detected so that I understand the event before opening it.
- As a demo viewer, I want simulator and uploaded-frame events to behave like Ring events so that the workflow can be tested reliably.

Acceptance criteria:

- A Ring simulator motion or ding event creates exactly one visible visit record.
- Each visit displays the event time, Ring source or demo source, and processing status.
- When one or more people are detected, the alert includes the detected count.
- A visit with three detected people produces three linked review cards, not three unrelated visits.
- When no usable face is visible, the visit remains logged and displays “Face undetected.”
- Duplicate delivery of the same Ring event does not create duplicate visits in the visible timeline.
- If media cannot be fetched, the visit shows a recoverable error state rather than disappearing.

### Epic 3: Thirty-day learning period

- As a new household, I want the app to avoid named alerts while it learns so that early mistakes do not look authoritative.
- As the administrator, I want profiles built from multiple confirmed images so that later suggestions are grounded in repeated usage.

Acceptance criteria:

- The first 30 calendar days after household activation are visibly labeled as the learning period.
- During the learning period, push notifications never include a person’s name, even if the system finds a possible match.
- The app can gather multiple usable face images from freeze frames and clips associated with confirmed visits.
- A profile screen shows that its examples came from confirmed household actions, not silent automatic enrollment.
- The interface shows learning-period progress without promising that recognition will become perfect at day 30.
- The transition out of learning mode does not remove the requirement for confirmation.

### Epic 4: Person-by-person identification

- As a household user, I want to identify every detected person separately so that group visits are accurately represented.
- As a household user, I want to use an existing profile, propose a new profile, mark someone unknown, or record an undetected face so that every visit can be completed honestly.
- As the administrator, I want to approve profile additions and corrections so that shared familiar identities remain controlled.

Acceptance criteria:

- Every detected person has an independent review state within the visit.
- The app never forces the same identity onto multiple faces in a group.
- Existing profiles are searchable by name and recognizable profile image.
- Members may submit a proposed new identity or correction, but the shared profile changes only after administrator approval.
- Administrator decisions update the visit for every household member.
- A visit can be saved with unresolved people; unresolved cards remain visibly marked for later review.
- The app prevents an accidental duplicate profile by warning when a proposed name or face resembles an existing profile, while still allowing the administrator to continue.

### Epic 5: Cautious AI-assisted suggestions

- As a household user, I want high-confidence suggestions after the learning period so that routine visits require less manual work.
- As a household user, I want uncertain results kept generic so that the notification does not misidentify someone.
- As the household, we want the system to learn from every correction so that repeated use improves its suggestions.

Acceptance criteria:

- After the learning period, only a result meeting the product’s high-confidence policy can produce “Possible match: [name].”
- Suggestions always use qualifying language such as “Possible match,” never “Confirmed” before human review.
- Low-confidence, conflicting, unknown, and face-undetected outcomes generate generic alerts.
- The review screen displays the suggestion and its confidence category in plain language.
- Confirming, correcting, merging, or relabeling supplies learning feedback for future visits.
- A single correction fixes that visit immediately; repeated usage can modify future matching behavior.
- No recognition outcome triggers a lock, alarm, gate, or other physical access action.

### Epic 6: Alerts and review workflow

- As a household user, I want an actionable alert so that I can move directly from a Ring event to the relevant review.
- As a household user, I want alerts to remain useful without exposing unjustified identity claims.

Acceptance criteria:

- Tapping an alert opens the matching visit rather than the generic home screen.
- Learning-period alerts say “Visitor detected” and include the person count when available.
- Post-learning alerts use a possible name only for high-confidence matches; all others remain generic.
- A group alert states the total detected count even when only one person has a possible match.
- If processing is incomplete when the alert is opened, the screen displays progress and refreshes into the review state.
- If notifications are disabled, the visit still appears in the shared timeline with an explanation in settings.

### Epic 7: Shared visitor history and search

- As a household user, I want a chronological visit history so that I can understand who came to the door and when.
- As a household user, I want filters and search so that I can find a familiar person, unknown visit, delivery, or unresolved event.

Acceptance criteria:

- The timeline sorts newest visits first and clearly separates visits by date.
- Each timeline item shows time, detected-person count, current labels, verification state, and whether its photo is still available.
- Users can filter by profile, unknown, delivery/service category, face undetected, unresolved, verified, and saved media.
- Searching a familiar profile returns every retained visit linked to that profile.
- When a photo has expired, the event remains readable with a “Photo expired” placeholder.
- A new household with no events sees an explanation and a visible demo-event action rather than a blank screen.

### Epic 8: Retention and saved media

- As a household user, I want routine visitor photos removed automatically so that sensitive imagery is not kept indefinitely by default.
- As a household user, I want to explicitly save important visitor photos so that evidence or meaningful events remain available.
- As the household, we want a one-year visitor log so that security history remains useful after routine media expires.

Acceptance criteria:

- Unsaved photos are automatically deleted 30 days after the visit.
- The associated text event, labels, decisions, and audit entries remain available for one year.
- A visible “Save photo” action explains that saved media will persist beyond 30 days.
- Saved photos remain marked as saved and do not disappear at the 30-day boundary.
- Household users cannot change the 30-day photo policy or one-year log policy in the MVP.
- The MVP does not provide manual deletion of visitor logs or profile-modification audit entries.
- At one year, expired visitor logs leave the active timeline according to the fixed retention policy.

### Epic 9: Profile and modification audit trail

- As the administrator, I want a familiar-person profile assembled from approved examples so that I can review what the system uses.
- As a household user, I want profile changes recorded so that security-relevant identity history cannot be silently rewritten.

Acceptance criteria:

- A familiar profile displays its name, primary image, approved example count, creation date, and current status.
- Each modification entry records the action, affected visit/profile, acting household user, administrator decision when required, and time.
- Corrections are visible to every active household member after approval.
- Removing a household member does not remove their earlier modification history.
- Audit entries cannot be edited or manually deleted in the MVP.
- A profile with conflicting corrections is flagged for administrator review and is excluded from named alerts until resolved.

## Edge Cases

### No face or unusable media

- The event remains in history as “Face undetected.”
- The interface distinguishes no face, obscured face, media unavailable, and processing failure when the product knows the difference.
- The user may still add a visit-level label such as delivery without inventing a person identity.

### Multiple people

- Every detected person is reviewed separately and linked to the same visit.
- The alert count reflects all people detected, including unresolved people.
- A possible match for one person never labels the whole group.

### Wrong or conflicting identity

- A correction immediately changes that visit’s visible identity after the appropriate approval.
- The old and new values remain in the audit trail.
- Repeated disagreement places the profile into review and suppresses named alerts for that profile.

### Delayed or failed processing

- The visit appears promptly with a processing state.
- Retriable failures provide a retry action to the administrator.
- A final failure preserves the Ring event metadata and explains that identification was unavailable.

### Offline device or disabled alerts

- Events synchronize into the timeline when access returns.
- The app does not claim that an alert was delivered when the operating system blocked it.
- Review actions already completed on another device resolve to the shared current state while retaining both actions in the audit trail if they conflict.

### Retention boundaries

- A photo nearing expiration shows the expiration date and a save action.
- Saving before expiration preserves the photo.
- Expired unsaved photos cannot be restored from the app.
- Photo expiration does not erase the one-year text visit record or profile audit history.

## What We Are Building

- One private household with a Ring-owner administrator and invited members aged 13 or older.
- Ring simulator/API visit intake plus uploaded-frame demo fixtures.
- Person counting, face-undetected states, and person-by-person review.
- A 30-day generic-alert learning period using multiple confirmed clip images.
- High-confidence, clearly tentative familiar-person suggestions after learning.
- Shared alerts, profile approval, visitor history, filtering, and immutable modification logs.
- Fixed 30-day unsaved-photo and one-year visitor-log retention behavior.
- A safe, repeatable hackathon demonstration that works without a physical Ring device.

## What We Would Add With More Time

- Automatic door, lock, gate, and alarm integrations after a separate safety and authorization design.
- Business roles, employee/customer workflows, multi-site administration, and organization reporting.
- More granular household permissions and parental controls beyond the 13+ eligibility rule.
- User-controlled export and legally reviewed deletion workflows that preserve necessary security audit evidence.
- Configurable retention plans after privacy, abuse, and regulatory review.
- Additional local-only vision engines and richer on-device processing.
- A production Appstore certification, accessibility audit, localization, and long-duration household beta.

## Submission Proof Points

1. A Ring simulator event creates one visit and an Android alert.
2. The alert accurately reports a multi-person count.
3. The review screen presents separate identity decisions for each face.
4. One face is linked to an existing profile, one becomes a proposed new profile, and one remains unknown or face undetected.
5. The administrator approves a change, and the shared audit trail records who proposed and approved it.
6. A learned high-confidence match is shown as “Possible match,” while a low-confidence event remains generic.
7. The visitor timeline filters between familiar, unknown, delivery, and unresolved events.
8. A photo-expiration state demonstrates the 30-day rule while the one-year visit record remains.
9. The repository visibly contains working Ring integration and the demo shows the Ring simulator path.
10. The product feedback and friction log explain the Ring and AWS onboarding experience for judging.

The primary “wow moment” is a group visit moving from a Ring event to a count-aware alert, separate AI-assisted identity cards, administrator-approved learning, and an immediately searchable shared history—without allowing the model to overstate who anyone is.
