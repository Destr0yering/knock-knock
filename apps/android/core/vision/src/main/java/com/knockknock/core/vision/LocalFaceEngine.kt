package com.knockknock.core.vision

import android.content.Context
import android.graphics.Bitmap
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest
import org.opencv.android.OpenCVLoader
import org.opencv.android.Utils
import org.opencv.core.Mat
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc
import org.opencv.objdetect.FaceDetectorYN
import org.opencv.objdetect.FaceRecognizerSF

data class FaceBounds(val left: Int, val top: Int, val right: Int, val bottom: Int)
data class DetectedFace(val bounds: FaceBounds, val embedding: FloatArray, val jpeg: ByteArray, val confidence: Float)
interface LocalFaceEngine { fun analyze(bitmap: Bitmap): List<DetectedFace> }

/** Both models are bundled: no network calls and no visitor-data training. */
class OpenCvLocalFaceEngine(private val context: Context) : LocalFaceEngine {
    private val runtimeInitialized by lazy {
        check(OpenCVLoader.initLocal()) { "Local AI runtime could not initialize." }
    }
    private val detector by lazy {
        runtimeInitialized
        FaceDetectorYN.create(model("face_detection_yunet_2023mar.onnx",
            "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"), "", Size(320.0, 320.0), 0.9f)
    }
    private val recognizer by lazy {
        FaceRecognizerSF.create(model("face_recognition_sface_2021dec.onnx",
            "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79"), "")
    }

    @Synchronized
    override fun analyze(bitmap: Bitmap): List<DetectedFace> {
        runtimeInitialized
        val rgba = Mat(); val bgr = Mat(); val faces = Mat()
        try {
            Utils.bitmapToMat(bitmap, rgba)
            Imgproc.cvtColor(rgba, bgr, Imgproc.COLOR_RGBA2BGR)
            detector.setInputSize(bgr.size())
            detector.detect(bgr, faces)
            return (0 until faces.rows()).mapNotNull { index ->
                val values = FloatArray(15); faces.get(index, 0, values)
                val left = values[0].toInt().coerceIn(0, bitmap.width - 1)
                val top = values[1].toInt().coerceIn(0, bitmap.height - 1)
                val right = (values[0] + values[2]).toInt().coerceIn(left + 1, bitmap.width)
                val bottom = (values[1] + values[3]).toInt().coerceIn(top + 1, bitmap.height)
                if (right - left < 32 || bottom - top < 32) return@mapNotNull null
                val row = faces.row(index); val aligned = Mat(); val feature = Mat()
                try {
                    recognizer.alignCrop(bgr, row, aligned)
                    recognizer.feature(aligned, feature)
                    val embedding = FloatArray(feature.total().toInt()); feature.get(0, 0, embedding)
                    val crop = Bitmap.createBitmap(bitmap, left, top, right - left, bottom - top)
                    val jpeg = ByteArrayOutputStream().use { output ->
                        crop.compress(Bitmap.CompressFormat.JPEG, 90, output); output.toByteArray()
                    }
                    if (crop !== bitmap) crop.recycle()
                    DetectedFace(FaceBounds(left, top, right, bottom), embedding, jpeg, values[14])
                } finally { row.release(); aligned.release(); feature.release() }
            }
        } finally { rgba.release(); bgr.release(); faces.release() }
    }

    private fun model(name: String, expected: String): String {
        val dir = File(context.noBackupFilesDir, "public-models").apply { mkdirs() }
        val file = File(dir, name)
        if (!file.exists()) context.assets.open("models/$name").use { input -> file.outputStream().use { input.copyTo(it) } }
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(8192); var count = input.read(buffer)
            while (count >= 0) { digest.update(buffer, 0, count); count = input.read(buffer) }
        }
        check(digest.digest().joinToString("") { "%02x".format(it) } == expected) { "Local AI model integrity check failed." }
        return file.absolutePath
    }
}
