# Knock Knock privacy notice

**Publication state: NOT READY TO PUBLISH.** Prepared October 21, 2026. The deletion design is now
implemented in source, but the AWS stack and Android app still need the new version deployed and
verified. Developer identity, monitored contact, stable public URL, and privacy review are also
required before inviting live-data testers.

## Who operates Knock Knock

Developer or business name: **Got2Get2Work**

Privacy and support contact: **got2get2worksupport@gmail.com**

## Information processed

Knock Knock uses Amazon Cognito for account sign-in. If you connect a Ring account through Ring's
hosted Appstore flow, the service receives Ring account and device identifiers, event metadata,
and one still JPEG snapshot for each supported event. Knock Knock does not request or store Ring
video clips. Ring may display permissions broader than the still-image workflow; review those
permissions before authorizing.

AWS services in US East (N. Virginia) receive snapshots for face detection and advisory Rekognition
matching, store encrypted snapshots and visit history, and operate account linking. Each Ring
owner's face collection is isolated from other owners. A match is only a suggestion and does not
prove a person's identity. Firebase Cloud Messaging receives a device token and generic alert data
only after a separate opt-in; alert payloads do not include visitor names or images. The Android
app stores private journal records in an encrypted local database and vault.

The service also processes account identifiers, Ring OAuth tokens, owner consent time/version,
push-consent records, deletion-job status, and limited operational/security metadata. AWS
application logs are configured not to contain visitor images, names, tokens, or face vectors.

## Retention

Unsaved snapshots and face crops expire after 30 days. Visit records expire after 365 days. Saved
visitor media and an active face profile remain until removed or the account is deleted. Push
tokens remain while alerts are enabled. A deletion receipt hash remains for up to 30 days so you can
check a request after sign-out. Ring webhook deduplication data expires after seven days. Service
logs are configured for 14 days; failed deletion messages may remain in a restricted encrypted
queue for up to 14 days.

Amazon DynamoDB point-in-time recovery backups for household and visit data can retain deleted data
in recoverable backups for up to 35 days. These backup copies expire on that schedule and are not
used for normal app operation. A minimal deletion tombstone has a DynamoDB TTL expiration set five
minutes after the current sign-in token expires to prevent token reuse from restarting processing;
TTL cleanup can occur later.

## Your controls

You can disable push alerts in Knock Knock, remove local app data through Android settings, and
request account deletion in Knock Knock by signing in and typing `DELETE`. Once accepted, the service
blocks new Ring processing, removes active cloud visit data, snapshots, Ring tokens, push tokens,
owner-specific face references and the Cognito sign-in account, and erases local app data. A receipt
is saved on the device to check progress after sign-out. The service reports completion only after
primary data cleanup succeeds; the backup and operational retention periods above still apply.

Ring uses a one-way Appstore link. To revoke Ring's side of the connection, open Ring Appstore > My
Apps > Knock Knock > Remove App. Ring invalidates its tokens and stops sending webhooks after that
removal. Account deletion inside Knock Knock does not remove this Ring authorization for you.

## Sharing and purpose

Knock Knock uses the information above to link the owner's Ring account, process doorbell events,
show visit history, provide optional visitor-match suggestions, and send generic opted-in alerts.
Data is shared with Ring, Amazon Web Services, Amazon Cognito, Amazon Rekognition, and Firebase
Cloud Messaging as needed for these functions. The providers' own privacy terms apply to data they
process. The prototype does not intentionally sell visitor information.

## Visitors and children

Use only with a Ring account and camera you control, notify household members and visitors, and
obtain consent before processing a person's image. Do not capture minors, neighbors, passersby or
people who have not been notified. Face analysis can be wrong; do not use it for emergency response,
access control, or consequential decisions.

## Before publication

Confirm this mailbox is monitored, publish the notice at a stable URL, confirm the deployed settings
and retention, and have the notice reviewed for the pilot location. No live-data pilot should rely
on this draft until those steps are complete.
