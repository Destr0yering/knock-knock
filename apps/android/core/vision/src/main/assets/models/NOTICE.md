# Bundled local AI models

Source: OpenCV Zoo, model directories `face_detection_yunet` and
`face_recognition_sface`. Per-model licenses are included beside the weights.
OpenCV runtime dependency: `org.opencv:opencv:4.13.0` (Apache-2.0).

| Model | SHA-256 | Bytes |
| --- | --- | --- |
| face_detection_yunet_2023mar.onnx | 8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4 | 232589 |
| face_recognition_sface_2021dec.onnx | 0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79 | 38696353 |

The APK bundles these files; no first-use model download is required. Runtime
checks enforce these immutable hashes. Neither engine trains on app visitor data.
SFace similarity is advisory, requires owner confirmation, and is not calibrated
for this doorbell or tablet. Evaluate false matches and model training-data
provenance before commercial release; bundling a license does not establish
rights in training datasets. Upstream tracking: https://github.com/opencv/opencv_zoo/issues/313

Original source directories:
- https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
- https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
