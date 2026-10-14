import SwiftUI

struct TVDiscoverView: View {
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var navigationState: TVNavigationState
    @StateObject private var contextMenuHandler = VideoContextMenuHandler()

    @State private var searchQuery = ""
    @State private var searchType = "videos"
    @State private var videoResults: [DiscoverVideoResult] = []
    @State private var channelResults: [ChannelSearchResult] = []
    @State private var isSearching = false
    @State private var hasSearched = false
    @State private var error: String?
    @State private var selectedVideo: FeedItem?
    @State private var showPlayer = false

    private let columns = [
        GridItem(.adaptive(minimum: 400, maximum: 450), spacing: 40)
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search bar with button (tvOS doesn't handle .searchable well)
                HStack(spacing: 20) {
                    TextField("Search videos or channels...", text: $searchQuery)
                        .textFieldStyle(.plain)
                        .padding()
                        .background(Color.secondary.opacity(0.2))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                        .onSubmit {
                            performSearch()
                        }

                    Button("Search") {
                        performSearch()
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(searchQuery.trimmingCharacters(in: .whitespaces).isEmpty)
                }
                .padding(.horizontal, 80)
                .padding(.top, 30)

                // Search type picker
                Picker("Search Type", selection: $searchType) {
                    Text("Videos").tag("videos")
                    Text("Channels").tag("channels")
                }
                .pickerStyle(.segmented)
                .padding(.horizontal, 100)
                .padding(.top, 20)

                // Results
                ScrollView {
                    if isSearching {
                        ProgressView("Searching...")
                            .padding(.top, 100)
                    } else if let error = error {
                        ContentUnavailableView(
                            "Search Error",
                            systemImage: "exclamationmark.triangle",
                            description: Text(error)
                        )
                        .padding(.top, 100)
                    } else if !hasSearched {
                        ContentUnavailableView(
                            "Discover Content",
                            systemImage: "magnifyingglass",
                            description: Text("Type a search term and press Search")
                        )
                        .padding(.top, 100)
                    } else if searchType == "videos" {
                        videoResultsGrid
                    } else {
                        channelResultsGrid
                    }
                }
            }
            .navigationTitle("Discover")
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
            .onAppear {
                // Check if navigated from Channels with a channel name
                if let channelName = navigationState.searchChannelName {
                    searchQuery = channelName
                    navigationState.clearChannelSearch()
                    performSearch()
                }
            }
        }
        .toastOverlay(handler: contextMenuHandler)
        .task {
            await contextMenuHandler.loadCollections(using: apiClient)
        }
    }

    // MARK: - Video Results

    private var videoResultsGrid: some View {
        Group {
            if videoResults.isEmpty {
                ContentUnavailableView(
                    "No Videos Found",
                    systemImage: "play.slash",
                    description: Text("No videos found for \"\(searchQuery)\"")
                )
                .padding(.top, 100)
            } else {
                LazyVGrid(columns: columns, spacing: 40) {
                    ForEach(videoResults) { video in
                        TVDiscoverVideoCard(video: video) {
                            playVideo(video)
                        }
                        .videoContextMenu(
                            for: video,
                            showAddToCollection: true,
                            showSave: true,
                            showWatchToggle: false,
                            handler: contextMenuHandler,
                            apiClient: apiClient
                        )
                    }
                }
                .padding(60)
            }
        }
    }

    // MARK: - Channel Results

    private var channelResultsGrid: some View {
        Group {
            if channelResults.isEmpty {
                ContentUnavailableView(
                    "No Channels Found",
                    systemImage: "person.slash",
                    description: Text("No channels found for \"\(searchQuery)\"")
                )
                .padding(.top, 100)
            } else {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 300, maximum: 350), spacing: 40)], spacing: 40) {
                    ForEach(channelResults) { channel in
                        TVDiscoverChannelCard(channel: channel) {
                            subscribeToChannel(channel.channelUrl)
                        }
                    }
                }
                .padding(60)
            }
        }
    }

    // MARK: - Actions

    private func performSearch() {
        let query = searchQuery.trimmingCharacters(in: .whitespaces)
        guard !query.isEmpty else { return }

        isSearching = true
        hasSearched = true
        error = nil

        Task {
            do {
                if searchType == "videos" {
                    let response = try await apiClient.searchVideos(
                        query: query,
                        platforms: nil,
                        maxResults: 30
                    )
                    videoResults = response.videos ?? []
                } else {
                    let response = try await apiClient.searchDiscoverChannels(
                        query: query,
                        platforms: nil
                    )
                    channelResults = response.channels ?? []
                }
            } catch {
                self.error = error.localizedDescription
            }
            isSearching = false
        }
    }

    private func playVideo(_ video: DiscoverVideoResult) {
        guard let feedItem = video.toFeedItem() else { return }
        selectedVideo = feedItem
        showPlayer = true
    }

    private func subscribeToChannel(_ url: String) {
        Task {
            do {
                _ = try await apiClient.addChannel(url: url)
            } catch {
                self.error = error.localizedDescription
            }
        }
    }
}

// MARK: - Discover Video Card

struct TVDiscoverVideoCard: View {
    let video: DiscoverVideoResult
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

                    if let duration = video.durationSeconds {
                        Text(formatDuration(duration))
                            .font(.caption)
                            .fontWeight(.semibold)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.black.opacity(0.7))
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .padding(8)
                    }
                }

                // Title
                Text(video.title)
                    .font(.headline)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .frame(width: 400, alignment: .leading)

                // Channel and metadata
                if let channelName = video.channelName {
                    Text(channelName)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                HStack(spacing: 12) {
                    TVPlatformBadge(platform: video.platform)

                    if let views = video.viewCount {
                        Text(formatViews(views))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .buttonStyle(.plain)
        .scaleEffect(isFocused ? 1.05 : 1.0)
        .shadow(radius: isFocused ? 20 : 5)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }

    private func formatDuration(_ seconds: Int) -> String {
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let secs = seconds % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        }
        return String(format: "%d:%02d", minutes, secs)
    }

    private func formatViews(_ views: Int) -> String {
        if views >= 1_000_000 {
            return String(format: "%.1fM views", Double(views) / 1_000_000)
        } else if views >= 1_000 {
            return String(format: "%.1fK views", Double(views) / 1_000)
        }
        return "\(views) views"
    }
}

// MARK: - Discover Channel Card

struct TVDiscoverChannelCard: View {
    let channel: ChannelSearchResult
    let onSubscribe: () -> Void

    @FocusState private var isFocused: Bool
    @State private var isSubscribed = false

    var body: some View {
        VStack(spacing: 16) {
            // Avatar
            AsyncImage(url: URL(string: channel.avatarUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().aspectRatio(contentMode: .fill)
                default:
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .overlay {
                            Text(String(channel.name.prefix(1)).uppercased())
                                .font(.largeTitle)
                                .fontWeight(.bold)
                                .foregroundStyle(.secondary)
                        }
                }
            }
            .frame(width: 100, height: 100)
            .clipShape(Circle())

            // Name
            Text(channel.name)
                .font(.headline)
                .lineLimit(1)

            // Metadata
            HStack(spacing: 12) {
                TVPlatformBadge(platform: channel.platform)

                if let subscribers = channel.subscriberCount {
                    Text(formatCount(subscribers) + " subs")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            // Subscribe button
            Button {
                onSubscribe()
                isSubscribed = true
            } label: {
                Text(isSubscribed ? "Subscribed" : "Subscribe")
            }
            .buttonStyle(.borderedProminent)
            .disabled(isSubscribed)
        }
        .padding(24)
        .background(isFocused ? Color.blue.opacity(0.2) : Color.secondary.opacity(0.1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .scaleEffect(isFocused ? 1.05 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }

    private func formatCount(_ count: Int) -> String {
        if count >= 1_000_000 {
            return String(format: "%.1fM", Double(count) / 1_000_000)
        } else if count >= 1_000 {
            return String(format: "%.1fK", Double(count) / 1_000)
        }
        return "\(count)"
    }
}

#Preview {
    TVDiscoverView()
        .environmentObject(APIClient())
        .environmentObject(TVNavigationState.shared)
}
