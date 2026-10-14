import SwiftData
import Foundation

@Model
final class SavedVideo {
    @Attribute(.unique) var id: Int
    var platform: String
    var videoId: String
    var videoUrl: String
    var title: String
    var thumbnailUrl: String?
    var channelName: String?
    var durationSeconds: Int?
    var isWatched: Bool
    var watchProgressSeconds: Int?
    var savedAt: Date
    var notes: String?

    var user: User?

    init(
        id: Int,
        platform: String,
        videoId: String,
        videoUrl: String,
        title: String,
        thumbnailUrl: String? = nil,
        channelName: String? = nil,
        durationSeconds: Int? = nil,
        isWatched: Bool = false,
        watchProgressSeconds: Int? = nil,
        savedAt: Date = Date(),
        notes: String? = nil
    ) {
        self.id = id
        self.platform = platform
        self.videoId = videoId
        self.videoUrl = videoUrl
        self.title = title
        self.thumbnailUrl = thumbnailUrl
        self.channelName = channelName
        self.durationSeconds = durationSeconds
        self.isWatched = isWatched
        self.watchProgressSeconds = watchProgressSeconds
        self.savedAt = savedAt
        self.notes = notes
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
}

// MARK: - API Response Model
struct SavedVideoResponse: Codable {
    let id: Int
    let platform: String
    let videoId: String
    let videoUrl: String
    let title: String
    let thumbnailUrl: String?
    let channelName: String?
    let durationSeconds: Int?
    let isWatched: Bool?
    let watchProgressSeconds: Int?
    let savedAt: String?
    let notes: String?

    enum CodingKeys: String, CodingKey {
        case id
        case platform
        case videoId = "video_id"
        case videoUrl = "video_url"
        case title
        case thumbnailUrl = "thumbnail_url"
        case channelName = "channel_name"
        case durationSeconds = "duration_seconds"
        case isWatched = "is_watched"
        case watchProgressSeconds = "watch_progress_seconds"
        case savedAt = "saved_at"
        case notes
    }
}
