package com.knockknock.app

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.knockknock.core.model.VisitDeepLink
import com.knockknock.core.model.VisitorAlert

interface VisitorNotificationGateway {
    fun showVisitAlert(visitId: String, alert: VisitorAlert): Boolean
}

class LocalVisitorNotificationGateway(private val context: Context) : VisitorNotificationGateway {
    override fun showVisitAlert(visitId: String, alert: VisitorAlert): Boolean {
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Visitor alerts", NotificationManager.IMPORTANCE_HIGH),
        )
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return false
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(VisitDeepLink.create(visitId)), context, MainActivity::class.java)
        val pending = PendingIntent.getActivity(
            context,
            visitId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(alert.title)
            .setContentText(alert.body)
            .setContentIntent(pending)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        NotificationManagerCompat.from(context).notify(visitId.hashCode(), notification)
        return true
    }

    private companion object { const val CHANNEL_ID = "visitor-alerts" }
}

// The future FCM service implements this boundary after validating the server-created payload.
interface FcmVisitMessageHandler {
    fun onVisitMessage(visitId: String, title: String, body: String)
}
