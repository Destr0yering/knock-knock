# Demo rehearsal and fallback runbook

Target duration: 2:50, with ten seconds of margin below Devpost's three-minute limit. Use only
synthetic or consented media and keep account identifiers, tokens, and presigned URLs off screen.

## Preflight

- Confirm the repository is clean and the tested commit is pushed.
- Run the backend and Android quality gates from the README.
- Open the Android app to the learning-period timeline and preload the three-person fixture.
- Disable unrelated notifications and enable Do Not Disturb while preserving the test alert path.
- Verify screen recording captures readable 1080p text and microphone audio.
- Prepare the owner/member role switch, approval queue, audit entry, expired-photo example, and
  post-learning `Possible match` example.
- Record the exact deployed endpoint and CloudFormation stack output only in private production
  notes; never place secrets or token-bearing URLs in the recording.

## Path A — live Ring and AWS

Trigger a Ring Playground event, receive the generic three-person alert, open its deep link, review
the three separate cards, submit as member, approve as owner, and show the audit event. Briefly show
the CloudWatch request identifiers and Rekognition result count without media or secret values.

Pass condition: one live event reaches the deployed queue and Android alert in time for the script.
If it fails once during rehearsal, switch to Path B instead of debugging during the recording.

## Path B — signed Ring replay and deployed AWS

Replay the sanitized official fixture with a locally supplied signing key against the deployed
webhook. Follow the same Android review and approval path. Label the event clearly as an official
payload replay; do not imply that a physical doorbell generated it.

Pass condition: the deployed API acknowledges the signed replay, creates one idempotent visit, and
delivers or exposes the visit even if FCM is delayed.

## Path C — deterministic local proof

Run `python scripts/run_local_demo.py`, load the offline Android fixture, inject the local generic
notification, and demonstrate review, owner approval, audit, filters, and retention states. Show the
passing SAM validation/build evidence separately and state honestly that cloud activation or Ring
credentials prevented the live path.

Pass condition: the complete product story is reproducible without network access or private data.

## Timed checkpoints

| Time | Proof |
|---|---|
| 0:00–0:35 | Hook, learning-period policy, generic three-person alert |
| 0:35–1:15 | Three independent person cards and member proposal |
| 1:15–1:40 | Owner approval and immutable attribution |
| 1:40–2:00 | Possible-match boundary and fixed retention UI |
| 2:00–2:25 | Ring/AWS modular architecture and passing tests |
| 2:25–2:50 | Responsible-use boundary and tagline |

After recording, verify playback, captions, audio, total duration, public/unlisted access, and that
no secret, real private visitor image, account ID, or notification token is visible.

