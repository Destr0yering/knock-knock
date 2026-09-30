package com.knockknock.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.knockknock.core.model.ConfidenceBand
import com.knockknock.core.model.VisitDeepLink
import com.knockknock.core.model.VisitorTrustPolicy
import com.knockknock.core.ui.KnockKnockTheme
import com.knockknock.feature.review.ApprovalRoute
import com.knockknock.feature.review.ApprovalViewModel
import com.knockknock.feature.review.ReviewViewModel
import com.knockknock.feature.review.VisitReviewRoute
import com.knockknock.feature.timeline.TimelineRoute
import com.knockknock.feature.timeline.TimelineViewModel

class MainActivity : ComponentActivity() {
    private lateinit var notifications: VisitorNotificationGateway

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        notifications = LocalVisitorNotificationGateway(this)
        val container = (application as KnockKnockApplication).container
        val initialVisitId = VisitDeepLink.parse(intent?.dataString)
        setContent {
            KnockKnockTheme {
                KnockKnockNavHost(
                    container = container,
                    initialVisitId = initialVisitId,
                    onTestAlert = ::postTestAlert,
                )
            }
        }
    }

    private fun postTestAlert() {
        if (Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 41)
            return
        }
        notifications.showVisitAlert(
            visitId = "offline-demo-group-arrival",
            alert = VisitorTrustPolicy.alert(
                peopleCount = 3,
                learningDay = 1,
                candidateName = "Morgan",
                confidenceBand = ConfidenceBand.HIGH,
            ),
        )
    }
}

@Composable
private fun KnockKnockNavHost(
    container: AppContainer,
    initialVisitId: String?,
    onTestAlert: () -> Unit,
) {
    val navController = rememberNavController()
    val start = initialVisitId?.let { "visit/$it" } ?: "timeline"
    NavHost(navController = navController, startDestination = start) {
        composable("timeline") {
            val timelineViewModel: TimelineViewModel = viewModel(
                factory = container.timelineViewModelFactory,
            )
            TimelineRoute(
                viewModel = timelineViewModel,
                onVisitClick = { visitId -> navController.navigate("visit/$visitId") },
                onTestAlert = onTestAlert,
            )
        }
        composable(
            route = "visit/{visitId}",
            arguments = listOf(navArgument("visitId") { type = NavType.StringType }),
        ) { entry ->
            val visitId = entry.arguments?.getString("visitId").orEmpty()
            val reviewViewModel: ReviewViewModel = viewModel(
                key = "review-$visitId",
                factory = container.reviewViewModelFactory(visitId),
            )
            VisitReviewRoute(
                viewModel = reviewViewModel,
                onBack = {
                    if (!navController.popBackStack()) navController.navigate("timeline")
                },
                onOpenApprovals = { navController.navigate("approvals") },
            )
        }
        composable("approvals") {
            val approvalViewModel: ApprovalViewModel = viewModel(
                factory = container.approvalViewModelFactory,
            )
            ApprovalRoute(approvalViewModel, onBack = navController::popBackStack)
        }
    }
}
