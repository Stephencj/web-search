import SwiftData
import Foundation

@Model
final class WatchState {
    @Attribute(.unique) var id: String  // Composite: "\(userId)_\(feedItemId)"
    var feedItemId: Int
    var isWatched: Bool
    var watchProgressSeconds: Int?
    var watchedAt: Date?
    var updatedAt: Date

    var user: User?

    init(
        userId: Int,
        feedItemId: Int,
        isWatched: Bool = false,
        watchProgressSeconds: Int? = nil,
        watchedAt: Date? = nil
    ) {
        self.id = "\(userId)_\(feedItemId)"
        self.feedItemId = feedItemId
        self.isWatched = isWatched
        self.watchProgressSeconds = watchProgressSeconds
        self.watchedAt = watchedAt
        self.updatedAt = Date()
    }

    func update(isWatched: Bool? = nil, watchProgressSeconds: Int? = nil) {
        if let isWatched = isWatched {
            self.isWatched = isWatched
            if isWatched {
                self.watchedAt = Date()
            }
        }
        if let progress = watchProgressSeconds {
            self.watchProgressSeconds = progress
        }
        self.updatedAt = Date()
    }
}

// MARK: - API Response Model
struct WatchStateResponse: Codable {
    let feedItemId: Int
    let isWatched: Bool
    let watchProgressSeconds: Int?
    let watchedAt: String?

    enum CodingKeys: String, CodingKey {
        case feedItemId = "feed_item_id"
        case isWatched = "is_watched"
        case watchProgressSeconds = "watch_progress_seconds"
        case watchedAt = "watched_at"
    }
}
