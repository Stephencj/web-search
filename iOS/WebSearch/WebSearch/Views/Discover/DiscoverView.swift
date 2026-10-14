import SwiftUI

struct DiscoverView: View {
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var navigationState: NavigationState
    @StateObject private var playerService = PlayerService.shared

    @State private var searchQuery = ""
    @State private var searchType = "videos" // videos, channels
    @State private var videoResults: [DiscoverVideoResult] = []
    @State private var channelResults: [ChannelSearchResult] = []
    @State private var platforms: [Platform] = []
    @State private var selectedPlatforms: Set<String> = []
    @State private var isSearching = false
    @State private var error: String?
    @State private var hasSearched = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Search type picker
                Picker("Search Type", selection: $searchType) {
                    Text("Videos").tag("videos")
                    Text("Channels").tag("channels")
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.top, 8)

                // Platform filter chips
                if !platforms.isEmpty {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack(spacing: 8) {
                            FilterChip(title: "All", isSelected: selectedPlatforms.isEmpty) {
                                selectedPlatforms.removeAll()
                            }

                            ForEach(platforms.filter { $0.supportsSearch }) { platform in
                                FilterChip(
                                    title: platform.name,
                                    isSelected: selectedPlatforms.contains(platform.platformId)
                                ) {
                                    if selectedPlatforms.contains(platform.platformId) {
                                        selectedPlatforms.remove(platform.platformId)
                                    } else {
                                        selectedPlatforms.insert(platform.platformId)
                                    }
                                }
                            }
                        }
                        .padding(.horizontal)
                        .padding(.vertical, 8)
                    }
                }

                // Results
                Group {
                    if isSearching {
                        VStack {
                            Spacer()
                            ProgressView("Searching...")
                            Spacer()
                        }
                    } else if !hasSearched {
                        ContentUnavailableView(
                            "Discover Content",
                            systemImage: "magnifyingglass",
                            description: Text("Search for videos and channels across multiple platforms")
                        )
                    } else if searchType == "videos" {
                        videoResultsList
                    } else {
                        channelResultsList
                    }
                }
            }
            .navigationTitle("Discover")
            .searchable(text: $searchQuery, prompt: "Search videos or channels...")
            .onSubmit(of: .search) {
                performSearch()
            }
            .task {
                await loadPlatforms()
            }
            .onChange(of: navigationState.discoverChannelName) { _, channelName in
                if let channelName = channelName {
                    searchQuery = channelName
                    searchType = "channels"
                    performSearch()
                    navigationState.clearChannelSearch()
                }
            }
            .onAppear {
                // Handle initial navigation with channel name
                if let channelName = navigationState.discoverChannelName {
                    searchQuery = channelName
                    searchType = "channels"
                    performSearch()
                    navigationState.clearChannelSearch()
                }
            }
        }
    }

    // MARK: - Video Results

    private var videoResultsList: some View {
        Group {
            if videoResults.isEmpty {
                ContentUnavailableView(
                    "No Videos Found",
                    systemImage: "play.slash",
                    description: Text("No videos found for \"\(searchQuery)\"")
                )
            } else {
                List {
                    ForEach(videoResults) { video in
                        DiscoverVideoRow(video: video) {
                            if let feedItem = video.toFeedItem() {
                                playerService.play(video: feedItem)
                            }
                        }
                        .swipeActions(edge: .leading) {
                            Button {
                                saveVideo(video)
                            } label: {
                                Label("Save", systemImage: "bookmark")
                            }
                            .tint(.blue)
                        }
                        .swipeActions(edge: .trailing) {
                            if let channelUrl = video.channelUrl {
                                Button {
                                    subscribeToChannel(channelUrl)
                                } label: {
                                    Label("Subscribe", systemImage: "plus.circle")
                                }
                                .tint(.green)
                            }
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
    }

    // MARK: - Channel Results

    private var channelResultsList: some View {
        Group {
            if channelResults.isEmpty {
                ContentUnavailableView(
                    "No Channels Found",
                    systemImage: "person.slash",
                    description: Text("No channels found for \"\(searchQuery)\"")
                )
            } else {
                List {
                    ForEach(channelResults) { channel in
                        DiscoverChannelRow(channel: channel) {
                            subscribeToChannel(channel.channelUrl)
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
    }

    // MARK: - Actions

    private func loadPlatforms() async {
        do {
            platforms = try await apiClient.getPlatforms()
        } catch {
            print("Failed to load platforms: \(error)")
        }
    }

    private func performSearch() {
        let query = searchQuery.trimmingCharacters(in: .whitespaces)
        guard !query.isEmpty else { return }

        isSearching = true
        hasSearched = true
        error = nil

        let platformFilter = selectedPlatforms.isEmpty ? nil : Array(selectedPlatforms)

        Task {
            do {
                if searchType == "videos" {
                    let response = try await apiClient.searchVideos(
                        query: query,
                        platforms: platformFilter,
                        maxResults: 30
                    )
                    videoResults = response.videos ?? []
                } else {
                    let response = try await apiClient.searchDiscoverChannels(
                        query: query,
                        platforms: platformFilter
                    )
                    channelResults = response.channels ?? []
                }
            } catch {
                self.error = error.localizedDescription
            }
            isSearching = false
        }
    }

    private func saveVideo(_ video: DiscoverVideoResult) {
        Task {
            do {
                _ = try await apiClient.saveVideoFromUrl(url: video.videoUrl)
            } catch {
                self.error = error.localizedDescription
            }
        }
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

struct DiscoverVideoRow: View {
    let video: DiscoverVideoResult
    let onPlay: () -> Void

    var body: some View {
        Button(action: onPlay) {
            HStack(alignment: .top, spacing: 12) {
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
                                        .foregroundStyle(.secondary)
                                }
                        }
                    }
                    .frame(width: 140, height: 79)
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                    if let duration = video.durationSeconds {
                        Text(formatDuration(duration))
                            .font(.caption2)
                            .fontWeight(.medium)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 2)
                            .background(.black.opacity(0.7))
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .padding(4)
                    }
                }

                // Info
                VStack(alignment: .leading, spacing: 4) {
                    Text(video.title)
                        .font(.headline)
                        .lineLimit(2)
                        .foregroundStyle(.primary)

                    if let channelName = video.channelName {
                        Text(channelName)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }

                    HStack(spacing: 8) {
                        PlatformBadge(platform: video.platform)

                        if let views = video.viewCount {
                            Text(formatViews(views))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Spacer()
            }
        }
        .buttonStyle(.plain)
        .padding(.vertical, 8)
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

struct DiscoverChannelRow: View {
    let channel: ChannelSearchResult
    let onSubscribe: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            AsyncImage(url: URL(string: channel.avatarUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().aspectRatio(contentMode: .fill)
                default:
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .overlay {
                            Text(String(channel.name.prefix(1)).uppercased())
                                .font(.headline)
                                .foregroundStyle(.secondary)
                        }
                }
            }
            .frame(width: 50, height: 50)
            .clipShape(Circle())

            VStack(alignment: .leading, spacing: 4) {
                Text(channel.name)
                    .font(.headline)
                    .lineLimit(1)

                HStack(spacing: 8) {
                    PlatformBadge(platform: channel.platform)

                    if let subscribers = channel.subscriberCount {
                        Text(formatCount(subscribers) + " subscribers")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                if let description = channel.description, !description.isEmpty {
                    Text(description)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }

            Spacer()

            Button("Subscribe", action: onSubscribe)
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
        }
        .padding(.vertical, 4)
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
    DiscoverView()
        .environmentObject(APIClient())
}
