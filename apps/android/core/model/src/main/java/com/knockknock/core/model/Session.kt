package com.knockknock.core.model

enum class HouseholdRole {
    OWNER,
    MEMBER,
}

data class AppSession(
    val userId: String,
    val role: HouseholdRole,
    val accessToken: String? = null,
    val age13Affirmed: Boolean = true,
)

interface SessionProvider {
    fun currentSession(): AppSession
}

class DemoSessionProvider(
    private var session: AppSession = AppSession("demo-owner", HouseholdRole.OWNER),
) : SessionProvider {
    override fun currentSession(): AppSession = session

    fun switchTo(role: HouseholdRole) {
        session = when (role) {
            HouseholdRole.OWNER -> AppSession("demo-owner", role)
            HouseholdRole.MEMBER -> AppSession("demo-member", role)
        }
    }
}
