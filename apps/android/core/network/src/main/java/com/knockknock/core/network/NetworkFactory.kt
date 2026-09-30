package com.knockknock.core.network

import com.google.gson.FieldNamingPolicy
import com.google.gson.GsonBuilder
import com.knockknock.core.model.SessionProvider
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object NetworkFactory {
    fun create(
        baseUrl: String,
        sessionProvider: SessionProvider,
        debug: Boolean,
    ): KnockKnockApi {
        val logging = HttpLoggingInterceptor().apply {
            level = if (debug) {
                HttpLoggingInterceptor.Level.BASIC
            } else {
                HttpLoggingInterceptor.Level.NONE
            }
            redactHeader("Authorization")
        }
        val sessionInterceptor = Interceptor { chain ->
            val session = sessionProvider.currentSession()
            val request = chain.request().newBuilder()
                .header("X-Demo-User", session.userId)
                .apply {
                    session.accessToken?.let { token ->
                        header("Authorization", "Bearer $token")
                    }
                }
                .build()
            chain.proceed(request)
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(sessionInterceptor)
            .addInterceptor(logging)
            .build()
        val gson = GsonBuilder()
            .setFieldNamingPolicy(FieldNamingPolicy.LOWER_CASE_WITH_UNDERSCORES)
            .create()
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create(gson))
            .build()
            .create(KnockKnockApi::class.java)
    }
}
