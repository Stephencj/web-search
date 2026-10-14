import SwiftUI

struct TVSavedVideosView: View {
    @EnvironmentObject var apiClient: APIClient

    @State private var savedVideos: [SavedVideo] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var selectedVideo: FeedItem?
    @State private var showPlayer = false

    // Toast
    @State private var toastMessage: String?
    @State private var showToast = false

    // Delete confirmation
    @State private var videoToDelete: SavedVideo?
    @State private var showDeleteConfirmation = false

    private let columns = [
        GridItem(.adaptive(minimum: 400, maximum: 450), spacing: 40)
    ]

    var body: some View {
        ScrollView {
            if isLoading && savedVideos.isEmpty {
                ProgressView("Loading saved videos...")
                    .padding(.top, 100)
            } else if let error = error {
                ContentUnavailableView(
                    "Error Loading Saved Videos",
                    systemImage: "exclamationmark.triangle",
                    description: Text(error)
                )
                .padding(.top, 100)
            } else if savedVideos.isEmpty {
                ContentUnavailableView(
                    "No Saved Videos",
                    systemImage: "bookmark",
                    description: Text("Save videos from Discover to watch later")
                )
                .padding(.top, 100)
            } else {
                LazyVGrid(columns: columns, spacing: 40) {
                    ForEach(savedVideos, id: \.id) { video in
                        TVSavedVideoCard(video: video) {
                            playVideo(video)
                        }
                        .contextMenu {
                            Button {
                                Task { await toggleWatched(video) }
                            } label: {
                                Label(
                                    video.isWatched ? "Mark Unwatched" : "Mark Watched",
                                    systemImage: video.isWatched ? "eye.slash" : "eye"
                                )
                            }

                            Button(role: .destructive) {
                                videoToDelete = video
                                showDeleteConfirmation = true
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
                }
                .padding(60)
            }
        }
        .navigationTitle("Saved Videos")
        .fullScreenCover(isPresented: $showPlayer) {
            if let video = selectedVideo {
                TVVideoPlayerView(video: video, isPresented: $showPlayer)
                    .environmentObject(apiClient)
            }
        }
        .alert("Delete Saved Video?", isPresented: $showDeleteConfirmation) {
            Button("Cancel", role: .cancel) {
                videoToDelete = nil
            }
            Button("Delete", role: .destructive) {
                if let video = videoToDelete {
                    Task { await deleteVideo(video) }
                }
            }
        } message: {
            if let video = videoToDelete {
                Text("Are you sure you want to delete \"\(video.title)\"?")
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
            await loadSavedVideos()
        }
    }

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
        // Convert SavedVideo to FeedItem for the player
        let feedItem = FeedItem(
            id: video.id,
            channelId: 0,
            platform: video.platform,
            videoId: video.videoId,
            videoUrl: video.videoUrl,
            title: video.title,
            description: video.description,
            thumbnailUrl: video.thumbnailUrl,
            durationSeconds: video.durationSeconds,
            viewCount: video.viewCount,
            uploadDate: video.uploadDate,
            categories: nil,
            isWatched: video.isWatched,
            watchedAt: video.watchedAt,
            watchProgressSeconds: video.watchProgressSeconds,
            discoveredAt: nil,
            channelName: video.channelName
        )
        selectedVideo = feedItem
        showPlayer = true
    }

    private func toggleWatched(_ video: SavedVideo) async {
        do {
            _ = try await apiClient.markSavedVideoWatched(id: video.id, watched: !video.isWatched)
            showToastMessage(video.isWatched ? "Marked as unwatched" : "Marked as watched")
            await loadSavedVideos()  // Refresh the list
        } catch {
            showToastMessage("Failed: \(error.localizedDescription)")
        }
    }

    private func deleteVideo(_ video: SavedVideo) async {
        do {
            try await apiClient.deleteSavedVideo(id: video.id)
            savedVideos.removeAll { $0.id == video.id }
            showToastMessage("Deleted saved video")
        } catch {
            showToastMessage("Failed to delete: \(error.localizedDescription)")
        }
        videoToDelete = nil
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

// MARK: - Saved Video Card

struct TVSavedVideoCard: View {
    let video: SavedVideo
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
                                    Image(systemName: "bookmark.fill")
                                        .font(.largeTitle)
                                        .foregroundStyle(.secondary)
                                }
                        }
                    }
                    .frame(width: 400, height: 225)
                    .clipShape(RoundedRectangle(cornerRadius: 12))

                    // Duration badge
                    if let duration = video.durationSeconds, duration > 0 {
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

                // Platform and saved date
                HStack(spacing: 12) {
                    TVPlatformBadge(platform: video.platform)

                    if let savedAt = video.savedAt {
                        Text(formatRelativeDate(savedAt))
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

                // Notes if any
                if let notes = video.notes, !notes.isEmpty {
                    Text(notes)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
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

    private func formatDuration(_ seconds: Int) -> String {
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        let secs = seconds % 60

        if hours > 0 {
            return String(format: "%d:%02d:%02d", hours, minutes, secs)
        } else {
            return String(format: "%d:%02d", minutes, secs)
        }
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
            return "Saved \(relative.localizedString(for: date, relativeTo: Date()))"
        }

        return "Saved"
    }
}

#Preview {
    TVSavedVideosView()
        .environmentObject(APIClient())
}
