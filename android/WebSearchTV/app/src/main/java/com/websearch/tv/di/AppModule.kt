package com.websearch.tv.di

import android.content.Context
import com.websearch.tv.api.ApiClient
import com.websearch.tv.auth.AuthManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideAuthManager(@ApplicationContext context: Context): AuthManager {
        return AuthManager(context)
    }

    @Provides
    @Singleton
    fun provideApiClient(authManager: AuthManager): ApiClient {
        return ApiClient(authManager)
    }
}
