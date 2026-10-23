# Local vision scaffold

Step 1 reserves this module for interchangeable on-device detection and matching
engines. No cloud-recognition dependency is introduced here. Model selection and
licensing review precede implementation in Step 3.

Detection, person counts, identity suggestions, and owner confirmation are
separate operations. Preserve unknown and face-undetected states; never treat an
uncalibrated similarity score as a probability. Owner-approved reference updates
are not permission to train a model on visitor data.

Planned test locations: `src/test/java/com/knockknock/core/vision/` and
`src/androidTest/java/com/knockknock/core/vision/`.
