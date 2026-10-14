import SwiftUI

struct TVFeedView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var contextMenuHandler = VideoContextMenuHandler()

    @State private var feedItems: [FeedItem] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var selectedVideo: FeedItem?
    @State private var showPlayer = false

    // Filters
    @State private var selectedMode: FeedMode = .newest
    @State private var watchFilter: WatchFilter = .unwatched
    @State private var selectedPlatform: String = "all"
    @State private var platforms: [Platform] = []

    // Stats
    @State private var feedStats: FeedStats?
    @State private var isSyncing = false

    private let columns = [
        GridItem(.adaptive(minimum: 400, maximum: 450), spacing: 40)
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Stats bar
                if let stats = feedStats {
                    HStack(spacing: 30) {
                        HStack(spacing: 8) {
                            Image(systemName: "play.rectangle.fill")
                                .foregroundStyle(.blue)
                            Text("\(stats.totalVideos) videos")
                        }
                        HStack(spacing: 8) {
                            Image(systemName: "eye.slash.fill")
                                .foregroundStyle(.orange)
                            Text("\(stats.unwatchedCount) unwatched")
                        }
                        if let platformStats = stats.byPlatform, !platformStats.isEmpty {
                            ForEach(platformStats.sorted(by: { $0.key < $1.key }), id: \.key) { platform, count in
                                HStack(spacing: 4) {
                                    TVPlatformBadge(platform: platform)
                                    Text("\(count)")
                                        .font(.caption)
                                }
                            }
                        }
                        Spacer()
                    }
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 60)
                    .padding(.top, 10)
                }

                // Filter bar
                HStack(spacing: 30) {
                    // Watch filter
                    HStack(spacing: 12) {
                        Text("Show:")
                            .foregroundStyle(.secondary)
                        Picker("Watch Status", selection: $watchFilter) {
                            ForEach(WatchFilter.allCases, id: \.self) { filter in
                                Text(filter.displayName).tag(filter)
                            }
                        }
                        .pickerStyle(.menu)
                        .onChange(of: watchFilter) { _, _ in
                            Task { await loadFeed() }
                        }
                    }

                    // Platform filter
                    HStack(spacing: 12) {
                        Text("Platform:")
                            .foregroundStyle(.secondary)
                        Picker("Platform", selection: $selectedPlatform) {
                            Text("All").tag("all")
                            ForEach(platforms) { platform in
                                Text(platform.name).tag(platform.platformId)
                            }
                        }
                        .pickerStyle(.menu)
                        .onChange(of: selectedPlatform) { _, _ in
                            Task { await loadFeed() }
                        }
                    }

                    // Feed mode
                    HStack(spacing: 12) {
                        Text("Sort:")
                            .foregroundStyle(.secondary)
                        Picker("Feed Mode", selection: $selectedMode) {
                            ForEach(FeedMode.allCases, id: \.self) { mode in
                                Label(mode.displayName, systemImage: mode.icon).tag(mode)
                            }
                        }
                        .pickerStyle(.menu)
                        .onChange(of: selectedMode) { _, _ in
                            Task { await loadFeed() }
                        }
                    }

                    Spacer()

                    // Sync button
                    Button {
                        Task { await syncFeed() }
                    } label: {
                        if isSyncing {
                            ProgressView()
                                .scaleEffect(0.7)
                        } else {
                            Label("Sync", systemImage: "arrow.triangle.2.circlepath")
                        }
                    }
                    .buttonStyle(.bordered)
                    .disabled(isSyncing)

                    // Refresh button
                    Button {
                        Task { await loadFeed() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.bordered)
                }
                .padding(.horizontal, 60)
                .padding(.vertical, 20)

                // Content
                ScrollView {
                    if isLoading && feedItems.isEmpty {
                        ProgressView("Loading feed...")
                            .padding(.top, 100)
                    } else if let error = error {
                        ContentUnavailableView(
                            "Error Loading Feed",
                            systemImage: "exclamationmark.triangle",
                            description: Text(error)
                        )
                        .padding(.top, 100)
                    } else if feedItems.isEmpty {
                        ContentUnavailableView(
                            "No Videos",
                            systemImage: "play.rectangle",
                            description: Text(watchFilter == .unwatched ? "No unwatched videos" : "Subscribe to channels to see videos")
                        )
                        .padding(.top, 100)
                    } else {
                        LazyVGrid(columns: columns, spacing: 40) {
                            ForEach(feedItems) { video in
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
                                        Task { await loadFeed() }
                                    }
                                )
                            }
                        }
                        .padding(60)
                    }
                }
            }
            .navigationTitle("Feed")
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
        }
        .toastOverlay(handler: contextMenuHandler)
        .task {
            await loadFeed()
        }
        .task {
            await loadStats()
        }
        .task {
            await loadPlatforms()
        }
        .task {
            await contextMenuHandler.loadCollections(using: apiClient)
        }
    }

    private func loadFeed() async {
        isLoading = true
        error = nil

        do {
            let response = try await apiClient.getFeed(
                platform: selectedPlatform == "all" ? nil : selectedPlatform,
                watched: watchFilter,
                mode: selectedMode,
                perPage: 50
            )
            feedItems = response.items
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func loadStats() async {
        do {
            feedStats = try await apiClient.getFeedStats()
        } catch {
            print("Failed to load feed stats: \(error)")
        }
    }

    private func loadPlatforms() async {
        do {
            platforms = try await apiClient.getPlatforms()
        } catch {
            print("Failed to load platforms: \(error)")
        }
    }

    private func syncFeed() async {
        isSyncing = true
        do {
            _ = try await apiClient.syncFeed()
            // Reload feed and stats after sync
            await loadFeed()
            await loadStats()
        } catch {
            print("Failed to sync feed: \(error)")
        }
        isSyncing = false
    }
}

// MARK: - Video Card

struct TVVideoCard: View {
    let video: FeedItem
    let onSelect: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 12) {
                // Thumbnail
                ZStack(alignment: .bottomTrailing) {
                    AsyncImage(url: URL(string: video.thumbnailUrl ?? "")) { phase in
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

                    // Duration badge
                    if !video.formattedDuration.isEmpty {
                        Text(video.formattedDuration)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.black.opacity(0.7))
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .padding(8)
                    }

                    // Watch progress
                    if let progress = video.watchProgressSeconds,
                       let duration = video.durationSeconds,
                       duration > 0 && progress > 0 && !video.isWatched {
                        GeometryReader { geo in
                            VStack {
                                Spacer()
                                Rectangle()
                                    .fill(.red)
                                    .frame(width: geo.size.width * (Double(progress) / Double(duration)), height: 4)
                            }
                        }
                    }
                }

                // Title
                Text(video.title)
                    .font(.headline)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .frame(width: 400, alignment: .leading)

                // Channel name
                if let channelName = video.channelName {
                    Text(channelName)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                // Metadata
                HStack(spacing: 12) {
                    if !video.formattedViews.isEmpty {
                        Text(video.formattedViews)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }

                    if let uploadDate = video.uploadDate {
                        Text(formatRelativeDate(uploadDate))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }

                // Watched indicator
                if video.isWatched {
                    HStack(spacing: 6) {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.caption)
                        Text("Watched")
                            .font(.caption)
                    }
                    .foregroundStyle(.green)
                }
            }
            .opacity(video.isWatched ? 0.7 : 1.0)
        }
        .buttonStyle(.plain)
        .scaleEffect(isFocused ? 1.05 : 1.0)
        .shadow(radius: isFocused ? 20 : 5)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }

    private func formatRelativeDate(_ dateString: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

        var date = formatter.date(from: dateString)
        if date == nil {
            formatter.formatOptions = [.withInternetDateTime]
            date = formatter.date(from: dateString)
        }

        if let date = date {
            let relative = RelativeDateTimeFormatter()
            relative.unitsStyle = .abbreviated
            return relative.localizedString(for: date, relativeTo: Date())
        }

        return dateString
    }
}

#Preview {
    TVFeedView()
        .environmentObject(APIClient())
}
