import SwiftUI

struct CollectionDetailView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var playerService = PlayerService.shared
    let collection: Collection

    @State private var collectionWithItems: CollectionWithItems?
    @State private var isLoading = false
    @State private var error: String?

    private var items: [CollectionItem] {
        collectionWithItems?.items ?? []
    }

    private var videoItems: [CollectionItem] {
        items.filter { $0.itemType == "video" }
    }

    var body: some View {
        Group {
            if isLoading && collectionWithItems == nil {
                ProgressView("Loading...")
            } else if let error = error {
                ContentUnavailableView(
                    "Error Loading Collection",
                    systemImage: "exclamationmark.triangle",
                    description: Text(error)
                )
            } else if items.isEmpty {
                ContentUnavailableView(
                    "Empty Collection",
                    systemImage: "play.rectangle.on.rectangle",
                    description: Text("Add videos to this collection from your feed or discover")
                )
            } else {
                List {
                    ForEach(videoItems) { item in
                        CollectionItemRow(item: item) {
                            playItem(item)
                        }
                        .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                            Button(role: .destructive) {
                                deleteItem(item)
                            } label: {
                                Label("Remove", systemImage: "trash")
                            }
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
        .navigationTitle(collection.name)
        .refreshable {
            await loadCollection()
        }
        .task {
            await loadCollection()
        }
    }

    private func loadCollection() async {
        isLoading = true
        error = nil

        do {
            collectionWithItems = try await apiClient.getCollection(id: collection.id)
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func playItem(_ item: CollectionItem) {
        guard let feedItem = item.toFeedItem() else {
            print("Cannot play video: unable to extract videoId from URL: \(item.url)")
            return
        }
        playerService.play(video: feedItem)
    }

    private func deleteItem(_ item: CollectionItem) {
        Task {
            do {
                try await apiClient.removeItemFromCollection(collectionId: collection.id, itemId: item.id)
                await loadCollection()
            } catch {
                self.error = error.localizedDescription
            }
        }
    }
}

struct CollectionItemRow: View {
    let item: CollectionItem
    let onPlay: () -> Void

    var body: some View {
        Button(action: onPlay) {
            HStack(spacing: 12) {
                // Thumbnail
                AsyncImage(url: URL(string: item.thumbnailUrl ?? "")) { phase in
                    switch phase {
                    case .success(let image):
                        image
                            .resizable()
                            .aspectRatio(16/9, contentMode: .fill)
                    default:
                        Rectangle()
                            .fill(Color.gray.opacity(0.3))
                            .overlay {
                                Image(systemName: item.itemType == "video" ? "play.rectangle" : "photo")
                                    .foregroundStyle(.secondary)
                            }
                    }
                }
                .frame(width: 120, height: 68)
                .clipShape(RoundedRectangle(cornerRadius: 6))

                VStack(alignment: .leading, spacing: 4) {
                    Text(item.title ?? "Untitled")
                        .font(.headline)
                        .lineLimit(2)
                        .foregroundStyle(.primary)

                    if let domain = item.domain {
                        Text(domain)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    if let addedAt = item.addedAt {
                        Text("Added \(formatRelativeDate(addedAt))")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                Spacer()
            }
        }
        .buttonStyle(.plain)
        .padding(.vertical, 4)
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
    NavigationStack {
        CollectionDetailView(collection: Collection(
            id: 1,
            name: "Watch Later",
            slug: "watch-later",
            description: "Videos to watch later",
            coverUrl: nil,
            sortOrder: 0,
            itemCount: 5,
            createdAt: nil,
            updatedAt: nil
        ))
    }
    .environmentObject(APIClient())
}
