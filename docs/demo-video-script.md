# Knock Knock demo video script

Target runtime: **2:40–2:55**. Public English YouTube or Vimeo video. Use synthetic/consented media only and no copyrighted music.

## 0:00–0:15 — Hook

**Visual:** Ring-style event followed immediately by the Android alert and timeline.

**Voiceover:** “A normal doorbell alert tells you something happened. Knock Knock helps a household understand who arrived together—without pretending that AI is the authority.”

## 0:15–0:35 — Product promise

**Visual:** Learning-period banner and `Visitor detected / 3 people detected` notification.

**Voiceover:** “For the first 30 days, alerts stay generic while the household verifies visitors and builds approved examples. Every group arrival is counted, and every person gets an independent review.”

## 0:35–1:15 — Primary wow moment

**Visual:** Open the notification. Show three cards: suggested familiar person, unresolved person, and face-undetected person. Label the unresolved person and submit a proposal.

**Voiceover:** “This Ring event contains three people. Knock Knock detects and crops faces separately, so a group frame is never treated as one match. One person has an advisory suggestion, one needs a label, and one remains explicitly face undetected. A household member can propose an identity but cannot change the canonical profile.”

## 1:15–1:40 — Owner approval and audit

**Visual:** Switch to Ring owner, approve the proposal, open immutable modification history.

**Voiceover:** “Only the Ring account owner can approve profile changes. Approval updates shared state, adds the verified frames to learning, and leaves an attributable history showing who proposed and who decided.”

## 1:40–2:00 — Trust and retention

**Visual:** Post-learning `Possible match` example, low-confidence generic example, then expired-photo placeholder.

**Voiceover:** “After learning, only high-confidence, conflict-free evidence can say ‘Possible match.’ Low confidence stays generic. Unsaved photos expire after 30 days, while the security log remains available for one year.”

## 2:00–2:25 — Technical proof

**Visual:** Architecture graphic or terminal montage: Ring replay, passing tests, SAM template, worker image.

**Voiceover:** “The official Ring boundary verifies signed events and queues work quickly. AWS Lambda, SQS, Rekognition, encrypted S3, DynamoDB, Cognito, CloudWatch, and FCM form a modular serverless path. A deterministic simulator keeps the full workflow testable without private media.”

## 2:25–2:45 — Responsible boundary and close

**Visual:** Android timeline and Knock Knock wordmark/tagline.

**Voiceover:** “Knock Knock never infers intent and never unlocks a door. It provides context; the household makes the decision. Knock Knock—know who’s at the door before the knock knock.”

## Recording checklist

- Capture at 1080p with Android text large enough to read.
- Blur account identifiers, tokens, URLs with query strings, and notification device tokens.
- Keep the actual edit under 3:00; target 2:50.
- Show the working Ring simulator or official sanitized replay clearly.
- Show AWS live evidence only after activation; otherwise label local SAM proof honestly.
- Use captions and avoid rapid cursor movement.
