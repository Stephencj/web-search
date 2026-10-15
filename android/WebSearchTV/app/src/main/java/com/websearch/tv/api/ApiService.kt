package com.websearch.tv.api

import retrofit2.http.*

interface ApiService {
    // MARK: - Auth

    @GET("api/auth/mode")
    suspend fun getAuthMode(): AuthMode

    @GET("api/auth/users")
    suspend fun getUsers(): UsersResponse

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    @POST("api/auth/logout")
    suspend fun logout(): MessageResponse

    @GET("api/auth/me")
    suspend fun getCurrentUser(): User

    // MARK: - Feed

    @GET("api/feed")
    suspend fun getFeed(
        @Query("platform") platform: String? = null,
        @Query("watched") watched: String? = null,
        @Query("mode") mode: String = "newest",
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 50
    ): FeedResponse

    @GET("api/feed/by-channel")
    suspend fun getFeedByChannel(): FeedByChannelResponse

    @GET("api/feed/stats")
    suspend fun getFeedStats(): FeedStats

    @PUT("api/feed/items/{id}/watched")
    suspend fun markWatched(
        @Path("id") id: Int,
        @Body request: WatchedRequest
    ): FeedItem

    @PUT("api/feed/items/{id}/unwatched")
    suspend fun markUnwatched(
        @Path("id") id: Int,
        @Body request: WatchedRequest
    ): FeedItem

    @PUT("api/feed/items/{id}/progress")
    suspend fun updateProgress(
        @Path("id") id: Int,
        @Body request: ProgressRequest
    ): FeedItem

    @POST("api/feed/sync")
    suspend fun syncFeed(): MessageResponse

    // MARK: - Channels

    @GET("api/channels")
    suspend fun getChannels(
        @Query("platform") platform: String? = null
    ): ChannelsResponse

    @GET("api/channels/search")
    suspend fun searchChannels(
        @Query("query") query: String,
        @Query("platform") platform: String? = null
    ): List<ChannelSearchResult>

    @POST("api/channels")
    suspend fun addChannel(@Body request: AddChannelRequest): Channel

    @DELETE("api/channels/{id}")
    suspend fun deleteChannel(@Path("id") id: Int)

    @POST("api/channels/{id}/sync")
    suspend fun syncChannel(@Path("id") id: Int): MessageResponse

    @POST("api/channels/import/urls")
    suspend fun importChannels(@Body request: ImportChannelsRequest): MessageResponse

    // MARK: - Discover

    @GET("api/discover/platforms")
    suspend fun getPlatforms(): List<Platform>

    @POST("api/discover/search")
    suspend fun searchDiscover(@Body request: DiscoverSearchRequest): DiscoverSearchResponse

    @POST("api/discover/quick-save")
    suspend fun quickSave(@Body request: QuickSaveRequest): SavedVideo

    // MARK: - Saved Videos

    @GET("api/saved-videos")
    suspend fun getSavedVideos(
        @Query("platform") platform: String? = null,
        @Query("watched") watched: String? = null
    ): List<SavedVideo>

    @POST("api/saved-videos/from-url")
    suspend fun saveVideoFromUrl(@Body request: SavedVideoRequest): SavedVideo

    @DELETE("api/saved-videos/{id}")
    suspend fun deleteSavedVideo(@Path("id") id: Int)

    @PUT("api/saved-videos/{id}/watched")
    suspend fun markSavedVideoWatched(
        @Path("id") id: Int,
        @Body request: WatchedRequest
    ): SavedVideo

    @PUT("api/saved-videos/{id}/progress")
    suspend fun updateSavedVideoProgress(
        @Path("id") id: Int,
        @Body request: ProgressRequest
    ): SavedVideo

    @GET("api/saved-videos/stats")
    suspend fun getSavedVideoStats(): SavedVideoStats

    // MARK: - Collections

    @GET("api/collections")
    suspend fun getCollections(): CollectionsResponse

    @GET("api/collections/{id}")
    suspend fun getCollection(@Path("id") id: Int): CollectionWithItems

    @POST("api/collections")
    suspend fun createCollection(@Body request: CreateCollectionRequest): Collection

    @DELETE("api/collections/{id}")
    suspend fun deleteCollection(@Path("id") id: Int)

    @POST("api/collections/{id}/items")
    suspend fun addItemToCollection(
        @Path("id") collectionId: Int,
        @Body request: AddCollectionItemRequest
    ): CollectionItem

    @DELETE("api/collections/{collectionId}/items/{itemId}")
    suspend fun removeItemFromCollection(
        @Path("collectionId") collectionId: Int,
        @Path("itemId") itemId: Int
    )

    @POST("api/collections/quick-add")
    suspend fun quickAddToFavorites(@Body request: QuickAddRequest): CollectionItem

    // MARK: - Stream

    @GET("api/stream/{platform}/{videoId}")
    suspend fun getStreamInfo(
        @Path("platform") platform: String,
        @Path("videoId") videoId: String,
        @Query("quality") quality: String = "best"
    ): StreamInfo
}
