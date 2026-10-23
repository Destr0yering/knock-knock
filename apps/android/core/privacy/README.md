# Protected device storage

`EncryptedFileVault(context)` exposes `put(id, bytes)`, `get(id)`, `exists(id)`,
and `delete(id)`. AES-256-GCM encrypts bytes before any disk write. Each record
uses a fresh nonce; its logical identifier and format version are authenticated
as associated data, so swapping encrypted files does not change their identity.
AtomicFile writes only ciphertext, including its temporary and backup files.
The vault lives in app-private `noBackupFilesDir`.

Android Keystore holds the non-exportable AES key. `DatabasePassphrase` creates
a random SQLCipher passphrase and persists only its wrapped ciphertext in the
vault. Losing the Keystore key makes stored records unrecoverable; there is no
cloud key recovery or automatic fallback to plaintext storage.

`OwnerUnlock(context)` supplies a system device-credential confirmation intent.
The UI must call `confirmUnlock()` only following `RESULT_OK`, and must hide
private content and close its database when leaving the private screen or when
the app backgrounds. The gate expires after five minutes. This is an application
access gate, not a Keystore key requiring authentication for every decryption;
the running app necessarily holds decrypted records in memory. Anyone with the
device credential can unlock it; it does not independently prove Ring ownership.

JVM tests verify nonce freshness, ciphertext tamper rejection, and identifier
binding. Instrumentation tests exercise real Android Keystore and reopening.
Run on an emulator or connected test device before using private data.
