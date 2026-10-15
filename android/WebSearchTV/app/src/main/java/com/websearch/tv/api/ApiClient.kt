package com.websearch.tv.api

import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ApiClient @Inject constructor(
    private val authManager: com.websearch.tv.auth.AuthManager
) {
    private var baseUrl: String = "https://refinedaf.com"
    private var retrofit: Retrofit? = null
    private var apiService: ApiService? = null

    fun setBaseUrl(url: String) {
        baseUrl = url.trimEnd('/')
        retrofit = null
        apiService = null
    }

    fun getBaseUrl(): String = baseUrl

    private fun getRetrofit(): Retrofit {
        if (retrofit == null) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val authInterceptor = Interceptor { chain ->
                val request = chain.request().newBuilder()
                authManager.getTokenSync()?.let { token ->
                    request.addHeader("Authorization", "Bearer $token")
                }
                request.addHeader("Content-Type", "application/json")
                request.addHeader("Accept", "application/json")
                chain.proceed(request.build())
            }

            val client = OkHttpClient.Builder()
                .addInterceptor(authInterceptor)
                .addInterceptor(loggingInterceptor)
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(120, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build()

            retrofit = Retrofit.Builder()
                .baseUrl("$baseUrl/")
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
        }
        return retrofit!!
    }

    fun getApiService(): ApiService {
        if (apiService == null) {
            apiService = getRetrofit().create(ApiService::class.java)
        }
        return apiService!!
    }

    // Convenience methods that delegate to ApiService

    suspend fun getAuthMode() = getApiService().getAuthMode()
    suspend fun getUsers() = getApiService().getUsers().users
    suspend fun login(username: String, pin: String? = null): LoginResponse {
        val response = getApiService().login(LoginRequest(username, pin))
        authManager.saveToken(response.token)
        return response
    }
    suspend fun logout() {
        getApiService().logout()
        authManager.clearToken()
    }
    suspend fun getCurrentUser() = getApiService().getCurrentUser()

    suspend fun getFeed(
        platform: String? = null,
        watched: WatchFilter = WatchFilter.ALL,
        mode: FeedMode = FeedMode.NEWEST,
        page: Int = 1,
        perPage: Int = 50
    ) = getApiService().getFeed(
        platform = platform,
        watched = if (watched != WatchFilter.ALL) watched.value else null,
        mode = mode.value,
        page = page,
        perPage = perPage
    )

    suspend fun getFeedStats() = getApiService().getFeedStats()
    suspend fun syncFeed() = getApiService().syncFeed()
    suspend fun markWatched(itemId: Int) = getApiService().markWatched(itemId, WatchedRequest(true))
    suspend fun markUnwatched(itemId: Int) = getApiService().markUnwatched(itemId, WatchedRequest(false))
    suspend fun updateProgress(itemId: Int, seconds: Int) =
        getApiService().updateProgress(itemId, ProgressRequest(seconds))

    suspend fun getChannels(platform: String? = null) = getApiService().getChannels(platform).items
    suspend fun deleteChannel(id: Int) = getApiService().deleteChannel(id)
    suspend fun syncChannel(id: Int) = getApiService().syncChannel(id)
    suspend fun addChannel(url: String) = getApiService().addChannel(AddChannelRequest(url))

    suspend fun getPlatforms() = getApiService().getPlatforms()
    suspend fun searchVideos(query: String, platforms: List<String>? = null, maxResults: Int = 20) =
        getApiService().searchDiscover(DiscoverSearchRequest(query, "videos", platforms, maxResults))
    suspend fun searchChannels(query: String, platforms: List<String>? = null) =
        getApiService().searchDiscover(DiscoverSearchRequest(query, "channels", platforms, 20))
    suspend fun quickSave(url: String) = getApiService().quickSave(QuickSaveRequest(url))

    suspend fun getSavedVideos(platform: String? = null, watched: WatchFilter = WatchFilter.ALL) =
        getApiService().getSavedVideos(
            platform = platform,
            watched = if (watched != WatchFilter.ALL) watched.value else null
        )
    suspend fun saveVideoFromUrl(url: String) = getApiService().saveVideoFromUrl(SavedVideoRequest(url))
    suspend fun deleteSavedVideo(id: Int) = getApiService().deleteSavedVideo(id)
    suspend fun markSavedVideoWatched(id: Int, watched: Boolean) =
        getApiService().markSavedVideoWatched(id, WatchedRequest(watched))
    suspend fun updateSavedVideoProgress(id: Int, seconds: Int) =
        getApiService().updateSavedVideoProgress(id, ProgressRequest(seconds))

    suspend fun getCollections() = getApiService().getCollections().items
    suspend fun getCollection(id: Int) = getApiService().getCollection(id)
    suspend fun createCollection(name: String, description: String? = null) =
        getApiService().createCollection(CreateCollectionRequest(name, description))
    suspend fun deleteCollection(id: Int) = getApiService().deleteCollection(id)
    suspend fun addItemToCollection(collectionId: Int, item: AddCollectionItemRequest) =
        getApiService().addItemToCollection(collectionId, item)
    suspend fun removeItemFromCollection(collectionId: Int, itemId: Int) =
        getApiService().removeItemFromCollection(collectionId, itemId)

    suspend fun getStreamInfo(platform: String, videoId: String, quality: String = "best") =
        getApiService().getStreamInfo(platform, videoId, quality)

    suspend fun validateSession(): Boolean {
        return try {
            if (authManager.getTokenSync() == null) return false
            getCurrentUser()
            true
        } catch (e: Exception) {
            authManager.clearToken()
            false
        }
    }
}
