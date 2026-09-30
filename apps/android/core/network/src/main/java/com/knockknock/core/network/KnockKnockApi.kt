package com.knockknock.core.network

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface KnockKnockApi {
    @GET("v1/visits")
    suspend fun listVisits(
        @Query("state") state: String? = null,
        @Query("saved") saved: Boolean? = null,
        @Query("limit") limit: Int = 100,
        @Query("offset") offset: Int = 0,
    ): List<VisitDto>

    @POST("v1/demo/events")
    suspend fun createDemoEvent(
        @Body body: FixtureRequestDto = FixtureRequestDto(),
    ): VisitDto
}
