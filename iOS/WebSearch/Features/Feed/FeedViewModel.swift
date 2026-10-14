import Foundation
import Combine
import SwiftData

enum FeedMode: String, CaseIterable, Identifiable {
    case newest = "Newest"
    case catchUp = "Catch Up"
    case discovery = "Discovery"
    case shortForm = "Short Form"

    var id: String { rawValue }

    var apiValue: String {
        switch self {
        case .newest: return "newest"
        case .catchUp: return "catch_up"
        case .discovery: return "discovery"
        case .shortForm: return "short_form"
        }
    }
}

enum FeedFilter: String, CaseIterable, Identifiable {
    case all = "All"
    case unwatched = "Unwatched"
    case watched = "Watched"

    var id: String { rawValue }

    var apiValue: String? {
        switch self {
        case .all: return nil
        case .unwatched: return "unwatched"
        case .watched: return "watched"
        }
    }
}

enum Platform: String, CaseIterable, Identifiable {
    case all = "All"
    case youtube = "YouTube"
    case rumble = "Rumble"
    case podcast = "Podcast"

    var id: String { rawValue }

    var apiValue: String? {
        switch self {
        case .all: return nil
        case .youtube: return "youtube"
        case .rumble: return "rumble"
        case .podcast: return "podcast"
        }
    }
}

@MainActor
final class FeedViewModel: ObservableObject {
    // MARK: - Published State
    @Published private(set) var feedItems: [FeedItem] = []
    @Published private(set) var isLoading = false
    @Published private(set) var isLoadingMore = false
    @Published private(set) var error: String?
    @Published private(set) var hasMorePages = true

    @Published var selectedMode: FeedMode = .newest
    @Published var selectedFilter: FeedFilter = .all
    @Published var selectedPlatform: Platform = .all

    // MARK: - Pagination
    private var currentPage = 1
    private let perPage = 20

    // MARK: - Model Context
    private var modelContext: ModelContext?

    init(modelContext: ModelContext? = nil) {
        self.modelContext = modelContext
    }

    // MARK: - Load Feed
    func loadFeed() async {
        guard !isLoading else { return }

        isLoading = true
        error = nil
        currentPage = 1

        do {
            let response = try await APIClient.shared.getFeed(
                filter: selectedFilter.apiValue,
                platform: selectedPlatform.apiValue,
                mode: selectedMode.apiValue,
                page: currentPage,
                perPage: perPage
            )

            feedItems = response.items.map { mapToFeedItem($0) }
            hasMorePages = response.items.count >= perPage
            currentPage = 1

            // Cache to SwiftData if context available
            if let context = modelContext {
                for item in feedItems {
                    context.insert(item)
                }
                try? context.save()
            }

        } catch let apiError as APIError {
            error = apiError.errorDescription
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    func loadMore() async {
        guard !isLoading && !isLoadingMore && hasMorePages else { return }

        isLoadingMore = true

        do {
            let nextPage = currentPage + 1
            let response = try await APIClient.shared.getFeed(
                filter: selectedFilter.apiValue,
                platform: selectedPlatform.apiValue,
                mode: selectedMode.apiValue,
                page: nextPage,
                perPage: perPage
            )

            let newItems = response.items.map { mapToFeedItem($0) }
            feedItems.append(contentsOf: newItems)
            hasMorePages = newItems.count >= perPage
            currentPage = nextPage

        } catch {
            // Silently fail for pagination errors
            print("Failed to load more: \(error)")
        }

        isLoadingMore = false
    }

    func refresh() async {
        await loadFeed()
    }

    // MARK: - Actions
    func toggleWatched(_ item: FeedItem) {
        let newValue = !item.isWatched
        item.isWatched = newValue
        if newValue {
            item.watchedAt = Date()
        }

        Task {
            do {
                try await APIClient.shared.markWatched(id: item.id, watched: newValue)
            } catch {
                // Revert on failure
                item.isWatched = !newValue
                print("Failed to update watched status: \(error)")
            }
        }
    }

    func saveVideo(_ item: FeedItem) {
        Task {
            do {
                try await APIClient.shared.requestVoid(.saveVideo(videoUrl: item.videoUrl))
            } catch {
                print("Failed to save video: \(error)")
            }
        }
    }

    func setMode(_ mode: FeedMode) {
        selectedMode = mode
        Task {
            await loadFeed()
        }
    }

    func setFilter(_ filter: FeedFilter) {
        selectedFilter = filter
        Task {
            await loadFeed()
        }
    }

    func setPlatform(_ platform: Platform) {
        selectedPlatform = platform
        Task {
            await loadFeed()
        }
    }

    // MARK: - Mapping
    private func mapToFeedItem(_ response: FeedItemResponse) -> FeedItem {
        FeedItem(
            id: response.id,
            platform: response.platform,
            videoId: response.videoId,
            videoUrl: response.videoUrl,
            title: response.title,
            thumbnailUrl: response.thumbnailUrl,
            channelName: response.channelName,
            durationSeconds: response.durationSeconds,
            viewCount: response.viewCount,
            uploadDate: parseDate(response.uploadDate),
            discoveredAt: parseDate(response.discoveredAt) ?? Date(),
            isWatched: response.isWatched ?? false,
            watchProgressSeconds: response.watchProgressSeconds,
            watchedAt: parseDate(response.watchedAt)
        )
    }

    private func parseDate(_ dateString: String?) -> Date? {
        guard let dateString = dateString else { return nil }

        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = formatter.date(from: dateString) {
            return date
        }

        formatter.formatOptions = [.withInternetDateTime]
        return formatter.date(from: dateString)
    }
}
