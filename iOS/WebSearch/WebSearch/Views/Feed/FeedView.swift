import SwiftUI

struct FeedView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var playerService = PlayerService.shared
    @StateObject private var navigationState = NavigationState.shared
    @Binding var selectedTab: Int

    @State private var feedItems: [FeedItem] = []
    @State private var isLoading = false
    @State private var error: String?

    // Filters
    @State private var selectedMode: FeedMode = .newest
    @State private var watchFilter: WatchFilter = .unwatched
    @State private var selectedPlatform: String?
    @State private var showFilters = false

    // Pagination
    @State private var currentPage = 1
    @State private var hasMore = true

    // View mode
    @State private var showByChannel = false

    // Channel grouped data
    @State private var channelGroups: [ChannelFeedGroup] = []

    private func navigateToChannel(_ channelName: String) {
        navigationState.searchChannel(channelName)
        selectedTab = 2 // Discover tab
    }

    var body: some View {
        NavigationStack {
            Group {
                if showByChannel {
                    channelGroupedList
                } else {
                    chronologicalList
                }
            }
            .navigationTitle("Feed")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        Button {
                            showByChannel = false
                        } label: {
                            Label("Chronological", systemImage: showByChannel ? "" : "checkmark")
                        }

                        Button {
                            showByChannel = true
                        } label: {
                            Label("By Channel", systemImage: showByChannel ? "checkmark" : "")
                        }
                    } label: {
                        Image(systemName: showByChannel ? "rectangle.stack" : "list.bullet")
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showFilters = true
                    } label: {
                        Image(systemName: "line.3.horizontal.decrease.circle")
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await syncFeed() }
                    } label: {
                        Image(systemName: "arrow.triangle.2.circlepath")
                    }
                }
            }
            .refreshable {
                await loadFeed(refresh: true)
            }
            .sheet(isPresented: $showFilters) {
                FeedFilterSheet(
                    selectedMode: $selectedMode,
                    watchFilter: $watchFilter,
                    selectedPlatform: $selectedPlatform,
                    onApply: {
                        showFilters = false
                        Task { await loadFeed(refresh: true) }
                    }
                )
            }
            .task {
                if showByChannel {
                    await loadByChannel()
                } else {
                    await loadFeed()
                }
            }
            .onChange(of: showByChannel) { _, newValue in
                Task {
                    if newValue {
                        await loadByChannel()
                    } else {
                        await loadFeed(refresh: true)
                    }
                }
            }
        }
    }

    // MARK: - Chronological List

    private var chronologicalList: some View {
        Group {
            if feedItems.isEmpty && !isLoading {
                ContentUnavailableView(
                    "No Videos",
                    systemImage: "play.rectangle",
                    description: Text("Subscribe to channels to see videos in your feed")
                )
            } else {
                List {
                    ForEach(feedItems) { item in
                        FeedItemRow(item: item, onToggleWatched: {
                            Task { await toggleWatched(item) }
                        }, onChannelTap: {
                            if let channelName = item.channelName {
                                navigateToChannel(channelName)
                            }
                        })
                        .swipeActions(edge: .trailing) {
                            Button {
                                Task { await toggleWatched(item) }
                            } label: {
                                Label(
                                    item.isWatched ? "Unwatched" : "Watched",
                                    systemImage: item.isWatched ? "eye.slash" : "eye"
                                )
                            }
                            .tint(item.isWatched ? .orange : .green)
                        }
                        .swipeActions(edge: .leading) {
                            Button {
                                Task { await saveVideo(item) }
                            } label: {
                                Label("Save", systemImage: "bookmark")
                            }
                            .tint(.blue)
                        }
                    }

                    if hasMore && !feedItems.isEmpty {
                        Button("Load More") {
                            Task { await loadMore() }
                        }
                        .frame(maxWidth: .infinity)
                    }

                    if isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
    }

    // MARK: - Channel Grouped List

    private var channelGroupedList: some View {
        Group {
            if channelGroups.isEmpty && !isLoading {
                ContentUnavailableView(
                    "No Videos",
                    systemImage: "play.rectangle",
                    description: Text("Subscribe to channels to see videos in your feed")
                )
            } else {
                List {
                    ForEach(channelGroups) { group in
                        Section {
                            ForEach(group.items.prefix(5)) { item in
                                FeedItemRow(item: item, compact: true, onToggleWatched: {
                                    Task { await toggleWatched(item) }
                                }, onChannelTap: {
                                    navigateToChannel(group.channel.name)
                                })
                            }
                        } header: {
                            HStack {
                                if let avatarUrl = group.channel.avatarUrl, let url = URL(string: avatarUrl) {
                                    AsyncImage(url: url) { image in
                                        image.resizable()
                                    } placeholder: {
                                        Circle().fill(Color.gray.opacity(0.3))
                                    }
                                    .frame(width: 24, height: 24)
                                    .clipShape(Circle())
                                }

                                Text(group.channel.name)
                                    .font(.headline)

                                Spacer()

                                if group.totalUnwatched > 0 {
                                    Text("\(group.totalUnwatched) new")
                                        .font(.caption)
                                        .foregroundStyle(.blue)
                                }
                            }
                        }
                    }

                    if isLoading {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                    }
                }
                .listStyle(.insetGrouped)
            }
        }
    }

    // MARK: - Actions

    private func loadFeed(refresh: Bool = false) async {
        if refresh {
            currentPage = 1
            hasMore = true
        }

        guard !isLoading else { return }
        isLoading = true
        error = nil

        do {
            let response = try await apiClient.getFeed(
                platform: selectedPlatform,
                watched: watchFilter,
                mode: selectedMode,
                page: currentPage,
                perPage: 20
            )

            if refresh {
                feedItems = response.items
            } else {
                feedItems.append(contentsOf: response.items)
            }

            hasMore = response.hasMore
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func loadMore() async {
        currentPage += 1
        await loadFeed()
    }

    private func loadByChannel() async {
        isLoading = true
        error = nil

        do {
            let response = try await apiClient.getFeedByChannel()
            channelGroups = response.channels
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func toggleWatched(_ item: FeedItem) async {
        do {
            if item.isWatched {
                _ = try await apiClient.markUnwatched(itemId: item.id)
            } else {
                _ = try await apiClient.markWatched(itemId: item.id)
            }

            // Update local state
            if let index = feedItems.firstIndex(where: { $0.id == item.id }) {
                // Reload to get updated state
                await loadFeed(refresh: true)
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func saveVideo(_ item: FeedItem) async {
        do {
            _ = try await apiClient.saveVideoFromUrl(url: item.videoUrl)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func syncFeed() async {
        do {
            _ = try await apiClient.syncFeed()
            await loadFeed(refresh: true)
        } catch {
            self.error = error.localizedDescription
        }
    }
}

#Preview {
    FeedView(selectedTab: .constant(0))
        .environmentObject(APIClient())
}
