# Private runtime data

This directory is intentionally excluded from Git except for this notice.

- `faces/<profile-id>/` contains enrolled biometric reference images for the local engine.
- `visitors.jsonl` contains the private visit audit log.
- `simulator/door.jpg` is an optional local test frame.

Treat all three as sensitive personal data. Do not use real people without informed consent,
do not sync this directory to a public service, and define a retention/deletion policy before
using Knock Knock outside a controlled demo.

