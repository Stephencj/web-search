import Foundation

// MARK: - Auth Models

struct AuthMode: Codable {
    let mode: String  // "open" or "protected"
    let allowGuest: Bool

    enum CodingKeys: String, CodingKey {
        case mode
        case allowGuest = "allow_guest"
    }
}

struct UsersResponse: Codable {
    let users: [User]
    let authMode: String

    enum CodingKeys: String, CodingKey {
        case users
        case authMode = "auth_mode"
    }
}

struct User: Codable, Identifiable {
    let id: Int
    let username: String
    let displayName: String?
    let avatarColor: String
    let isAdmin: Bool?
    let hasPin: Bool?
    let lastLoginAt: String?

    enum CodingKeys: String, CodingKey {
        case id, username
        case displayName = "display_name"
        case avatarColor = "avatar_color"
        case isAdmin = "is_admin"
        case hasPin = "has_pin"
        case lastLoginAt = "last_login_at"
    }

    var initials: String {
        let name = displayName ?? username
        let parts = name.split(separator: " ")
        if parts.count >= 2 {
            return String(parts[0].prefix(1) + parts[1].prefix(1)).uppercased()
        }
        return String(name.prefix(2)).uppercased()
    }
}

struct LoginRequest: Codable {
    let username: String
    let pin: String?
}

struct LoginResponse: Codable {
    let token: String
    let user: User
    let expiresAt: String?

    enum CodingKeys: String, CodingKey {
        case token, user
        case expiresAt = "expires_at"
    }
}

// MARK: - Channel Models

struct Channel: Codable, Identifiable {
    let id: Int
    let platform: String
    let platformChannelId: String
    let channelUrl: String
    let name: String
    let description: String?
    let avatarUrl: String?
    let bannerUrl: String?
    let subscriberCount: Int?
    let videoCount: Int?
    let unwatchedCount: Int?
    let isActive: Bool
    let lastSyncedAt: String?
    let lastSyncError: String?
    let consecutiveErrors: Int?
    let importSource: String?
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, platform, name, description
        case platformChannelId = "platform_channel_id"
        case channelUrl = "channel_url"
        case avatarUrl = "avatar_url"
        case bannerUrl = "banner_url"
        case subscriberCount = "subscriber_count"
        case videoCount = "video_count"
        case unwatchedCount = "unwatched_count"
        case isActive = "is_active"
        case lastSyncedAt = "last_synced_at"
        case lastSyncError = "last_sync_error"
        case consecutiveErrors = "consecutive_errors"
        case importSource = "import_source"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    var platformIcon: String {
        switch platform.lowercased() {
        case "youtube": return "play.rectangle.fill"
        case "rumble": return "r.circle.fill"
        case "odysee": return "o.circle.fill"
        case "podcast": return "mic.fill"
        case "redbar": return "radio.fill"
        default: return "tv.fill"
        }
    }
}

struct ChannelsResponse: Codable {
    let items: [Channel]
    let total: Int
}

struct ChannelSearchResult: Codable, Identifiable {
    var id: String { "\(platform)_\(channelId)" }
    let platform: String
    let channelId: String
    let channelUrl: String
    let name: String
    let description: String?
    let avatarUrl: String?
    let subscriberCount: Int?
    let videoCount: Int?

    enum CodingKeys: String, CodingKey {
        case platform, name, description
        case channelId = "channel_id"
        case channelUrl = "channel_url"
        case avatarUrl = "avatar_url"
        case subscriberCount = "subscriber_count"
        case videoCount = "video_count"
    }
}

struct AddChannelRequest: Codable {
    let url: String
}

struct ImportChannelsRequest: Codable {
    let urls: [String]
}

// MARK: - Feed Models

struct FeedItem: Codable, Identifiable {
    let id: Int
    let channelId: Int?
    let platform: String
    let videoId: String
    let videoUrl: String
    let title: String
    let description: String?
    let thumbnailUrl: String?
    let durationSeconds: Int?
    let viewCount: Int?
    let uploadDate: String?
    let categories: [String]?
    let isWatched: Bool
    let watchedAt: String?
    let watchProgressSeconds: Int?
    let discoveredAt: String?
    let channelName: String?

    enum CodingKeys: String, CodingKey {
        case id, platform, title, description, categories
        case channelId = "channel_id"
        case videoId = "video_id"
        case videoUrl = "video_url"
        case thumbnailUrl = "thumbnail_url"
        case durationSeconds = "duration_seconds"
        case viewCount = "view_count"
        case uploadDate = "upload_date"
        case isWatched = "is_watched"
        case watchedAt = "watched_at"
        case watchProgressSeconds = "watch_progress_seconds"
        case discoveredAt = "discovered_at"
        case channelName = "channel_name"
    }

    var formattedDuration: String {
        guard let seconds = durationSeconds else { return "" }
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let secs = seconds % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        }
        return String(format: "%d:%02d", minutes, secs)
    }

    var formattedViews: String {
        guard let views = viewCount else { return "" }
        if views >= 1_000_000 {
            return String(format: "%.1fM views", Double(views) / 1_000_000)
        } else if views >= 1_000 {
            return String(format: "%.1fK views", Double(views) / 1_000)
        }
        return "\(views) views"
    }
}

struct FeedResponse: Codable {
    let items: [FeedItem]
    let total: Int
    let page: Int
    let perPage: Int
    let hasMore: Bool

    enum CodingKeys: String, CodingKey {
        case items, total, page
        case perPage = "per_page"
        case hasMore = "has_more"
    }
}

struct FeedByChannelResponse: Codable {
    let channels: [ChannelFeedGroup]
}

struct ChannelFeedGroup: Codable, Identifiable {
    let channel: Channel
    let items: [FeedItem]
    let totalUnwatched: Int

    var id: Int { channel.id }

    enum CodingKeys: String, CodingKey {
        case channel, items
        case totalUnwatched = "total_unwatched"
    }
}

struct FeedStats: Codable {
    let totalVideos: Int
    let watchedCount: Int
    let unwatchedCount: Int
    let byPlatform: [String: Int]?

    enum CodingKeys: String, CodingKey {
        case totalVideos = "total_videos"
        case watchedCount = "watched_count"
        case unwatchedCount = "unwatched_count"
        case byPlatform = "by_platform"
    }
}

// MARK: - Discover Models

struct Platform: Codable, Identifiable {
    var id: String { platformId }
    let platformId: String
    let name: String
    let icon: String?
    let color: String?
    let supportsSearch: Bool
    let supportsChannelFeed: Bool
    let supportsPlaylists: Bool

    enum CodingKeys: String, CodingKey {
        case name, icon, color
        case platformId = "id"
        case supportsSearch = "supports_search"
        case supportsChannelFeed = "supports_channel_feed"
        case supportsPlaylists = "supports_playlists"
    }
}

struct DiscoverSearchRequest: Codable {
    let query: String
    let searchType: String  // "videos", "channels", "playlists"
    let platforms: [String]?
    let maxResults: Int?

    enum CodingKeys: String, CodingKey {
        case query, platforms
        case searchType = "search_type"
        case maxResults = "max_results"
    }
}

struct DiscoverVideoResult: Codable, Identifiable {
    var id: String { "\(platform)_\(videoId)" }
    let platform: String
    let videoId: String
    let videoUrl: String
    let title: String
    let description: String?
    let thumbnailUrl: String?
    let channelName: String?
    let channelId: String?
    let channelUrl: String?
    let durationSeconds: Int?
    let viewCount: Int?
    let likeCount: Int?
    let uploadDate: String?
    let tags: [String]?

    enum CodingKeys: String, CodingKey {
        case platform, title, description, tags
        case videoId = "video_id"
        case videoUrl = "video_url"
        case thumbnailUrl = "thumbnail_url"
        case channelName = "channel_name"
        case channelId = "channel_id"
        case channelUrl = "channel_url"
        case durationSeconds = "duration_seconds"
        case viewCount = "view_count"
        case likeCount = "like_count"
        case uploadDate = "upload_date"
    }

    var formattedDuration: String {
        guard let seconds = durationSeconds else { return "" }
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let secs = seconds % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        }
        return String(format: "%d:%02d", minutes, secs)
    }
}

struct DiscoverSearchResponse: Codable {
    let videos: [DiscoverVideoResult]?
    let channels: [ChannelSearchResult]?
    let totalResults: Int?
    let timingMs: Double?

    enum CodingKeys: String, CodingKey {
        case videos, channels
        case totalResults = "total_results"
        case timingMs = "timing_ms"
    }
}

struct QuickSaveRequest: Codable {
    let url: String
}

// MARK: - Saved Videos Models

struct SavedVideo: Codable, Identifiable {
    let id: Int
    let platform: String
    let videoId: String
    let videoUrl: String
    let title: String
    let description: String?
    let thumbnailUrl: String?
    let durationSeconds: Int?
    let viewCount: Int?
    let uploadDate: String?
    let channelName: String?
    let channelId: String?
    let channelUrl: String?
    let isWatched: Bool
    let watchedAt: String?
    let watchProgressSeconds: Int?
    let notes: String?
    let savedAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, platform, title, description, notes
        case videoId = "video_id"
        case videoUrl = "video_url"
        case thumbnailUrl = "thumbnail_url"
        case durationSeconds = "duration_seconds"
        case viewCount = "view_count"
        case uploadDate = "upload_date"
        case channelName = "channel_name"
        case channelId = "channel_id"
        case channelUrl = "channel_url"
        case isWatched = "is_watched"
        case watchedAt = "watched_at"
        case watchProgressSeconds = "watch_progress_seconds"
        case savedAt = "saved_at"
        case updatedAt = "updated_at"
    }

    var formattedDuration: String {
        guard let seconds = durationSeconds else { return "" }
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let secs = seconds % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        }
        return String(format: "%d:%02d", minutes, secs)
    }
}

struct SavedVideoRequest: Codable {
    let url: String
}

struct SavedVideoStats: Codable {
    let total: Int
    let watched: Int
    let unwatched: Int
    let byPlatform: [String: Int]?

    enum CodingKeys: String, CodingKey {
        case total, watched, unwatched
        case byPlatform = "by_platform"
    }
}

// MARK: - Collection Models

struct Collection: Codable, Identifiable {
    let id: Int
    let name: String
    let slug: String
    let description: String?
    let coverUrl: String?
    let sortOrder: Int
    let itemCount: Int
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, name, slug, description
        case coverUrl = "cover_url"
        case sortOrder = "sort_order"
        case itemCount = "item_count"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct CollectionsResponse: Codable {
    let items: [Collection]
    let total: Int
}

struct CollectionWithItems: Codable, Identifiable {
    let id: Int
    let name: String
    let slug: String
    let description: String?
    let coverUrl: String?
    let sortOrder: Int
    let itemCount: Int
    let items: [CollectionItem]
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, name, slug, description, items
        case coverUrl = "cover_url"
        case sortOrder = "sort_order"
        case itemCount = "item_count"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct CollectionItem: Codable, Identifiable {
    let id: Int
    let collectionId: Int?
    let itemType: String  // "video" or "image"
    let url: String
    let thumbnailUrl: String?
    let title: String?
    let sourceUrl: String?
    let domain: String?
    let embedType: String?
    let videoId: String?
    let sortOrder: Int?
    let addedAt: String?

    enum CodingKeys: String, CodingKey {
        case id, url, title, domain
        case collectionId = "collection_id"
        case itemType = "item_type"
        case thumbnailUrl = "thumbnail_url"
        case sourceUrl = "source_url"
        case embedType = "embed_type"
        case videoId = "video_id"
        case sortOrder = "sort_order"
        case addedAt = "added_at"
    }
}

struct CreateCollectionRequest: Codable {
    let name: String
    var description: String?
}

struct AddCollectionItemRequest: Codable {
    let itemType: String
    let url: String
    var thumbnailUrl: String?
    var title: String?
    var sourceUrl: String?
    var videoId: String?

    enum CodingKeys: String, CodingKey {
        case url, title
        case itemType = "item_type"
        case thumbnailUrl = "thumbnail_url"
        case sourceUrl = "source_url"
        case videoId = "video_id"
    }
}

struct QuickAddRequest: Codable {
    let itemType: String
    let url: String
    var thumbnailUrl: String?
    var title: String?
    var sourceUrl: String?

    enum CodingKeys: String, CodingKey {
        case url, title
        case itemType = "item_type"
        case thumbnailUrl = "thumbnail_url"
        case sourceUrl = "source_url"
    }
}

// MARK: - Watch State Updates

struct WatchedRequest: Codable {
    let isWatched: Bool

    enum CodingKeys: String, CodingKey {
        case isWatched = "is_watched"
    }
}

struct ProgressRequest: Codable {
    let watchProgressSeconds: Int

    enum CodingKeys: String, CodingKey {
        case watchProgressSeconds = "watch_progress_seconds"
    }
}

// MARK: - Stream Info

struct StreamInfo: Codable {
    let streamUrl: String?
    let audioUrl: String?
    let quality: String?
    let formatType: String?
    let duration: Int?
    let title: String?
    let error: String?

    enum CodingKeys: String, CodingKey {
        case streamUrl = "stream_url"
        case audioUrl = "audio_url"
        case quality
        case formatType = "format_type"
        case duration
        case title
        case error
    }
}

// MARK: - API Response Helpers

struct MessageResponse: Codable {
    let message: String
}

struct APIError: Codable, Error {
    let detail: String?
    let message: String?

    var errorDescription: String {
        detail ?? message ?? "Unknown error"
    }
}

// MARK: - Feed Modes

enum FeedMode: String, CaseIterable {
    case newest = "newest"
    case oldest = "oldest"
    case catchUp = "catch_up"
    case quickWatch = "quick_watch"
    case deepDive = "deep_dive"
    case random = "random"

    var displayName: String {
        switch self {
        case .newest: return "Newest"
        case .oldest: return "Oldest"
        case .catchUp: return "Catch Up"
        case .quickWatch: return "Quick Watch"
        case .deepDive: return "Deep Dive"
        case .random: return "Random"
        }
    }

    var icon: String {
        switch self {
        case .newest: return "arrow.down.circle"
        case .oldest: return "arrow.up.circle"
        case .catchUp: return "clock.arrow.circlepath"
        case .quickWatch: return "bolt.circle"
        case .deepDive: return "book.circle"
        case .random: return "shuffle.circle"
        }
    }
}

enum WatchFilter: String, CaseIterable {
    case all = "all"
    case unwatched = "unwatched"
    case watched = "watched"

    var displayName: String {
        switch self {
        case .all: return "All"
        case .unwatched: return "Unwatched"
        case .watched: return "Watched"
        }
    }
}

// MARK: - Video URL Parsing Utility

/// Utility for extracting video IDs and platform information from video URLs
struct VideoURLParser {

    /// Extracts the video ID from a video URL
    /// - Parameters:
    ///   - url: The video URL to parse
    ///   - platform: Optional platform hint to improve parsing accuracy
    /// - Returns: The extracted video ID, or nil if parsing failed
    static func extractVideoId(from url: String, platform: String? = nil) -> String? {
        let detectedPlatform = platform ?? extractPlatform(from: url)

        switch detectedPlatform.lowercased() {
        case "youtube":
            return extractYouTubeVideoId(from: url)
        case "rumble":
            return extractRumbleVideoId(from: url)
        case "odysee":
            return extractOdyseeVideoId(from: url)
        default:
            return nil
        }
    }

    /// Extracts the platform name from a video URL
    /// - Parameter url: The video URL to parse
    /// - Returns: The platform name (youtube, rumble, odysee, or unknown)
    static func extractPlatform(from url: String) -> String {
        let lowercased = url.lowercased()

        if lowercased.contains("youtube.com") || lowercased.contains("youtu.be") {
            return "youtube"
        } else if lowercased.contains("rumble.com") {
            return "rumble"
        } else if lowercased.contains("odysee.com") {
            return "odysee"
        }

        return "unknown"
    }

    // MARK: - Private Helpers

    /// Extracts video ID from YouTube URLs
    private static func extractYouTubeVideoId(from url: String) -> String? {
        // Try URL query parameter first (watch?v=...)
        if let urlComponents = URLComponents(string: url),
           let queryItems = urlComponents.queryItems,
           let videoId = queryItems.first(where: { $0.name == "v" })?.value,
           !videoId.isEmpty {
            return videoId
        }

        // Try path-based formats (youtu.be/ID, embed/ID, v/ID)
        guard let urlObj = URL(string: url) else { return nil }

        let pathComponents = urlObj.pathComponents.filter { $0 != "/" }

        // youtu.be/VIDEO_ID
        if url.contains("youtu.be") && !pathComponents.isEmpty {
            return pathComponents[0]
        }

        // /embed/VIDEO_ID or /v/VIDEO_ID
        if let embedIndex = pathComponents.firstIndex(where: { $0 == "embed" || $0 == "v" }),
           embedIndex + 1 < pathComponents.count {
            return pathComponents[embedIndex + 1]
        }

        return nil
    }

    /// Extracts video ID from Rumble URLs
    private static func extractRumbleVideoId(from url: String) -> String? {
        guard let urlObj = URL(string: url) else { return nil }

        let pathComponents = urlObj.pathComponents.filter { $0 != "/" }

        // Check for embed path first
        if let embedIndex = pathComponents.firstIndex(of: "embed"),
           embedIndex + 1 < pathComponents.count {
            let embedId = pathComponents[embedIndex + 1]
            return embedId.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        }

        // Standard rumble video URL: /vXXXXXX-title.html
        for component in pathComponents {
            if component.hasPrefix("v") && component.count > 1 {
                if let dashIndex = component.firstIndex(of: "-") {
                    return String(component[..<dashIndex])
                }
                if component.hasSuffix(".html") {
                    let withoutHtml = component.replacingOccurrences(of: ".html", with: "")
                    if let dashIndex = withoutHtml.firstIndex(of: "-") {
                        return String(withoutHtml[..<dashIndex])
                    }
                }
                return component
            }
        }

        return nil
    }

    /// Extracts video ID from Odysee URLs
    private static func extractOdyseeVideoId(from url: String) -> String? {
        guard let urlObj = URL(string: url) else { return nil }

        let pathComponents = urlObj.pathComponents.filter { $0 != "/" }

        // Check for embed path: $/embed/claim-name/claim-id
        if pathComponents.contains("$") {
            if let embedIndex = pathComponents.firstIndex(of: "embed"),
               embedIndex + 2 < pathComponents.count {
                let claimName = pathComponents[embedIndex + 1]
                let claimId = pathComponents[embedIndex + 2]
                return "\(claimName)/\(claimId)"
            }
        }

        // Standard URL format: @channel:id/video-title:claimId
        for (index, component) in pathComponents.enumerated() {
            if component.hasPrefix("@") && index + 1 < pathComponents.count {
                return pathComponents[index + 1]
            }
        }

        // Direct claim URL
        if !pathComponents.isEmpty && !pathComponents[0].hasPrefix("$") {
            return pathComponents.joined(separator: "/")
        }

        return nil
    }
}

// MARK: - Video Conversion Protocol

/// Protocol for types that can be converted to FeedItem for unified playback
protocol FeedItemConvertible {
    func toFeedItem() -> FeedItem?
}

extension SavedVideo: FeedItemConvertible {
    func toFeedItem() -> FeedItem? {
        FeedItem(
            id: id,
            channelId: nil,
            platform: platform,
            videoId: videoId,
            videoUrl: videoUrl,
            title: title,
            description: description,
            thumbnailUrl: thumbnailUrl,
            durationSeconds: durationSeconds,
            viewCount: viewCount,
            uploadDate: uploadDate,
            categories: nil,
            isWatched: isWatched,
            watchedAt: watchedAt,
            watchProgressSeconds: watchProgressSeconds,
            discoveredAt: nil,
            channelName: channelName
        )
    }
}

extension DiscoverVideoResult: FeedItemConvertible {
    func toFeedItem() -> FeedItem? {
        // Use videoId from API, with fallback to URL extraction
        let resolvedVideoId = !videoId.isEmpty
            ? videoId
            : VideoURLParser.extractVideoId(from: videoUrl, platform: platform) ?? videoId

        return FeedItem(
            id: 0,
            channelId: nil,
            platform: platform,
            videoId: resolvedVideoId,
            videoUrl: videoUrl,
            title: title,
            description: description,
            thumbnailUrl: thumbnailUrl,
            durationSeconds: durationSeconds,
            viewCount: viewCount,
            uploadDate: uploadDate,
            categories: nil,
            isWatched: false,
            watchedAt: nil,
            watchProgressSeconds: nil,
            discoveredAt: nil,
            channelName: channelName
        )
    }
}

extension CollectionItem: FeedItemConvertible {
    func toFeedItem() -> FeedItem? {
        // Only convert video items
        guard itemType == "video" else { return nil }

        // Resolve platform: use embedType or extract from URL
        let resolvedPlatform = embedType ?? VideoURLParser.extractPlatform(from: url)

        // Resolve videoId: use stored value or extract from URL
        let resolvedVideoId: String
        if let existingVideoId = videoId, !existingVideoId.isEmpty {
            resolvedVideoId = existingVideoId
        } else if let extractedId = VideoURLParser.extractVideoId(from: url, platform: resolvedPlatform) {
            resolvedVideoId = extractedId
        } else {
            // Cannot create FeedItem without valid videoId
            return nil
        }

        return FeedItem(
            id: id,
            channelId: nil,
            platform: resolvedPlatform,
            videoId: resolvedVideoId,
            videoUrl: url,
            title: title ?? "Untitled",
            description: nil,
            thumbnailUrl: thumbnailUrl,
            durationSeconds: nil,
            viewCount: nil,
            uploadDate: nil,
            categories: nil,
            isWatched: false,
            watchedAt: nil,
            watchProgressSeconds: nil,
            discoveredAt: nil,
            channelName: nil
        )
    }
}
