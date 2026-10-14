import SwiftData
import Foundation

@Model
final class User {
    @Attribute(.unique) var id: Int
    var username: String
    var displayName: String?
    var avatarColor: String
    var isAdmin: Bool
    var lastLoginAt: Date?

    @Relationship(deleteRule: .cascade, inverse: \WatchState.user) var watchStates: [WatchState] = []
    @Relationship(deleteRule: .cascade, inverse: \SavedVideo.user) var savedVideos: [SavedVideo] = []
    @Relationship(deleteRule: .cascade, inverse: \Collection.user) var collections: [Collection] = []

    init(
        id: Int,
        username: String,
        displayName: String? = nil,
        avatarColor: String = "#6366f1",
        isAdmin: Bool = false,
        lastLoginAt: Date? = nil
    ) {
        self.id = id
        self.username = username
        self.displayName = displayName
        self.avatarColor = avatarColor
        self.isAdmin = isAdmin
        self.lastLoginAt = lastLoginAt
    }
}

// MARK: - API Response Model
struct UserResponse: Codable {
    let id: Int
    let username: String
    let displayName: String?
    let avatarColor: String?
    let isAdmin: Bool?
    let lastLoginAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case username
        case displayName = "display_name"
        case avatarColor = "avatar_color"
        case isAdmin = "is_admin"
        case lastLoginAt = "last_login_at"
    }
}
