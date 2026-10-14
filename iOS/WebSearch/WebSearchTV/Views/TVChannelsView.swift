import SwiftUI

struct TVChannelsView: View {
    @EnvironmentObject var apiClient: APIClient
    @Binding var selectedTab: Int

    @State private var channels: [Channel] = []
    @State private var isLoading = false
    @State private var error: String?

    // Filters
    @State private var selectedPlatform: String = "all"
    @State private var platforms: [Platform] = []

    // Sync state
    @State private var syncingChannelId: Int?
    @State private var toastMessage: String?
    @State private var showToast = false

    // Delete confirmation
    @State private var channelToDelete: Channel?
    @State private var showDeleteConfirmation = false

    private var filteredChannels: [Channel] {
        if selectedPlatform == "all" {
            return channels
        }
        return channels.filter { $0.platform.lowercased() == selectedPlatform }
    }

    private let columns = [
        GridItem(.adaptive(minimum: 300, maximum: 350), spacing: 40)
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Filter bar
                HStack(spacing: 30) {
                    // Platform filter
                    HStack(spacing: 12) {
                        Text("Platform:")
                            .foregroundStyle(.secondary)
                        Picker("Platform", selection: $selectedPlatform) {
                            Text("All (\(channels.count))").tag("all")
                            ForEach(platforms) { platform in
                                let count = channels.filter { $0.platform.lowercased() == platform.platformId.lowercased() }.count
                                Text("\(platform.name) (\(count))").tag(platform.platformId)
                            }
                        }
                        .pickerStyle(.menu)
                    }

                    Spacer()

                    // Refresh button
                    Button {
                        Task { await loadChannels() }
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                    .buttonStyle(.bordered)
                }
                .padding(.horizontal, 60)
                .padding(.vertical, 20)

                ScrollView {
                    if isLoading && channels.isEmpty {
                        ProgressView("Loading channels...")
                            .padding(.top, 100)
                    } else if let error = error {
                        ContentUnavailableView(
                            "Error Loading Channels",
                            systemImage: "exclamationmark.triangle",
                            description: Text(error)
                        )
                        .padding(.top, 100)
                    } else if filteredChannels.isEmpty {
                        ContentUnavailableView(
                            "No Channels",
                            systemImage: "person.2",
                            description: Text(selectedPlatform == "all" ? "Subscribe to channels from Discover" : "No \(selectedPlatform.capitalized) channels")
                        )
                        .padding(.top, 100)
                    } else {
                        LazyVGrid(columns: columns, spacing: 40) {
                            ForEach(filteredChannels) { channel in
                                TVChannelCard(channel: channel, isSyncing: syncingChannelId == channel.id) {
                                    // Navigate to Discover with this channel
                                    TVNavigationState.shared.searchChannel(channel.name)
                                    selectedTab = 2  // Discover tab
                                }
                                .contextMenu {
                                    Button {
                                        Task { await syncChannel(channel) }
                                    } label: {
                                        Label("Sync Channel", systemImage: "arrow.triangle.2.circlepath")
                                    }

                                    Button(role: .destructive) {
                                        channelToDelete = channel
                                        showDeleteConfirmation = true
                                    } label: {
                                        Label("Unsubscribe", systemImage: "person.badge.minus")
                                    }
                                }
                            }
                        }
                        .padding(60)
                    }
                }
            }
            .navigationTitle("Channels")
            .refreshable {
                await loadChannels()
            }
        }
        .alert("Unsubscribe from Channel?", isPresented: $showDeleteConfirmation) {
            Button("Cancel", role: .cancel) {
                channelToDelete = nil
            }
            Button("Unsubscribe", role: .destructive) {
                if let channel = channelToDelete {
                    Task { await deleteChannel(channel) }
                }
            }
        } message: {
            if let channel = channelToDelete {
                Text("Are you sure you want to unsubscribe from \(channel.name)? This will remove all their videos from your feed.")
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
            await loadChannels()
        }
        .task {
            await loadPlatforms()
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

    private func loadPlatforms() async {
        do {
            platforms = try await apiClient.getPlatforms()
        } catch {
            print("Failed to load platforms: \(error)")
        }
    }

    private func syncChannel(_ channel: Channel) async {
        syncingChannelId = channel.id

        do {
            let result = try await apiClient.syncChannel(id: channel.id)
            await loadChannels()  // Refresh to show new video count
            showToastMessage("Synced \(channel.name): \(result.message)")
        } catch {
            showToastMessage("Failed to sync: \(error.localizedDescription)")
        }

        syncingChannelId = nil
    }

    private func deleteChannel(_ channel: Channel) async {
        do {
            try await apiClient.deleteChannel(id: channel.id)
            channels.removeAll { $0.id == channel.id }
            showToastMessage("Unsubscribed from \(channel.name)")
        } catch {
            showToastMessage("Failed to unsubscribe: \(error.localizedDescription)")
        }
        channelToDelete = nil
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

// MARK: - Channel Card

struct TVChannelCard: View {
    let channel: Channel
    var isSyncing: Bool = false
    let onSelect: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        Button(action: onSelect) {
            VStack(spacing: 16) {
                // Avatar
                ZStack {
                    if let avatarUrl = channel.avatarUrl, let url = URL(string: avatarUrl) {
                        AsyncImage(url: url) { image in
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Circle()
                                .fill(Color.gray.opacity(0.3))
                                .overlay {
                                    Text(String(channel.name.prefix(1)).uppercased())
                                        .font(.largeTitle)
                                        .fontWeight(.bold)
                                        .foregroundStyle(.secondary)
                                }
                        }
                        .frame(width: 120, height: 120)
                        .clipShape(Circle())
                    } else {
                        Circle()
                            .fill(Color.gray.opacity(0.3))
                            .frame(width: 120, height: 120)
                            .overlay {
                                Text(String(channel.name.prefix(1)).uppercased())
                                    .font(.largeTitle)
                                    .fontWeight(.bold)
                                    .foregroundStyle(.secondary)
                            }
                    }

                    // Syncing overlay
                    if isSyncing {
                        Circle()
                            .fill(Color.black.opacity(0.5))
                            .frame(width: 120, height: 120)
                            .overlay {
                                ProgressView()
                                    .scaleEffect(1.5)
                            }
                    }
                }

                // Name
                Text(channel.name)
                    .font(.headline)
                    .lineLimit(1)

                // Stats
                HStack(spacing: 16) {
                    if let videoCount = channel.videoCount {
                        Label("\(videoCount)", systemImage: "play.rectangle")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }

                    if let unwatched = channel.unwatchedCount, unwatched > 0 {
                        Text("\(unwatched) new")
                            .font(.caption)
                            .foregroundStyle(.blue)
                    }
                }

                // Platform badge
                TVPlatformBadge(platform: channel.platform)
            }
            .padding(24)
            .background(isFocused ? Color.blue.opacity(0.2) : Color.secondary.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
        .scaleEffect(isFocused ? 1.05 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }
}

// MARK: - Platform Badge

struct TVPlatformBadge: View {
    let platform: String

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: platformIcon)
                .font(.caption)
            Text(platform.capitalized)
                .font(.caption)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .background(platformColor.opacity(0.2))
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
    TVChannelsView(selectedTab: .constant(1))
        .environmentObject(APIClient())
}
