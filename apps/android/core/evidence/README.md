# Record export scaffold

Step 1 reserves this module for owner-requested exports with source provenance,
capture/receipt/export timestamps, modification history, and a SHA-256 file
manifest. Implementation follows the protected data model and backend core.

Describe exports as records. Hashes show whether bytes changed relative to the
manifest; they do not establish authenticity, a trusted capture time, a legal
chain of custody, or legal admissibility. If source Ring media contains audio,
export only the derived silent frames/video and record that transformation.

Planned test locations: `src/test/java/com/knockknock/core/evidence/` and
`src/androidTest/java/com/knockknock/core/evidence/`.
