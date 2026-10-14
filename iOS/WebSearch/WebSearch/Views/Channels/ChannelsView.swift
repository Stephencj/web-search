import SwiftUI

struct ChannelsView: View {
    @EnvironmentObject var apiClient: APIClient
    @State private var channels: [Channel] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var showAddChannel = false
    @State private var selectedPlatform: String?
    @State private var channelToDelete: Channel?
    @State private var showDeleteConfirmation = false
    @State private var syncingChannelId: Int?

    let platforms = ["youtube", "rumble", "odysee", "podcast", "redbar"]

    var filteredChannels: [Channel] {
        if let platform = selectedPlatform {
            return channels.filter { $0.platform.lowercased() == platform }
        }
        return channels
    }

    var body: some View {
        NavigationStack {
            Group {
                if isLoading && channels.isEmpty {
                    ProgressView("Loading channels...")
                } else if channels.isEmpty {
                    ContentUnavailableView(
                        "No Subscriptions",
                        systemImage: "person.2",
                        description: Text("Subscribe to channels to start building your feed")
                    )
                } else {
                    List {
                        // Platform filter chips
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                FilterChip(title: "All", isSelected: selectedPlatform == nil) {
                                    selectedPlatform = nil
                                }

                                ForEach(platforms, id: \.self) { platform in
                                    let count = channels.filter { $0.platform.lowercased() == platform }.count
                                    if count > 0 {
                                        FilterChip(
                                            title: "\(platform.capitalized) (\(count))",
                                            isSelected: selectedPlatform == platform
                                        ) {
                                            selectedPlatform = platform
                                        }
                                    }
                                }
                            }
                            .padding(.horizontal)
                        }
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)

                        ForEach(filteredChannels) { channel in
                            ChannelRow(
                                channel: channel,
                                isSyncing: syncingChannelId == channel.id,
                                onSync: { syncChannel(channel) }
                            )
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    channelToDelete = channel
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("Unsubscribe", systemImage: "trash")
                                }
                            }
                            .swipeActions(edge: .leading) {
                                Button {
                                    syncChannel(channel)
                                } label: {
                                    Label("Sync", systemImage: "arrow.triangle.2.circlepath")
                                }
                                .tint(.blue)
                            }
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Channels")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showAddChannel = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .refreshable {
                await loadChannels()
            }
            .sheet(isPresented: $showAddChannel) {
                AddChannelSheet { newChannel in
                    channels.insert(newChannel, at: 0)
                }
            }
            .alert("Unsubscribe", isPresented: $showDeleteConfirmation) {
                Button("Cancel", role: .cancel) {
                    channelToDelete = nil
                }
                Button("Unsubscribe", role: .destructive) {
                    if let channel = channelToDelete {
                        deleteChannel(channel)
                    }
                }
            } message: {
                if let channel = channelToDelete {
                    Text("Unsubscribe from \(channel.name)?")
                }
            }
            .task {
                await loadChannels()
            }
        }
    }

    private func loadChannels() async {
        isLoading = true
        error = nil

        do {
            channels = try await apiClient.getChannels()
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func deleteChannel(_ channel: Channel) {
        Task {
            do {
                try await apiClient.deleteChannel(id: channel.id)
                channels.removeAll { $0.id == channel.id }
            } catch {
                self.error = error.localizedDescription
            }
            channelToDelete = nil
        }
    }

    private func syncChannel(_ channel: Channel) {
        syncingChannelId = channel.id

        Task {
            do {
                _ = try await apiClient.syncChannel(id: channel.id)
                // Reload to get updated counts
                await loadChannels()
            } catch {
                self.error = error.localizedDescription
            }
            syncingChannelId = nil
        }
    }
}

struct FilterChip: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(isSelected ? Color.blue : Color(.systemGray5))
                .foregroundStyle(isSelected ? .white : .primary)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }
}

struct ChannelRow: View {
    let channel: Channel
    let isSyncing: Bool
    let onSync: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Avatar
            AsyncImage(url: URL(string: channel.avatarUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                case .failure, .empty:
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .overlay {
                            Text(String(channel.name.prefix(1)).uppercased())
                                .font(.title3)
                                .fontWeight(.semibold)
                                .foregroundStyle(.secondary)
                        }
                @unknown default:
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                }
            }
            .frame(width: 50, height: 50)
            .clipShape(Circle())

            // Info
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(channel.name)
                        .font(.headline)
                        .lineLimit(1)

                    if !channel.isActive {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.caption)
                            .foregroundStyle(.orange)
                    }
                }

                HStack(spacing: 8) {
                    PlatformBadge(platform: channel.platform)

                    if let videoCount = channel.videoCount {
                        Text("\(videoCount) videos")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    if let unwatched = channel.unwatchedCount, unwatched > 0 {
                        Text("\(unwatched) new")
                            .font(.caption)
                            .foregroundStyle(.blue)
                    }
                }

                if let lastSync = channel.lastSyncedAt {
                    Text("Synced \(formatRelativeDate(lastSync))")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                if let syncError = channel.lastSyncError, !syncError.isEmpty {
                    Text(syncError)
                        .font(.caption2)
                        .foregroundStyle(.red)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Sync button
            Button(action: onSync) {
                if isSyncing {
                    ProgressView()
                        .scaleEffect(0.8)
                } else {
                    Image(systemName: "arrow.triangle.2.circlepath")
                        .font(.title3)
                }
            }
            .buttonStyle(.bordered)
            .disabled(isSyncing)
        }
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
    ChannelsView()
        .environmentObject(APIClient())
}
