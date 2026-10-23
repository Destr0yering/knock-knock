# Knock Knock limited test terms

**Draft only. Not published, not a contract, and not ready for a live-data pilot until the public
privacy notice, identity/contact, deployed deletion flow and Ring consent wording are reviewed.**
Prepared October 21, 2026.

Knock Knock is an experimental Android visitor-journal prototype. It can contain errors and may be
unavailable. It is not a security alarm, emergency service, access-control system, or reliable
identification system. Face matching can be wrong. A person must review every suggestion and make
their own decisions.

## Test boundaries

- Use synthetic/demo events until the privacy notice is published and the deployed Ring, account,
  and deletion flows are verified.
- A live tester must own or administer the Ring account and camera, have authority to connect them,
  notify household members and visitors, and test with consenting adults only. Do not include
  children, neighbors, passersby, or anyone who has not been notified.
- Ring may request broader camera, video, device, or account access than Knock Knock's still-image
  workflow uses. Review Ring's authorization screen and decline if its scope is not acceptable.
- Optional push alerts are separate. They contain generic text and a visit ID, not names or images.
- A tester can request account deletion in the app by signing in and typing `DELETE`. The service
  stops processing and queues removal of active cloud records, media, tokens, isolated face
  references and the Cognito account; the app erases local data. AWS backups and operational
  records can remain under the retention periods in the privacy notice.
- Ring unlinking is separate: remove Knock Knock at Ring Appstore > My Apps > Knock Knock > Remove
  App. Local Android clearing alone does not revoke Ring access or remove cloud data.

## Tester responsibility and risks

Use the prototype only for evaluation and feedback. Secure the Android device and any exports. Do
not share private images or records without permission. Do not rely on the app to determine who is
at a door or to take action against a person. Contact the operator using the published privacy
contact to report unexpected collection, exposure, or incorrect behavior.

## Operator and contact

Responsible developer/business: **[public name required]**

Privacy/support contact: **[monitored email or contact URL required]**

Before publication, add an effective date and stable privacy-notice URL, then verify the deployed
behavior and obtain appropriate privacy review. Do not invite live-data testers with this draft.
