import SwiftUI

struct FeedItemRow: View {
    let item: FeedItem
    let onPlay: () -> Void

    var body: some View {
        Button(action: onPlay) {
            HStack(alignment: .top, spacing: 12) {
                // Thumbnail with duration overlay
                thumbnailView

                // Content
                VStack(alignment: .leading, spacing: 4) {
                    // Title
                    Text(item.title)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)
                        .foregroundStyle(item.isWatched ? .secondary : .primary)

                    // Channel name
                    if let channelName = item.channelName {
                        Text(channelName)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }

                    // Metadata row
                    HStack(spacing: 8) {
                        // Platform badge
                        platformBadge

                        // Upload date
                        if let uploadDate = item.uploadDate {
                            Text(uploadDate, style: .relative)
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                        }

                        // View count
                        if let viewCount = item.viewCount, viewCount > 0 {
                            Text(formatViewCount(viewCount))
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                        }
                    }

                    // Progress bar
                    if item.progressPercentage > 0 && !item.isWatched {
                        ProgressView(value: item.progressPercentage)
                            .tint(.accentColor)
                            .padding(.top, 4)
                    }
                }

                Spacer(minLength: 0)

                // Watched indicator
                if item.isWatched {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                        .font(.caption)
                }
            }
            .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Thumbnail
    @ViewBuilder
    private var thumbnailView: some View {
        ZStack(alignment: .bottomTrailing) {
            if let thumbnailUrl = item.thumbnailUrl,
               let url = URL(string: thumbnailUrl) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .empty:
                        Rectangle()
                            .fill(.quaternary)
                            .overlay {
                                ProgressView()
                                    .scaleEffect(0.5)
                            }
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(16/9, contentMode: .fill)
                    case .failure:
                        Rectangle()
                            .fill(.quaternary)
                            .overlay {
                                Image(systemName: "photo")
                                    .foregroundStyle(.tertiary)
                            }
                    @unknown default:
                        Rectangle()
                            .fill(.quaternary)
                    }
                }
            } else {
                Rectangle()
                    .fill(.quaternary)
                    .overlay {
                        Image(systemName: "play.rectangle")
                            .foregroundStyle(.tertiary)
                    }
            }

            // Duration badge
            if let duration = item.durationSeconds, duration > 0 {
                Text(item.formattedDuration)
                    .font(.caption2)
                    .fontWeight(.medium)
                    .padding(.horizontal, 4)
                    .padding(.vertical, 2)
                    .background(.black.opacity(0.7))
                    .foregroundColor(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 2))
                    .padding(4)
            }
        }
        .frame(width: 120, height: 68)
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }

    // MARK: - Platform Badge
    @ViewBuilder
    private var platformBadge: some View {
        let (icon, color) = platformInfo(item.platform)

        HStack(spacing: 2) {
            Image(systemName: icon)
            Text(item.platform.capitalized)
        }
        .font(.caption2)
        .foregroundStyle(color)
    }

    private func platformInfo(_ platform: String) -> (icon: String, color: Color) {
        switch platform.lowercased() {
        case "youtube":
            return ("play.rectangle.fill", .red)
        case "rumble":
            return ("play.circle.fill", .green)
        case "podcast":
            return ("waveform", .purple)
        default:
            return ("play.fill", .secondary)
        }
    }

    // MARK: - Formatting
    private func formatViewCount(_ count: Int) -> String {
        if count >= 1_000_000 {
            return String(format: "%.1fM views", Double(count) / 1_000_000)
        } else if count >= 1_000 {
            return String(format: "%.1fK views", Double(count) / 1_000)
        } else {
            return "\(count) views"
        }
    }
}

// MARK: - Preview

#Preview {
    List {
        FeedItemRow(
            item: FeedItem(
                id: 1,
                platform: "youtube",
                videoId: "abc123",
                videoUrl: "https://youtube.com/watch?v=abc123",
                title: "This is a sample video title that might be quite long",
                thumbnailUrl: nil,
                channelName: "Sample Channel",
                durationSeconds: 754,
                viewCount: 123456,
                uploadDate: Date().addingTimeInterval(-86400),
                isWatched: false,
                watchProgressSeconds: 200
            ),
            onPlay: {}
        )

        FeedItemRow(
            item: FeedItem(
                id: 2,
                platform: "rumble",
                videoId: "def456",
                videoUrl: "https://rumble.com/v/def456",
                title: "Another video that has been watched",
                channelName: "Another Channel",
                durationSeconds: 1200,
                isWatched: true
            ),
            onPlay: {}
        )
    }
    .listStyle(.plain)
}
