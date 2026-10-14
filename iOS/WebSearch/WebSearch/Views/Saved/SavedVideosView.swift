import SwiftUI

struct SavedVideosView: View {
    @EnvironmentObject var apiClient: APIClient
    @EnvironmentObject var navigationState: NavigationState
    @StateObject private var playerService = PlayerService.shared
    @Binding var selectedTab: Int

    @State private var savedVideos: [SavedVideo] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var watchFilter: WatchFilter = .all
    @State private var selectedPlatform: String?
    @State private var showAddByUrl = false
    @State private var urlToAdd = ""

    let platforms = ["youtube", "rumble", "odysee", "podcast", "redbar"]

    private func navigateToChannel(_ channelName: String) {
        navigationState.searchChannel(channelName)
        selectedTab = 2 // Discover tab
    }

    var filteredVideos: [SavedVideo] {
        var filtered = savedVideos

        if let platform = selectedPlatform {
            filtered = filtered.filter { $0.platform.lowercased() == platform }
        }

        switch watchFilter {
        case .watched:
            filtered = filtered.filter { $0.isWatched }
        case .unwatched:
            filtered = filtered.filter { !$0.isWatched }
        case .all:
            break
        }

        return filtered
    }

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && savedVideos.isEmpty {
                    ProgressView("Loading saved videos...")
                } else if savedVideos.isEmpty {
                    ContentUnavailableView(
                        "No Saved Videos",
                        systemImage: "bookmark",
                        description: Text("Save videos from Discover or your Feed to watch later")
                    )
                } else {
                    VStack(spacing: 0) {
                        // Filters
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                // Watch filter
                                Menu {
                                    ForEach(WatchFilter.allCases, id: \.self) { filter in
                                        Button {
                                            watchFilter = filter
                                        } label: {
                                            Label(filter.displayName, systemImage: watchFilter == filter ? "checkmark" : "")
                                        }
                                    }
                                } label: {
                                    HStack(spacing: 4) {
                                        Text(watchFilter.displayName)
                                        Image(systemName: "chevron.down")
                                            .font(.caption2)
                                    }
                                    .font(.subheadline)
                                    .padding(.horizontal, 12)
                                    .padding(.vertical, 6)
                                    .background(Color(.systemGray5))
                                    .clipShape(Capsule())
                                }

                                // Platform filter
                                FilterChip(title: "All", isSelected: selectedPlatform == nil) {
                                    selectedPlatform = nil
                                }

                                ForEach(platforms, id: \.self) { platform in
                                    let count = savedVideos.filter { $0.platform.lowercased() == platform }.count
                                    if count > 0 {
                                        FilterChip(
                                            title: platform.capitalized,
                                            isSelected: selectedPlatform == platform
                                        ) {
                                            selectedPlatform = platform
                                        }
                                    }
                                }
                            }
                            .padding(.horizontal)
                            .padding(.vertical, 8)
                        }

                        // List
                        List {
                            ForEach(filteredVideos) { video in
                                SavedVideoRow(video: video, onPlay: {
                                    playVideo(video)
                                }, onChannelTap: {
                                    if let channelName = video.channelName {
                                        navigateToChannel(channelName)
                                    }
                                })
                                .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                    Button(role: .destructive) {
                                        deleteVideo(video)
                                    } label: {
                                        Label("Delete", systemImage: "trash")
                                    }
                                }
                                .swipeActions(edge: .leading) {
                                    Button {
                                        toggleWatched(video)
                                    } label: {
                                        Label(
                                            video.isWatched ? "Unwatched" : "Watched",
                                            systemImage: video.isWatched ? "eye.slash" : "eye"
                                        )
                                    }
                                    .tint(video.isWatched ? .orange : .green)
                                }
                            }
                        }
                        .listStyle(.plain)
                    }
                }
            }
            .navigationTitle("Saved")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showAddByUrl = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .refreshable {
                await loadSavedVideos()
            }
            .alert("Save Video", isPresented: $showAddByUrl) {
                TextField("Video URL", text: $urlToAdd)
                    .autocapitalization(.none)
                Button("Cancel", role: .cancel) {
                    urlToAdd = ""
                }
                Button("Save") {
                    saveVideoFromUrl()
                }
            } message: {
                Text("Enter a video URL to save")
            }
            .task {
                await loadSavedVideos()
            }
        }
    }

    // MARK: - Actions

    private func loadSavedVideos() async {
        isLoading = true
        error = nil

        do {
            savedVideos = try await apiClient.getSavedVideos()
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func playVideo(_ video: SavedVideo) {
        guard let feedItem = video.toFeedItem() else { return }
        playerService.play(video: feedItem)
    }

    private func deleteVideo(_ video: SavedVideo) {
        Task {
            do {
                try await apiClient.deleteSavedVideo(id: video.id)
                savedVideos.removeAll { $0.id == video.id }
            } catch {
                self.error = error.localizedDescription
            }
        }
    }

    private func toggleWatched(_ video: SavedVideo) {
        Task {
            do {
                _ = try await apiClient.markSavedVideoWatched(id: video.id, watched: !video.isWatched)
                await loadSavedVideos()
            } catch {
                self.error = error.localizedDescription
            }
        }
    }

    private func saveVideoFromUrl() {
        let url = urlToAdd.trimmingCharacters(in: .whitespaces)
        guard !url.isEmpty else { return }

        Task {
            do {
                let video = try await apiClient.saveVideoFromUrl(url: url)
                savedVideos.insert(video, at: 0)
            } catch {
                self.error = error.localizedDescription
            }
            urlToAdd = ""
        }
    }
}

struct SavedVideoRow: View {
    let video: SavedVideo
    let onPlay: () -> Void
    var onChannelTap: (() -> Void)? = nil

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

                    // Watch progress
                    if let progress = video.watchProgressSeconds,
                       let duration = video.durationSeconds,
                       duration > 0 && progress > 0 && !video.isWatched {
                        GeometryReader { geo in
                            VStack {
                                Spacer()
                                Rectangle()
                                    .fill(.red)
                                    .frame(width: geo.size.width * (Double(progress) / Double(duration)), height: 3)
                            }
                        }
                    }
                }

                // Info
                VStack(alignment: .leading, spacing: 4) {
                    Text(video.title)
                        .font(.headline)
                        .lineLimit(2)
                        .foregroundStyle(.primary)

                    if let channelName = video.channelName {
                        if let onChannelTap = onChannelTap {
                            Button {
                                onChannelTap()
                            } label: {
                                Text(channelName)
                                    .font(.subheadline)
                                    .foregroundStyle(.blue)
                                    .lineLimit(1)
                            }
                            .buttonStyle(.plain)
                        } else {
                            Text(channelName)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }

                    HStack(spacing: 8) {
                        PlatformBadge(platform: video.platform)

                        if let savedAt = video.savedAt {
                            Text("Saved \(formatRelativeDate(savedAt))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    if video.isWatched {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.caption2)
                            Text("Watched")
                                .font(.caption2)
                        }
                        .foregroundStyle(.green)
                    }

                    if let notes = video.notes, !notes.isEmpty {
                        Text(notes)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                            .italic()
                    }
                }

                Spacer()
            }
        }
        .buttonStyle(.plain)
        .padding(.vertical, 8)
        .opacity(video.isWatched ? 0.7 : 1.0)
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
    SavedVideosView(selectedTab: .constant(4))
        .environmentObject(APIClient())
        .environmentObject(NavigationState.shared)
}
