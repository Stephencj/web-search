package com.websearch.tv.api

import com.google.gson.annotations.SerializedName

// MARK: - Auth Models

data class AuthMode(
    val mode: String,
    @SerializedName("allow_guest") val allowGuest: Boolean
)

data class UsersResponse(
    val users: List<User>,
    @SerializedName("auth_mode") val authMode: String
)

data class User(
    val id: Int,
    val username: String,
    @SerializedName("display_name") val displayName: String?,
    @SerializedName("avatar_color") val avatarColor: String,
    @SerializedName("is_admin") val isAdmin: Boolean?,
    @SerializedName("has_pin") val hasPin: Boolean?,
    @SerializedName("last_login_at") val lastLoginAt: String?
) {
    val initials: String
        get() {
            val name = displayName ?: username
            val parts = name.split(" ")
            return if (parts.size >= 2) {
                "${parts[0].take(1)}${parts[1].take(1)}".uppercase()
            } else {
                name.take(2).uppercase()
            }
        }
}

data class LoginRequest(
    val username: String,
    val pin: String?
)

data class LoginResponse(
    val token: String,
    val user: User,
    @SerializedName("expires_at") val expiresAt: String?
)

// MARK: - Channel Models

data class Channel(
    val id: Int,
    val platform: String,
    @SerializedName("platform_channel_id") val platformChannelId: String,
    @SerializedName("channel_url") val channelUrl: String,
    val name: String,
    val description: String?,
    @SerializedName("avatar_url") val avatarUrl: String?,
    @SerializedName("banner_url") val bannerUrl: String?,
    @SerializedName("subscriber_count") val subscriberCount: Int?,
    @SerializedName("video_count") val videoCount: Int?,
    @SerializedName("unwatched_count") val unwatchedCount: Int?,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("last_synced_at") val lastSyncedAt: String?,
    @SerializedName("last_sync_error") val lastSyncError: String?,
    @SerializedName("consecutive_errors") val consecutiveErrors: Int?,
    @SerializedName("import_source") val importSource: String?,
    @SerializedName("created_at") val createdAt: String?,
    @SerializedName("updated_at") val updatedAt: String?
)

data class ChannelsResponse(
    val items: List<Channel>,
    val total: Int
)

data class ChannelSearchResult(
    val platform: String,
    @SerializedName("channel_id") val channelId: String,
    @SerializedName("channel_url") val channelUrl: String,
    val name: String,
    val description: String?,
    @SerializedName("avatar_url") val avatarUrl: String?,
    @SerializedName("subscriber_count") val subscriberCount: Int?,
    @SerializedName("video_count") val videoCount: Int?
) {
    val id: String get() = "${platform}_${channelId}"
}

data class AddChannelRequest(val url: String)

data class ImportChannelsRequest(val urls: List<String>)

// MARK: - Feed Models

data class FeedItem(
    val id: Int,
    @SerializedName("channel_id") val channelId: Int?,
    val platform: String,
    @SerializedName("video_id") val videoId: String,
    @SerializedName("video_url") val videoUrl: String,
    val title: String,
    val description: String?,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    @SerializedName("duration_seconds") val durationSeconds: Int?,
    @SerializedName("view_count") val viewCount: Int?,
    @SerializedName("upload_date") val uploadDate: String?,
    val categories: List<String>?,
    @SerializedName("is_watched") val isWatched: Boolean,
    @SerializedName("watched_at") val watchedAt: String?,
    @SerializedName("watch_progress_seconds") val watchProgressSeconds: Int?,
    @SerializedName("discovered_at") val discoveredAt: String?,
    @SerializedName("channel_name") val channelName: String?
) {
    val formattedDuration: String
        get() {
            val seconds = durationSeconds ?: return ""
            val hours = seconds / 3600
            val minutes = (seconds % 3600) / 60
            val secs = seconds % 60
            return if (hours > 0) {
                String.format("%d:%02d:%02d", hours, minutes, secs)
            } else {
                String.format("%d:%02d", minutes, secs)
            }
        }

    val formattedViews: String
        get() {
            val views = viewCount ?: return ""
            return when {
                views >= 1_000_000 -> String.format("%.1fM views", views / 1_000_000.0)
                views >= 1_000 -> String.format("%.1fK views", views / 1_000.0)
                else -> "$views views"
            }
        }
}

data class FeedResponse(
    val items: List<FeedItem>,
    val total: Int,
    val page: Int,
    @SerializedName("per_page") val perPage: Int,
    @SerializedName("has_more") val hasMore: Boolean
)

data class FeedByChannelResponse(
    val channels: List<ChannelFeedGroup>
)

data class ChannelFeedGroup(
    val channel: Channel,
    val items: List<FeedItem>,
    @SerializedName("total_unwatched") val totalUnwatched: Int
) {
    val id: Int get() = channel.id
}

data class FeedStats(
    @SerializedName("total_videos") val totalVideos: Int,
    @SerializedName("watched_count") val watchedCount: Int,
    @SerializedName("unwatched_count") val unwatchedCount: Int,
    @SerializedName("by_platform") val byPlatform: Map<String, Int>?
)

// MARK: - Discover Models

data class Platform(
    @SerializedName("id") val platformId: String,
    val name: String,
    val icon: String?,
    val color: String?,
    @SerializedName("supports_search") val supportsSearch: Boolean,
    @SerializedName("supports_channel_feed") val supportsChannelFeed: Boolean,
    @SerializedName("supports_playlists") val supportsPlaylists: Boolean
) {
    val id: String get() = platformId
}

data class DiscoverSearchRequest(
    val query: String,
    @SerializedName("search_type") val searchType: String,
    val platforms: List<String>?,
    @SerializedName("max_results") val maxResults: Int?
)

data class DiscoverVideoResult(
    val platform: String,
    @SerializedName("video_id") val videoId: String,
    @SerializedName("video_url") val videoUrl: String,
    val title: String,
    val description: String?,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    @SerializedName("channel_name") val channelName: String?,
    @SerializedName("channel_id") val channelId: String?,
    @SerializedName("channel_url") val channelUrl: String?,
    @SerializedName("duration_seconds") val durationSeconds: Int?,
    @SerializedName("view_count") val viewCount: Int?,
    @SerializedName("like_count") val likeCount: Int?,
    @SerializedName("upload_date") val uploadDate: String?,
    val tags: List<String>?
) {
    val id: String get() = "${platform}_${videoId}"

    val formattedDuration: String
        get() {
            val seconds = durationSeconds ?: return ""
            val hours = seconds / 3600
            val minutes = (seconds % 3600) / 60
            val secs = seconds % 60
            return if (hours > 0) {
                String.format("%d:%02d:%02d", hours, minutes, secs)
            } else {
                String.format("%d:%02d", minutes, secs)
            }
        }

    fun toFeedItem(): FeedItem = FeedItem(
        id = 0,
        channelId = null,
        platform = platform,
        videoId = videoId,
        videoUrl = videoUrl,
        title = title,
        description = description,
        thumbnailUrl = thumbnailUrl,
        durationSeconds = durationSeconds,
        viewCount = viewCount,
        uploadDate = uploadDate,
        categories = null,
        isWatched = false,
        watchedAt = null,
        watchProgressSeconds = null,
        discoveredAt = null,
        channelName = channelName
    )
}

data class DiscoverSearchResponse(
    val videos: List<DiscoverVideoResult>?,
    val channels: List<ChannelSearchResult>?,
    @SerializedName("total_results") val totalResults: Int?,
    @SerializedName("timing_ms") val timingMs: Double?
)

data class QuickSaveRequest(val url: String)

// MARK: - Saved Videos Models

data class SavedVideo(
    val id: Int,
    val platform: String,
    @SerializedName("video_id") val videoId: String,
    @SerializedName("video_url") val videoUrl: String,
    val title: String,
    val description: String?,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    @SerializedName("duration_seconds") val durationSeconds: Int?,
    @SerializedName("view_count") val viewCount: Int?,
    @SerializedName("upload_date") val uploadDate: String?,
    @SerializedName("channel_name") val channelName: String?,
    @SerializedName("channel_id") val channelId: String?,
    @SerializedName("channel_url") val channelUrl: String?,
    @SerializedName("is_watched") val isWatched: Boolean,
    @SerializedName("watched_at") val watchedAt: String?,
    @SerializedName("watch_progress_seconds") val watchProgressSeconds: Int?,
    val notes: String?,
    @SerializedName("saved_at") val savedAt: String?,
    @SerializedName("updated_at") val updatedAt: String?
) {
    val formattedDuration: String
        get() {
            val seconds = durationSeconds ?: return ""
            val hours = seconds / 3600
            val minutes = (seconds % 3600) / 60
            val secs = seconds % 60
            return if (hours > 0) {
                String.format("%d:%02d:%02d", hours, minutes, secs)
            } else {
                String.format("%d:%02d", minutes, secs)
            }
        }

    fun toFeedItem(): FeedItem = FeedItem(
        id = id,
        channelId = null,
        platform = platform,
        videoId = videoId,
        videoUrl = videoUrl,
        title = title,
        description = description,
        thumbnailUrl = thumbnailUrl,
        durationSeconds = durationSeconds,
        viewCount = viewCount,
        uploadDate = uploadDate,
        categories = null,
        isWatched = isWatched,
        watchedAt = watchedAt,
        watchProgressSeconds = watchProgressSeconds,
        discoveredAt = null,
        channelName = channelName
    )
}

data class SavedVideoRequest(val url: String)

data class SavedVideoStats(
    val total: Int,
    val watched: Int,
    val unwatched: Int,
    @SerializedName("by_platform") val byPlatform: Map<String, Int>?
)

// MARK: - Collection Models

data class Collection(
    val id: Int,
    val name: String,
    val slug: String,
    val description: String?,
    @SerializedName("cover_url") val coverUrl: String?,
    @SerializedName("sort_order") val sortOrder: Int,
    @SerializedName("item_count") val itemCount: Int,
    @SerializedName("created_at") val createdAt: String?,
    @SerializedName("updated_at") val updatedAt: String?
)

data class CollectionsResponse(
    val items: List<Collection>,
    val total: Int
)

data class CollectionWithItems(
    val id: Int,
    val name: String,
    val slug: String,
    val description: String?,
    @SerializedName("cover_url") val coverUrl: String?,
    @SerializedName("sort_order") val sortOrder: Int,
    @SerializedName("item_count") val itemCount: Int,
    val items: List<CollectionItem>,
    @SerializedName("created_at") val createdAt: String?,
    @SerializedName("updated_at") val updatedAt: String?
)

data class CollectionItem(
    val id: Int,
    @SerializedName("collection_id") val collectionId: Int?,
    @SerializedName("item_type") val itemType: String,
    val url: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String?,
    val title: String?,
    @SerializedName("source_url") val sourceUrl: String?,
    val domain: String?,
    @SerializedName("embed_type") val embedType: String?,
    @SerializedName("video_id") val videoId: String?,
    @SerializedName("sort_order") val sortOrder: Int?,
    @SerializedName("added_at") val addedAt: String?
) {
    fun toFeedItem(): FeedItem? {
        if (itemType != "video") return null
        val resolvedPlatform = embedType ?: VideoURLParser.extractPlatform(url)
        val resolvedVideoId = videoId?.takeIf { it.isNotEmpty() }
            ?: VideoURLParser.extractVideoId(url, resolvedPlatform)
            ?: return null

        return FeedItem(
            id = id,
            channelId = null,
            platform = resolvedPlatform,
            videoId = resolvedVideoId,
            videoUrl = url,
            title = title ?: "Untitled",
            description = null,
            thumbnailUrl = thumbnailUrl,
            durationSeconds = null,
            viewCount = null,
            uploadDate = null,
            categories = null,
            isWatched = false,
            watchedAt = null,
            watchProgressSeconds = null,
            discoveredAt = null,
            channelName = null
        )
    }
}

data class CreateCollectionRequest(
    val name: String,
    val description: String? = null
)

data class AddCollectionItemRequest(
    @SerializedName("item_type") val itemType: String,
    val url: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String? = null,
    val title: String? = null,
    @SerializedName("source_url") val sourceUrl: String? = null,
    @SerializedName("video_id") val videoId: String? = null
)

data class QuickAddRequest(
    @SerializedName("item_type") val itemType: String,
    val url: String,
    @SerializedName("thumbnail_url") val thumbnailUrl: String? = null,
    val title: String? = null,
    @SerializedName("source_url") val sourceUrl: String? = null
)

// MARK: - Watch State Updates

data class WatchedRequest(
    @SerializedName("is_watched") val isWatched: Boolean
)

data class ProgressRequest(
    @SerializedName("watch_progress_seconds") val watchProgressSeconds: Int
)

// MARK: - Stream Info

data class StreamInfo(
    @SerializedName("stream_url") val streamUrl: String?,
    @SerializedName("audio_url") val audioUrl: String?,
    val quality: String?,
    @SerializedName("format_type") val formatType: String?,
    val duration: Int?,
    val title: String?,
    val error: String?
)

// MARK: - API Response Helpers

data class MessageResponse(val message: String)

data class APIError(
    val detail: String?,
    val message: String?
) {
    val errorDescription: String
        get() = detail ?: message ?: "Unknown error"
}

// MARK: - Feed Modes

enum class FeedMode(val value: String, val displayName: String, val icon: String) {
    NEWEST("newest", "Newest", "arrow_downward"),
    OLDEST("oldest", "Oldest", "arrow_upward"),
    CATCH_UP("catch_up", "Catch Up", "history"),
    QUICK_WATCH("quick_watch", "Quick Watch", "bolt"),
    DEEP_DIVE("deep_dive", "Deep Dive", "menu_book"),
    RANDOM("random", "Random", "shuffle");

    companion object {
        fun fromValue(value: String): FeedMode =
            entries.find { it.value == value } ?: NEWEST
    }
}

enum class WatchFilter(val value: String, val displayName: String) {
    ALL("all", "All"),
    UNWATCHED("unwatched", "Unwatched"),
    WATCHED("watched", "Watched");

    companion object {
        fun fromValue(value: String): WatchFilter =
            entries.find { it.value == value } ?: ALL
    }
}

// MARK: - Video URL Parser

object VideoURLParser {
    fun extractVideoId(url: String, platform: String? = null): String? {
        val detectedPlatform = platform ?: extractPlatform(url)
        return when (detectedPlatform.lowercase()) {
            "youtube" -> extractYouTubeVideoId(url)
            "rumble" -> extractRumbleVideoId(url)
            "odysee" -> extractOdyseeVideoId(url)
            else -> null
        }
    }

    fun extractPlatform(url: String): String {
        val lowercased = url.lowercase()
        return when {
            "youtube.com" in lowercased || "youtu.be" in lowercased -> "youtube"
            "rumble.com" in lowercased -> "rumble"
            "odysee.com" in lowercased -> "odysee"
            else -> "unknown"
        }
    }

    private fun extractYouTubeVideoId(url: String): String? {
        // Try query parameter first (watch?v=...)
        val regex = Regex("[?&]v=([^&]+)")
        regex.find(url)?.groupValues?.get(1)?.let { return it }

        // Try youtu.be/ID
        if ("youtu.be" in url) {
            val parts = url.split("/")
            return parts.lastOrNull()?.split("?")?.firstOrNull()
        }

        // Try /embed/ID or /v/ID
        val embedRegex = Regex("/(?:embed|v)/([^/?]+)")
        embedRegex.find(url)?.groupValues?.get(1)?.let { return it }

        return null
    }

    private fun extractRumbleVideoId(url: String): String? {
        // Check for embed path
        val embedRegex = Regex("/embed/([^/?]+)")
        embedRegex.find(url)?.groupValues?.get(1)?.let { return it }

        // Standard rumble video URL: /vXXXXXX-title.html
        val videoRegex = Regex("/(v[^-/]+)")
        videoRegex.find(url)?.groupValues?.get(1)?.let { return it }

        return null
    }

    private fun extractOdyseeVideoId(url: String): String? {
        // Check for embed path: $/embed/claim-name/claim-id
        val embedRegex = Regex("/embed/([^/]+)/([^/?]+)")
        embedRegex.find(url)?.let { match ->
            return "${match.groupValues[1]}/${match.groupValues[2]}"
        }

        // Standard URL format: @channel/video-title
        val parts = url.split("/").filter { it.isNotEmpty() && !it.startsWith("$") }
        if (parts.size >= 2) {
            val channelIndex = parts.indexOfFirst { it.startsWith("@") }
            if (channelIndex >= 0 && channelIndex + 1 < parts.size) {
                return parts[channelIndex + 1]
            }
        }

        return null
    }
}
