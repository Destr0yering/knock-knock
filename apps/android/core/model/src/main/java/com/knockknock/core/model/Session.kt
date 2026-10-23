package com.knockknock.core.model

enum class HouseholdRole {
    OWNER,
    MEMBER,
}

data class AppSession(
    val userId: String,
    val role: HouseholdRole,
    val accessToken: String? = null,
    val age13Affirmed: Boolean = false,
    val demoSession: Boolean = false,
)

interface SessionProvider {
    fun currentSession(): AppSession
    fun affirmAgeRequirement()
}

class DemoSessionProvider(
    private var session: AppSession = AppSession("demo-owner", HouseholdRole.OWNER, demoSession = true),
) : SessionProvider {
    override fun currentSession(): AppSession = session

    override fun affirmAgeRequirement() {
        session = session.copy(age13Affirmed = true)
    }

    fun switchTo(role: HouseholdRole) {
        val userId = if (role == HouseholdRole.OWNER) "demo-owner" else "demo-member"
        session = AppSession(userId, role, age13Affirmed = session.age13Affirmed, demoSession = true)
    }
}
