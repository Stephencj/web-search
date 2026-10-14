import SwiftUI
import SwiftData

struct FeedView: View {
    @Environment(\.modelContext) private var modelContext
    @StateObject private var viewModel = FeedViewModel()
    @StateObject private var playerService = PlayerService.shared

    @State private var showingFilterSheet = false

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.isLoading && viewModel.feedItems.isEmpty {
                    loadingView
                } else if viewModel.feedItems.isEmpty {
                    emptyView
                } else {
                    feedList
                }
            }
            .navigationTitle("Feed")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    modeMenu
                }
                ToolbarItem(placement: .topBarTrailing) {
                    filterButton
                }
            }
            .sheet(isPresented: $showingFilterSheet) {
                filterSheet
            }
            .refreshable {
                await viewModel.refresh()
            }
        }
        .task {
            await viewModel.loadFeed()
        }
    }

    // MARK: - Feed List
    private var feedList: some View {
        List {
            ForEach(viewModel.feedItems, id: \.id) { item in
                FeedItemRow(item: item) {
                    playerService.play(video: item)
                }
                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                    Button {
                        viewModel.toggleWatched(item)
                    } label: {
                        Label(
                            item.isWatched ? "Unwatched" : "Watched",
                            systemImage: item.isWatched ? "eye.slash" : "eye"
                        )
                    }
                    .tint(item.isWatched ? .orange : .green)
                }
                .swipeActions(edge: .leading, allowsFullSwipe: true) {
                    Button {
                        viewModel.saveVideo(item)
                    } label: {
                        Label("Save", systemImage: "bookmark")
                    }
                    .tint(.blue)
                }
                .onAppear {
                    // Load more when reaching near the end
                    if item.id == viewModel.feedItems.last?.id {
                        Task {
                            await viewModel.loadMore()
                        }
                    }
                }
            }

            // Loading more indicator
            if viewModel.isLoadingMore {
                HStack {
                    Spacer()
                    ProgressView()
                        .padding()
                    Spacer()
                }
                .listRowSeparator(.hidden)
            }
        }
        .listStyle(.plain)
    }

    // MARK: - Mode Menu
    private var modeMenu: some View {
        Menu {
            ForEach(FeedMode.allCases) { mode in
                Button {
                    viewModel.setMode(mode)
                } label: {
                    HStack {
                        Text(mode.rawValue)
                        if viewModel.selectedMode == mode {
                            Image(systemName: "checkmark")
                        }
                    }
                }
            }
        } label: {
            HStack(spacing: 4) {
                Text(viewModel.selectedMode.rawValue)
                    .fontWeight(.medium)
                Image(systemName: "chevron.down")
                    .font(.caption)
            }
        }
    }

    // MARK: - Filter Button
    private var filterButton: some View {
        Button {
            showingFilterSheet = true
        } label: {
            Image(systemName: hasActiveFilters ? "line.3.horizontal.decrease.circle.fill" : "line.3.horizontal.decrease.circle")
        }
    }

    private var hasActiveFilters: Bool {
        viewModel.selectedFilter != .all || viewModel.selectedPlatform != .all
    }

    // MARK: - Filter Sheet
    private var filterSheet: some View {
        NavigationStack {
            List {
                Section("Status") {
                    ForEach(FeedFilter.allCases) { filter in
                        Button {
                            viewModel.setFilter(filter)
                        } label: {
                            HStack {
                                Text(filter.rawValue)
                                    .foregroundStyle(.primary)
                                Spacer()
                                if viewModel.selectedFilter == filter {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.tint)
                                }
                            }
                        }
                    }
                }

                Section("Platform") {
                    ForEach(Platform.allCases) { platform in
                        Button {
                            viewModel.setPlatform(platform)
                        } label: {
                            HStack {
                                Text(platform.rawValue)
                                    .foregroundStyle(.primary)
                                Spacer()
                                if viewModel.selectedPlatform == platform {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.tint)
                                }
                            }
                        }
                    }
                }

                if hasActiveFilters {
                    Section {
                        Button("Clear All Filters", role: .destructive) {
                            viewModel.setFilter(.all)
                            viewModel.setPlatform(.all)
                        }
                    }
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        showingFilterSheet = false
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }

    // MARK: - Loading View
    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
            Text("Loading feed...")
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - Empty View
    private var emptyView: some View {
        ContentUnavailableView {
            Label("No Videos", systemImage: "play.rectangle.on.rectangle")
        } description: {
            Text("Your feed is empty. Subscribe to some channels to get started.")
        } actions: {
            Button("Refresh") {
                Task {
                    await viewModel.refresh()
                }
            }
            .buttonStyle(.bordered)
        }
    }
}

#Preview {
    FeedView()
}
