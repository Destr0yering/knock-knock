# Private records

`createPrivateDatabase(context)` uses SQLCipher 4.19.1 and Room schema v3 in
`knock-knock-private.db`. The old synthetic-demo database file is not converted
or overwritten. Its existing Room builder needs migrations 1→2 and 2→3.

`PrivateRecordsRepository(db, EncryptedFileVault(context), OwnerUnlock(context))`
provides visit/profile/audit flows and owner-gated import, confirmation,
correction, deletion, retention, media reads and export. The caller must show
flows only inside the unlocked UI; a Room flow is not an authentication boundary.

Confirmation enrolls one private reference from the reviewed person's image.
Reassigning the person removes that person's prior reference from the wrong
profile. Label corrections and explicit unknown actions are audited. Profile
deletion erases its references, unlinks identities from visits, removes profile
audit identifiers, and leaves a non-identifying deletion receipt. Database/media
deletion removes logical files; it does not promise physical flash sanitization.

Default unsaved image retention is 30 days and visit retention is 365 days.
Owner settings are encrypted in the vault. Saved images bypass the image
window but remain attached to their visit and are removed when that visit is
deleted or expires; enrolled profile references persist until removed by the
owner. Cleanup currently runs when the private app is opened, not at an exact
wall-clock expiry while the tablet is off. File deletion and database updates
are retryable but are not a single cross-filesystem transaction; a process crash
can leave an orphaned encrypted image pending further garbage collection.

Imported JPEGs are already sanitized by the image input/vision pipeline. This
repository accepts no video container or audio API. It records import time;
the original source capture time is unknown. Record export verifies retained
image hashes, includes source, export time, owner-labeled direction and audit
history, and makes no claim of source authenticity or legal admissibility.

Upstream integration:
https://github.com/sqlcipher/sqlcipher-android
https://developer.android.com/privacy-and-security/keystore

SQLCipher's current AAR requires compileSdk 36; targetSdk/minSdk do not need to
change. Instrumentation tests cover encrypted reopen, schema migration, owner
correction, deletion and default image retention. They need a real emulator or
tablet; JVM cryptographic tests do not validate Android Keystore or SQLCipher.
