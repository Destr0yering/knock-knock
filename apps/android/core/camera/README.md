# Camera input scaffold

Step 1 reserves this module for camera adapters and video-frame extraction.
Implementation follows in Step 3. Ring authorization and delivery require a
network connection; private profiles and records remain on the owner device.

Inputs to private storage must be decoded image frames or validated video-only
media. A downloaded MP4 can contain audio even without Android microphone
permission. Do not persist the original container, create audio tracks, or route
private frames through the legacy Python/cloud recognition service.

Planned test locations: `src/test/java/com/knockknock/core/camera/` and
`src/androidTest/java/com/knockknock/core/camera/`.
