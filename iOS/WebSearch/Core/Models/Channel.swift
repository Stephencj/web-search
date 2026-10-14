import SwiftData
import Foundation

@Model
final class Channel {
    @Attribute(.unique) var id: Int
    var platform: String  // youtube, rumble, podcast
    var channelId: String
    var url: String
    var name: String
    var avatarUrl: String?
    var subscriberCount: Int?
    var videoCount: Int?
    var isActive: Bool
    var lastSyncedAt: Date?
    var syncError: String?

    @Relationship(deleteRule: .cascade, inverse: \FeedItem.channel) var feedItems: [FeedItem] = []

    init(
        id: Int,
        platform: String,
        channelId: String,
        url: String,
        name: String,
        avatarUrl: String? = nil,
        subscriberCount: Int? = nil,
        videoCount: Int? = nil,
        isActive: Bool = true,
        lastSyncedAt: Date? = nil,
        syncError: String? = nil
    ) {
        self.id = id
        self.platform = platform
        self.channelId = channelId
        self.url = url
        self.name = name
        self.avatarUrl = avatarUrl
        self.subscriberCount = subscriberCount
        self.videoCount = videoCount
        self.isActive = isActive
        self.lastSyncedAt = lastSyncedAt
        self.syncError = syncError
    }
}

// MARK: - API Response Model
struct ChannelResponse: Codable {
    let id: Int
    let platform: String
    let channelId: String
    let url: String
    let name: String
    let avatarUrl: String?
    let subscriberCount: Int?
    let videoCount: Int?
    let isActive: Bool?
    let lastSyncedAt: String?
    let syncError: String?

    enum CodingKeys: String, CodingKey {
        case id
        case platform
        case channelId = "channel_id"
        case url
        case name
        case avatarUrl = "avatar_url"
        case subscriberCount = "subscriber_count"
        case videoCount = "video_count"
        case isActive = "is_active"
        case lastSyncedAt = "last_synced_at"
        case syncError = "sync_error"
    }
}
