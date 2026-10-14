import SwiftUI

// MARK: - Protocol for Video Context Menu Data

/// Common interface for video types that can use the context menu
protocol VideoContextMenuData {
    var menuVideoUrl: String { get }
    var menuTitle: String { get }
    var menuThumbnailUrl: String? { get }
    var menuVideoId: String { get }
    var menuPlatform: String { get }
    var menuItemId: Int? { get }
    var menuIsWatched: Bool? { get }
}

// MARK: - Protocol Conformance

extension FeedItem: VideoContextMenuData {
    var menuVideoUrl: String { videoUrl }
    var menuTitle: String { title }
    var menuThumbnailUrl: String? { thumbnailUrl }
    var menuVideoId: String { videoId }
    var menuPlatform: String { platform }
    var menuItemId: Int? { id }
    var menuIsWatched: Bool? { isWatched }
}

extension DiscoverVideoResult: VideoContextMenuData {
    var menuVideoUrl: String { videoUrl }
    var menuTitle: String { title }
    var menuThumbnailUrl: String? { thumbnailUrl }
    var menuVideoId: String { videoId }
    var menuPlatform: String { platform }
    var menuItemId: Int? { nil }
    var menuIsWatched: Bool? { nil }
}

extension CollectionItem: VideoContextMenuData {
    var menuVideoUrl: String { url }
    var menuTitle: String { title ?? "Untitled" }
    var menuThumbnailUrl: String? { thumbnailUrl }
    var menuVideoId: String { videoId ?? "" }
    var menuPlatform: String { embedType ?? VideoURLParser.extractPlatform(from: url) }
    var menuItemId: Int? { nil }
    var menuIsWatched: Bool? { nil }
}

// MARK: - Context Menu Handler

@MainActor
class VideoContextMenuHandler: ObservableObject {
    @Published var showAddToCollection = false
    @Published var showSuccessToast = false
    @Published var successMessage = ""
    @Published var showErrorToast = false
    @Published var errorMessage = ""
    @Published var collections: [Collection] = []

    private var currentVideoForCollection: FeedItem?

    func loadCollections(using apiClient: APIClient) async {
        do {
            collections = try await apiClient.getCollections()
        } catch {
            print("Failed to load collections: \(error)")
        }
    }

    /// Prepare a video for the Add to Collection modal
    func prepareAddToCollection<T: VideoContextMenuData>(_ video: T) {
        currentVideoForCollection = FeedItem(
            id: video.menuItemId ?? 0,
            channelId: nil,
            platform: video.menuPlatform,
            videoId: video.menuVideoId,
            videoUrl: video.menuVideoUrl,
            title: video.menuTitle,
            description: nil,
            thumbnailUrl: video.menuThumbnailUrl,
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
        showAddToCollection = true
    }

    var videoForCollection: FeedItem? { currentVideoForCollection }

    /// Save video to library
    func saveVideo<T: VideoContextMenuData>(_ video: T, using apiClient: APIClient) async {
        do {
            _ = try await apiClient.saveVideoFromUrl(url: video.menuVideoUrl)
            successMessage = "Saved to library"
            showSuccessToast = true
            hideToastAfterDelay()
        } catch {
            errorMessage = "Failed to save"
            showErrorToast = true
            hideToastAfterDelay()
        }
    }

    /// Toggle watched state for a feed item
    func toggleWatched(itemId: Int, isCurrentlyWatched: Bool, using apiClient: APIClient) async {
        do {
            if isCurrentlyWatched {
                _ = try await apiClient.markUnwatched(itemId: itemId)
                successMessage = "Marked as unwatched"
            } else {
                _ = try await apiClient.markWatched(itemId: itemId)
                successMessage = "Marked as watched"
            }
            showSuccessToast = true
            hideToastAfterDelay()
        } catch {
            errorMessage = "Failed to update"
            showErrorToast = true
            hideToastAfterDelay()
        }
    }

    private func hideToastAfterDelay() {
        Task {
            try? await Task.sleep(nanoseconds: 2_000_000_000)
            showSuccessToast = false
            showErrorToast = false
        }
    }
}

// MARK: - Toast View

struct ToastView: View {
    let message: String
    let isSuccess: Bool

    var body: some View {
        VStack {
            Spacer()
            HStack(spacing: 12) {
                Image(systemName: isSuccess ? "checkmark.circle.fill" : "xmark.circle.fill")
                    .font(.title2)
                    .foregroundStyle(isSuccess ? .green : .red)
                Text(message)
                    .font(.headline)
            }
            .padding(.horizontal, 32)
            .padding(.vertical, 20)
            .background(.ultraThinMaterial)
            .clipShape(Capsule())
            .padding(.bottom, 80)
        }
        .transition(.move(edge: .bottom).combined(with: .opacity))
    }
}

// MARK: - Toast Overlay Modifier

struct ToastOverlay: ViewModifier {
    @ObservedObject var handler: VideoContextMenuHandler

    func body(content: Content) -> some View {
        content
            .overlay {
                if handler.showSuccessToast {
                    ToastView(message: handler.successMessage, isSuccess: true)
                }
                if handler.showErrorToast {
                    ToastView(message: handler.errorMessage, isSuccess: false)
                }
            }
            .animation(.easeInOut(duration: 0.3), value: handler.showSuccessToast)
            .animation(.easeInOut(duration: 0.3), value: handler.showErrorToast)
    }
}

extension View {
    func toastOverlay(handler: VideoContextMenuHandler) -> some View {
        modifier(ToastOverlay(handler: handler))
    }
}

// MARK: - Context Menu View Modifier

struct VideoCardContextMenu<T: VideoContextMenuData>: ViewModifier {
    let video: T
    let showAddToCollection: Bool
    let showSave: Bool
    let showWatchToggle: Bool
    let handler: VideoContextMenuHandler
    let apiClient: APIClient
    var onWatchStateChanged: (() -> Void)?

    func body(content: Content) -> some View {
        content
            .contextMenu {
                if showAddToCollection {
                    Button {
                        handler.prepareAddToCollection(video)
                    } label: {
                        Label("Add to Collection", systemImage: "plus.rectangle.on.folder")
                    }
                }

                if showSave {
                    Button {
                        Task {
                            await handler.saveVideo(video, using: apiClient)
                        }
                    } label: {
                        Label("Save", systemImage: "square.and.arrow.down")
                    }
                }

                if showWatchToggle, let itemId = video.menuItemId, let isWatched = video.menuIsWatched {
                    Button {
                        Task {
                            await handler.toggleWatched(
                                itemId: itemId,
                                isCurrentlyWatched: isWatched,
                                using: apiClient
                            )
                            onWatchStateChanged?()
                        }
                    } label: {
                        if isWatched {
                            Label("Mark as Unwatched", systemImage: "eye.slash")
                        } else {
                            Label("Mark as Watched", systemImage: "checkmark.circle")
                        }
                    }
                }
            }
    }
}

extension View {
    func videoContextMenu<T: VideoContextMenuData>(
        for video: T,
        showAddToCollection: Bool = true,
        showSave: Bool = true,
        showWatchToggle: Bool = false,
        handler: VideoContextMenuHandler,
        apiClient: APIClient,
        onWatchStateChanged: (() -> Void)? = nil
    ) -> some View {
        modifier(VideoCardContextMenu(
            video: video,
            showAddToCollection: showAddToCollection,
            showSave: showSave,
            showWatchToggle: showWatchToggle,
            handler: handler,
            apiClient: apiClient,
            onWatchStateChanged: onWatchStateChanged
        ))
    }
}

// MARK: - Collection Item Context Menu (different actions)

struct CollectionItemContextMenu: ViewModifier {
    let item: CollectionItem
    let collectionId: Int
    let handler: VideoContextMenuHandler
    let apiClient: APIClient
    var onRemoved: (() -> Void)?

    func body(content: Content) -> some View {
        content
            .contextMenu {
                Button {
                    handler.prepareAddToCollection(item)
                } label: {
                    Label("Add to Another Collection", systemImage: "plus.rectangle.on.folder")
                }

                Button(role: .destructive) {
                    Task {
                        await removeFromCollection()
                    }
                } label: {
                    Label("Remove from Collection", systemImage: "trash")
                }
            }
    }

    private func removeFromCollection() async {
        do {
            try await apiClient.removeItemFromCollection(collectionId: collectionId, itemId: item.id)
            handler.successMessage = "Removed from collection"
            handler.showSuccessToast = true
            onRemoved?()
        } catch {
            handler.errorMessage = "Failed to remove"
            handler.showErrorToast = true
        }
    }
}

extension View {
    func collectionItemContextMenu(
        for item: CollectionItem,
        collectionId: Int,
        handler: VideoContextMenuHandler,
        apiClient: APIClient,
        onRemoved: (() -> Void)? = nil
    ) -> some View {
        modifier(CollectionItemContextMenu(
            item: item,
            collectionId: collectionId,
            handler: handler,
            apiClient: apiClient,
            onRemoved: onRemoved
        ))
    }
}
