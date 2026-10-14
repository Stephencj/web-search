import SwiftData
import Foundation

@Model
final class Collection {
    @Attribute(.unique) var id: Int
    var name: String
    var descriptionText: String?
    var coverUrl: String?
    var itemCount: Int
    var createdAt: Date

    var user: User?
    @Relationship(deleteRule: .cascade, inverse: \CollectionItem.collection) var items: [CollectionItem] = []

    init(
        id: Int,
        name: String,
        descriptionText: String? = nil,
        coverUrl: String? = nil,
        itemCount: Int = 0,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.name = name
        self.descriptionText = descriptionText
        self.coverUrl = coverUrl
        self.itemCount = itemCount
        self.createdAt = createdAt
    }
}

@Model
final class CollectionItem {
    @Attribute(.unique) var id: Int
    var videoId: String
    var videoUrl: String
    var title: String
    var thumbnailUrl: String?
    var channelName: String?
    var platform: String?
    var durationSeconds: Int?
    var addedAt: Date

    var collection: Collection?

    init(
        id: Int,
        videoId: String,
        videoUrl: String,
        title: String,
        thumbnailUrl: String? = nil,
        channelName: String? = nil,
        platform: String? = nil,
        durationSeconds: Int? = nil,
        addedAt: Date = Date()
    ) {
        self.id = id
        self.videoId = videoId
        self.videoUrl = videoUrl
        self.title = title
        self.thumbnailUrl = thumbnailUrl
        self.channelName = channelName
        self.platform = platform
        self.durationSeconds = durationSeconds
        self.addedAt = addedAt
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

// MARK: - API Response Models
struct CollectionResponse: Codable {
    let id: Int
    let name: String
    let description: String?
    let coverUrl: String?
    let itemCount: Int?
    let createdAt: String?
    let items: [CollectionItemResponse]?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case description
        case coverUrl = "cover_url"
        case itemCount = "item_count"
        case createdAt = "created_at"
        case items
    }
}

struct CollectionItemResponse: Codable {
    let id: Int
    let videoId: String
    let videoUrl: String
    let title: String
    let thumbnailUrl: String?
    let channelName: String?
    let platform: String?
    let durationSeconds: Int?
    let addedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case videoId = "video_id"
        case videoUrl = "video_url"
        case title
        case thumbnailUrl = "thumbnail_url"
        case channelName = "channel_name"
        case platform
        case durationSeconds = "duration_seconds"
        case addedAt = "added_at"
    }
}
