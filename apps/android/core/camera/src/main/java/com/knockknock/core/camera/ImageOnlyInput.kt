package com.knockknock.core.camera

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import java.io.ByteArrayInputStream

/** Decodes visual frames in memory; original media containers are never persisted. */
class ImageOnlyInput(private val context: Context) {
    fun read(uri: Uri): Bitmap {
        require(context.contentResolver.getType(uri) in setOf("image/jpeg", "image/png", "image/webp")) {
            "Choose a JPEG, PNG, or WebP image. Video and audio imports are disabled."
        }
        val bytes = context.contentResolver.openInputStream(uri)?.use { input ->
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            var count = input.read(buffer)
            while (count >= 0) {
                require(output.size() + count <= 16 * 1024 * 1024) { "Image must be below 16 MB." }
                output.write(buffer, 0, count)
                count = input.read(buffer)
            }
            output.toByteArray()
        } ?: error("Image could not be opened.")
        try {
            val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
            require(bounds.outWidth > 0 && bounds.outHeight > 0 &&
                bounds.outWidth.toLong() * bounds.outHeight <= 40_000_000) { "Invalid or oversized image." }
            var sample = 1
            while (maxOf(bounds.outWidth, bounds.outHeight) / sample > 1600) sample *= 2
            val decoded = BitmapFactory.decodeByteArray(bytes, 0, bytes.size,
                BitmapFactory.Options().apply { inSampleSize = sample; inPreferredConfig = Bitmap.Config.ARGB_8888 })
                ?: error("Image could not be decoded.")
            val orientation = runCatching {
                ExifInterface(ByteArrayInputStream(bytes)).getAttributeInt(
                    ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL)
            }.getOrDefault(ExifInterface.ORIENTATION_NORMAL)
            val transform = Matrix().apply {
                when (orientation) {
                    ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> setScale(-1f, 1f)
                    ExifInterface.ORIENTATION_ROTATE_180 -> setRotate(180f)
                    ExifInterface.ORIENTATION_FLIP_VERTICAL -> setScale(1f, -1f)
                    ExifInterface.ORIENTATION_TRANSPOSE -> { setRotate(90f); postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_ROTATE_90 -> setRotate(90f)
                    ExifInterface.ORIENTATION_TRANSVERSE -> { setRotate(270f); postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_ROTATE_270 -> setRotate(270f)
                }
            }
            val rotated = Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, transform, true)
            if (rotated !== decoded) decoded.recycle()
            val scale = minOf(1f, 1280f / maxOf(rotated.width, rotated.height))
            val result = Bitmap.createScaledBitmap(rotated,
                maxOf(1, (rotated.width * scale).toInt()), maxOf(1, (rotated.height * scale).toInt()), true)
            if (result !== rotated) rotated.recycle()
            return result
        } finally { bytes.fill(0) }
    }
}
