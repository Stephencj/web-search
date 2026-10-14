import SwiftUI

struct FeedItemRow: View {
    let item: FeedItem
    var compact: Bool = false
    let onToggleWatched: () -> Void
    var onChannelTap: (() -> Void)? = nil

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
                    .frame(width: compact ? 100 : 140, height: compact ? 56 : 79)
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

                    // Watch progress indicator
                    if let progress = item.watchProgressSeconds,
                       let duration = item.durationSeconds,
                       duration > 0 && progress > 0 && !item.isWatched {
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
                    Text(item.title)
                        .font(compact ? .subheadline : .headline)
                        .fontWeight(.medium)
                        .lineLimit(2)
                        .foregroundStyle(.primary)
                        .multilineTextAlignment(.leading)

                    if !compact, let channelName = item.channelName {
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
                        // Platform badge
                        PlatformBadge(platform: item.platform)

                        // Views
                        if !item.formattedViews.isEmpty {
                            Text(item.formattedViews)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        // Upload date
                        if let uploadDate = item.uploadDate {
                            Text(formatRelativeDate(uploadDate))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    // Watched indicator
                    if item.isWatched {
                        HStack(spacing: 4) {
                            Image(systemName: "checkmark.circle.fill")
                                .font(.caption2)
                            Text("Watched")
                                .font(.caption2)
                        }
                        .foregroundStyle(.green)
                    }
                }

                Spacer()
            }
        }
        .buttonStyle(.plain)
        .padding(.vertical, compact ? 4 : 8)
        .opacity(item.isWatched ? 0.7 : 1.0)
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

struct PlatformBadge: View {
    let platform: String

    var body: some View {
        HStack(spacing: 4) {
            Image(systemName: platformIcon)
                .font(.caption2)
            Text(platform.capitalized)
                .font(.caption2)
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(platformColor.opacity(0.15))
        .foregroundStyle(platformColor)
        .clipShape(Capsule())
    }

    private var platformIcon: String {
        switch platform.lowercased() {
        case "youtube": return "play.rectangle.fill"
        case "rumble": return "r.circle.fill"
        case "odysee": return "o.circle.fill"
        case "podcast": return "mic.fill"
        case "redbar": return "radio.fill"
        default: return "tv.fill"
        }
    }

    private var platformColor: Color {
        switch platform.lowercased() {
        case "youtube": return .red
        case "rumble": return .green
        case "odysee": return .pink
        case "podcast": return .purple
        case "redbar": return .orange
        default: return .blue
        }
    }
}

#Preview {
    List {
        FeedItemRow(
            item: FeedItem(
                id: 1,
                channelId: 1,
                platform: "youtube",
                videoId: "abc123",
                videoUrl: "https://youtube.com/watch?v=abc123",
                title: "This is a sample video title that might be quite long",
                description: nil,
                thumbnailUrl: "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
                durationSeconds: 3661,
                viewCount: 1234567,
                uploadDate: "2024-12-10T15:30:00Z",
                categories: nil,
                isWatched: false,
                watchedAt: nil,
                watchProgressSeconds: 120,
                discoveredAt: nil,
                channelName: "Sample Channel"
            ),
            onToggleWatched: {}
        )
    }
}
