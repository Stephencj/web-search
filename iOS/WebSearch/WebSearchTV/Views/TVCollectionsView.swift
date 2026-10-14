import SwiftUI

struct TVCollectionsView: View {
    @EnvironmentObject var apiClient: APIClient

    @State private var collections: [Collection] = []
    @State private var historyCount: Int = 0
    @State private var savedVideosCount: Int = 0
    @State private var isLoading = false
    @State private var error: String?

    // Delete confirmation
    @State private var collectionToDelete: Collection?
    @State private var showDeleteConfirmation = false

    // Toast
    @State private var toastMessage: String?
    @State private var showToast = false

    private let columns = [
        GridItem(.adaptive(minimum: 350, maximum: 400), spacing: 40)
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                if isLoading && collections.isEmpty {
                    ProgressView("Loading collections...")
                        .padding(.top, 100)
                } else {
                    VStack(alignment: .leading, spacing: 40) {
                        // History section (always shown)
                        VStack(alignment: .leading, spacing: 20) {
                            Text("History")
                                .font(.title2)
                                .fontWeight(.bold)
                                .padding(.horizontal, 60)

                            NavigationLink(destination: TVHistoryView()) {
                                TVHistoryCard(itemCount: historyCount)
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal, 60)
                        }
                        .padding(.top, 40)

                        // Saved Videos section
                        VStack(alignment: .leading, spacing: 20) {
                            Text("Saved Videos")
                                .font(.title2)
                                .fontWeight(.bold)
                                .padding(.horizontal, 60)

                            NavigationLink(destination: TVSavedVideosView()) {
                                TVSavedVideosCard(itemCount: savedVideosCount)
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal, 60)
                        }

                        // Collections section
                        if !collections.isEmpty {
                            VStack(alignment: .leading, spacing: 20) {
                                Text("My Collections")
                                    .font(.title2)
                                    .fontWeight(.bold)
                                    .padding(.horizontal, 60)

                                LazyVGrid(columns: columns, spacing: 40) {
                                    ForEach(collections) { collection in
                                        NavigationLink(destination: TVCollectionDetailView(collection: collection)) {
                                            TVCollectionCard(collection: collection)
                                        }
                                        .buttonStyle(.plain)
                                        .contextMenu {
                                            Button(role: .destructive) {
                                                collectionToDelete = collection
                                                showDeleteConfirmation = true
                                            } label: {
                                                Label("Delete Collection", systemImage: "trash")
                                            }
                                        }
                                    }
                                }
                                .padding(.horizontal, 60)
                            }
                        }
                    }
                    .padding(.bottom, 60)
                }
            }
            .navigationTitle("Collections")
            .refreshable {
                await loadData()
            }
        }
        .alert("Delete Collection?", isPresented: $showDeleteConfirmation) {
            Button("Cancel", role: .cancel) {
                collectionToDelete = nil
            }
            Button("Delete", role: .destructive) {
                if let collection = collectionToDelete {
                    Task { await deleteCollection(collection) }
                }
            }
        } message: {
            if let collection = collectionToDelete {
                Text("Are you sure you want to delete \"\(collection.name)\"? This cannot be undone.")
            }
        }
        .overlay {
            if showToast, let message = toastMessage {
                VStack {
                    Spacer()
                    Text(message)
                        .font(.headline)
                        .padding(.horizontal, 24)
                        .padding(.vertical, 16)
                        .background(.black.opacity(0.8))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .padding(.bottom, 100)
                }
                .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
        }
        .task {
            await loadData()
        }
    }

    private func loadData() async {
        isLoading = true
        error = nil

        do {
            // Load collections, history count, and saved videos count in parallel
            async let collectionsTask = apiClient.getCollections()
            async let historyTask = apiClient.getFeed(watched: .watched, perPage: 1)
            async let savedVideosTask = apiClient.getSavedVideos()

            collections = try await collectionsTask
            let historyResponse = try await historyTask
            historyCount = historyResponse.total
            let savedVideos = try await savedVideosTask
            savedVideosCount = savedVideos.count
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func deleteCollection(_ collection: Collection) async {
        do {
            try await apiClient.deleteCollection(id: collection.id)
            collections.removeAll { $0.id == collection.id }
            showToastMessage("Deleted \"\(collection.name)\"")
        } catch {
            showToastMessage("Failed to delete: \(error.localizedDescription)")
        }
        collectionToDelete = nil
    }

    private func showToastMessage(_ message: String) {
        toastMessage = message
        withAnimation(.easeInOut(duration: 0.3)) {
            showToast = true
        }

        Task {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            withAnimation(.easeInOut(duration: 0.3)) {
                showToast = false
            }
        }
    }
}

// MARK: - History Card

struct TVHistoryCard: View {
    let itemCount: Int

    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 24) {
            // Icon
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.blue.opacity(0.2))
                    .frame(width: 120, height: 80)

                Image(systemName: "clock.arrow.circlepath")
                    .font(.system(size: 36))
                    .foregroundStyle(.blue)
            }

            // Info
            VStack(alignment: .leading, spacing: 8) {
                Text("Watch History")
                    .font(.headline)

                Text("\(itemCount) watched videos")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.title3)
                .foregroundStyle(.secondary)
        }
        .padding(20)
        .background(isFocused ? Color.blue.opacity(0.3) : Color.secondary.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .scaleEffect(isFocused ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }
}

// MARK: - Saved Videos Card

struct TVSavedVideosCard: View {
    let itemCount: Int

    @FocusState private var isFocused: Bool

    var body: some View {
        HStack(spacing: 24) {
            // Icon
            ZStack {
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color.green.opacity(0.2))
                    .frame(width: 120, height: 80)

                Image(systemName: "bookmark.fill")
                    .font(.system(size: 36))
                    .foregroundStyle(.green)
            }

            // Info
            VStack(alignment: .leading, spacing: 8) {
                Text("Saved Videos")
                    .font(.headline)

                Text("\(itemCount) saved videos")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.title3)
                .foregroundStyle(.secondary)
        }
        .padding(20)
        .background(isFocused ? Color.green.opacity(0.3) : Color.secondary.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .scaleEffect(isFocused ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }
}

// MARK: - History View

struct TVHistoryView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var contextMenuHandler = VideoContextMenuHandler()

    @State private var historyItems: [FeedItem] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var selectedVideo: FeedItem?
    @State private var showPlayer = false

    private let columns = [
        GridItem(.adaptive(minimum: 400, maximum: 450), spacing: 40)
    ]

    var body: some View {
        ScrollView {
            if isLoading && historyItems.isEmpty {
                ProgressView("Loading history...")
                    .padding(.top, 100)
            } else if let error = error {
                ContentUnavailableView(
                    "Error Loading History",
                    systemImage: "exclamationmark.triangle",
                    description: Text(error)
                )
                .padding(.top, 100)
            } else if historyItems.isEmpty {
                ContentUnavailableView(
                    "No Watch History",
                    systemImage: "clock",
                    description: Text("Videos you watch will appear here")
                )
                .padding(.top, 100)
            } else {
                LazyVGrid(columns: columns, spacing: 40) {
                    ForEach(historyItems) { video in
                        TVVideoCard(video: video) {
                            selectedVideo = video
                            showPlayer = true
                        }
                        .videoContextMenu(
                            for: video,
                            showAddToCollection: true,
                            showSave: true,
                            showWatchToggle: true,
                            handler: contextMenuHandler,
                            apiClient: apiClient,
                            onWatchStateChanged: {
                                Task { await loadHistory() }
                            }
                        )
                    }
                }
                .padding(60)
            }
        }
        .navigationTitle("Watch History")
        .fullScreenCover(isPresented: $showPlayer) {
            if let video = selectedVideo {
                TVVideoPlayerView(video: video, isPresented: $showPlayer)
                    .environmentObject(apiClient)
            }
        }
        .fullScreenCover(isPresented: $contextMenuHandler.showAddToCollection) {
            if let video = contextMenuHandler.videoForCollection {
                TVAddToCollectionView(
                    video: video,
                    collections: $contextMenuHandler.collections,
                    isPresented: $contextMenuHandler.showAddToCollection
                )
                .environmentObject(apiClient)
            }
        }
        .toastOverlay(handler: contextMenuHandler)
        .task {
            await loadHistory()
        }
        .task {
            await contextMenuHandler.loadCollections(using: apiClient)
        }
    }

    private func loadHistory() async {
        isLoading = true
        error = nil

        do {
            let response = try await apiClient.getFeed(
                watched: .watched,
                mode: .newest,
                perPage: 100
            )
            historyItems = response.items
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }
}

// MARK: - Collection Card

struct TVCollectionCard: View {
    let collection: Collection

    @FocusState private var isFocused: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            // Cover image or placeholder
            ZStack {
                if let coverUrl = collection.coverUrl, let url = URL(string: coverUrl) {
                    AsyncImage(url: url) { image in
                        image
                            .resizable()
                            .aspectRatio(16/9, contentMode: .fill)
                    } placeholder: {
                        collectionPlaceholder
                    }
                } else {
                    collectionPlaceholder
                }
            }
            .frame(width: 350, height: 197)
            .clipShape(RoundedRectangle(cornerRadius: 12))

            // Name
            Text(collection.name)
                .font(.headline)
                .lineLimit(1)

            // Item count
            Text("\(collection.itemCount) items")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .scaleEffect(isFocused ? 1.05 : 1.0)
        .shadow(radius: isFocused ? 20 : 5)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }

    private var collectionPlaceholder: some View {
        Rectangle()
            .fill(Color.gray.opacity(0.3))
            .overlay {
                VStack(spacing: 8) {
                    Image(systemName: "square.stack.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.secondary)
                    Text(collection.name)
                        .font(.headline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }
            }
    }
}

// MARK: - Collection Detail View

struct TVCollectionDetailView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var contextMenuHandler = VideoContextMenuHandler()
    let collection: Collection

    @State private var collectionWithItems: CollectionWithItems?
    @State private var isLoading = false
    @State private var error: String?
    @State private var selectedVideo: FeedItem?
    @State private var showPlayer = false
    @State private var playbackError: String?
    @State private var showPlaybackError = false

    private var videoItems: [CollectionItem] {
        collectionWithItems?.items.filter { $0.itemType == "video" } ?? []
    }

    private let columns = [
        GridItem(.adaptive(minimum: 400, maximum: 450), spacing: 40)
    ]

    var body: some View {
        ScrollView {
            if isLoading && collectionWithItems == nil {
                ProgressView("Loading...")
                    .padding(.top, 100)
            } else if videoItems.isEmpty {
                ContentUnavailableView(
                    "Empty Collection",
                    systemImage: "play.rectangle.on.rectangle",
                    description: Text("Add videos to this collection from the iOS app")
                )
                .padding(.top, 100)
            } else {
                LazyVGrid(columns: columns, spacing: 40) {
                    ForEach(videoItems) { item in
                        TVCollectionItemCard(item: item) {
                            playItem(item)
                        }
                        .collectionItemContextMenu(
                            for: item,
                            collectionId: collection.id,
                            handler: contextMenuHandler,
                            apiClient: apiClient,
                            onRemoved: {
                                Task { await loadCollection() }
                            }
                        )
                    }
                }
                .padding(60)
            }
        }
        .navigationTitle(collection.name)
        .fullScreenCover(isPresented: $showPlayer) {
            if let video = selectedVideo {
                TVVideoPlayerView(video: video, isPresented: $showPlayer)
                    .environmentObject(apiClient)
            }
        }
        .fullScreenCover(isPresented: $contextMenuHandler.showAddToCollection) {
            if let video = contextMenuHandler.videoForCollection {
                TVAddToCollectionView(
                    video: video,
                    collections: $contextMenuHandler.collections,
                    isPresented: $contextMenuHandler.showAddToCollection
                )
                .environmentObject(apiClient)
            }
        }
        .toastOverlay(handler: contextMenuHandler)
        .alert("Playback Error", isPresented: $showPlaybackError) {
            Button("OK", role: .cancel) { }
        } message: {
            Text(playbackError ?? "An unknown error occurred")
        }
        .task {
            await loadCollection()
        }
        .task {
            await contextMenuHandler.loadCollections(using: apiClient)
        }
    }

    private func loadCollection() async {
        isLoading = true
        error = nil

        do {
            collectionWithItems = try await apiClient.getCollection(id: collection.id)
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func playItem(_ item: CollectionItem) {
        guard let feedItem = item.toFeedItem() else {
            print("Cannot play video: unable to extract videoId from URL: \(item.url)")
            playbackError = "Unable to play this video. The video URL format is not supported."
            showPlaybackError = true
            return
        }
        selectedVideo = feedItem
        showPlayer = true
    }
}

// MARK: - Collection Item Card

struct TVCollectionItemCard: View {
    let item: CollectionItem
    let onSelect: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 12) {
                // Thumbnail
                AsyncImage(url: URL(string: item.thumbnailUrl ?? "")) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(16/9, contentMode: .fill)
                    default:
                        Rectangle()
                            .fill(Color.gray.opacity(0.3))
                            .overlay {
                                Image(systemName: "play.rectangle")
                                    .font(.largeTitle)
                                    .foregroundStyle(.secondary)
                            }
                    }
                }
                .frame(width: 400, height: 225)
                .clipShape(RoundedRectangle(cornerRadius: 12))

                // Title
                Text(item.title ?? "Untitled")
                    .font(.headline)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .frame(width: 400, alignment: .leading)

                // Domain
                if let domain = item.domain {
                    Text(domain)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .buttonStyle(.plain)
        .scaleEffect(isFocused ? 1.05 : 1.0)
        .shadow(radius: isFocused ? 20 : 5)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }
}

#Preview {
    TVCollectionsView()
        .environmentObject(APIClient())
}
