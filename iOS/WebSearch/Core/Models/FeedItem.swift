import SwiftData
import Foundation

@Model
final class FeedItem {
    @Attribute(.unique) var id: Int
    var platform: String
    var videoId: String
    var videoUrl: String
    var title: String
    var thumbnailUrl: String?
    var channelName: String?
    var durationSeconds: Int?
    var viewCount: Int?
    var uploadDate: Date?
    var discoveredAt: Date

    // Watch state (denormalized for simpler queries)
    var isWatched: Bool
    var watchProgressSeconds: Int?
    var watchedAt: Date?

    var channel: Channel?

    init(
        id: Int,
        platform: String,
        videoId: String,
        videoUrl: String,
        title: String,
        thumbnailUrl: String? = nil,
        channelName: String? = nil,
        durationSeconds: Int? = nil,
        viewCount: Int? = nil,
        uploadDate: Date? = nil,
        discoveredAt: Date = Date(),
        isWatched: Bool = false,
        watchProgressSeconds: Int? = nil,
        watchedAt: Date? = nil
    ) {
        self.id = id
        self.platform = platform
        self.videoId = videoId
        self.videoUrl = videoUrl
        self.title = title
        self.thumbnailUrl = thumbnailUrl
        self.channelName = channelName
        self.durationSeconds = durationSeconds
        self.viewCount = viewCount
        self.uploadDate = uploadDate
        self.discoveredAt = discoveredAt
        self.isWatched = isWatched
        self.watchProgressSeconds = watchProgressSeconds
        self.watchedAt = watchedAt
    }

    var formattedDuration: String {
        guard let seconds = durationSeconds else { return "" }
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let secs = seconds % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        } else {
            return String(format: "%d:%02d", minutes, secs)
        }
    }

    var progressPercentage: Double {
        guard let progress = watchProgressSeconds,
              let duration = durationSeconds,
              duration > 0 else { return 0 }
        return Double(progress) / Double(duration)
    }
}

// MARK: - API Response Model
struct FeedItemResponse: Codable {
    let id: Int
    let platform: String
    let videoId: String
    let videoUrl: String
    let title: String
    let thumbnailUrl: String?
    let channelName: String?
    let durationSeconds: Int?
    let viewCount: Int?
    let uploadDate: String?
    let discoveredAt: String?
    let isWatched: Bool?
    let watchProgressSeconds: Int?
    let watchedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case platform
        case videoId = "video_id"
        case videoUrl = "video_url"
        case title
        case thumbnailUrl = "thumbnail_url"
        case channelName = "channel_name"
        case durationSeconds = "duration_seconds"
        case viewCount = "view_count"
        case uploadDate = "upload_date"
        case discoveredAt = "discovered_at"
        case isWatched = "is_watched"
        case watchProgressSeconds = "watch_progress_seconds"
        case watchedAt = "watched_at"
    }
}

// MARK: - Feed Response Wrapper
struct FeedResponse: Codable {
    let items: [FeedItemResponse]
    let total: Int?
    let page: Int?
    let perPage: Int?

    enum CodingKeys: String, CodingKey {
        case items
        case total
        case page
        case perPage = "per_page"
    }
}
