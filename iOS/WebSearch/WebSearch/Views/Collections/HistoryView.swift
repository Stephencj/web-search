import SwiftUI

struct HistoryView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var playerService = PlayerService.shared

    @State private var watchedVideos: [FeedItem] = []
    @State private var isLoading = false
    @State private var error: String?

    var body: some View {
        Group {
            if isLoading && watchedVideos.isEmpty {
                ProgressView("Loading history...")
            } else if watchedVideos.isEmpty {
                ContentUnavailableView(
                    "No Watch History",
                    systemImage: "clock",
                    description: Text("Videos you watch will appear here")
                )
            } else {
                List {
                    ForEach(watchedVideos) { item in
                        HistoryItemRow(item: item)
                            .swipeActions(edge: .leading) {
                                Button {
                                    markUnwatched(item)
                                } label: {
                                    Label("Mark Unwatched", systemImage: "eye.slash")
                                }
                                .tint(.orange)
                            }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle("Watch History")
        .refreshable {
            await loadHistory()
        }
        .task {
            await loadHistory()
        }
    }

    private func loadHistory() async {
        isLoading = true
        error = nil

        do {
            watchedVideos = try await apiClient.getWatchHistory()
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func markUnwatched(_ item: FeedItem) {
        Task {
            do {
                _ = try await apiClient.markUnwatched(itemId: item.id)
                watchedVideos.removeAll { $0.id == item.id }
            } catch {
                self.error = error.localizedDescription
            }
        }
    }
}

struct HistoryItemRow: View {
    let item: FeedItem
    @StateObject private var playerService = PlayerService.shared

    var body: some View {
        Button {
            playerService.play(video: item)
        } label: {
            HStack(alignment: .top, spacing: 12) {
                // Thumbnail
                ZStack(alignment: .bottomTrailing) {
                    AsyncImage(url: URL(string: item.thumbnailUrl ?? "")) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(16/9, contentMode: .fill)
                        case .failure:
                            Rectangle()
                                .fill(Color.gray.opacity(0.3))
                                .overlay {
                                    Image(systemName: "play.rectangle")
                                        .foregroundStyle(.secondary)
                                }
                        case .empty:
                            Rectangle()
                                .fill(Color.gray.opacity(0.2))
                                .overlay {
                                    ProgressView()
                                }
                        @unknown default:
                            Rectangle()
                                .fill(Color.gray.opacity(0.3))
                        }
                    }
                    .frame(width: 120, height: 68)
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                    // Duration badge
                    if !item.formattedDuration.isEmpty {
                        Text(item.formattedDuration)
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
                    Text(item.title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(2)
                        .foregroundStyle(.primary)
                        .multilineTextAlignment(.leading)

                    if let channelName = item.channelName {
                        Text(channelName)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }

                    HStack(spacing: 8) {
                        // Platform badge
                        PlatformBadge(platform: item.platform)

                        // Watched date
                        if let watchedAt = item.watchedAt {
                            Text(formatWatchedDate(watchedAt))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Spacer()
            }
        }
        .buttonStyle(.plain)
        .padding(.vertical, 4)
    }

    private func formatWatchedDate(_ dateString: String) -> String {
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
            return "Watched \(relative.localizedString(for: date, relativeTo: Date()))"
        }

        return ""
    }
}

#Preview {
    NavigationStack {
        HistoryView()
            .environmentObject(APIClient())
    }
}
