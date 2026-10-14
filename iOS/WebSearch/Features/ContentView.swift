import SwiftUI

struct ContentView: View {
    @StateObject private var playerService = PlayerService.shared
    @State private var selectedTab = 0

    var body: some View {
        ZStack(alignment: .bottom) {
            TabView(selection: $selectedTab) {
                FeedView()
                    .tabItem {
                        Label("Feed", systemImage: "play.rectangle.fill")
                    }
                    .tag(0)

                DiscoverView()
                    .tabItem {
                        Label("Discover", systemImage: "magnifyingglass")
                    }
                    .tag(1)

                SavedVideosView()
                    .tabItem {
                        Label("Saved", systemImage: "bookmark.fill")
                    }
                    .tag(2)

                SubscriptionsView()
                    .tabItem {
                        Label("Channels", systemImage: "person.2.fill")
                    }
                    .tag(3)

                SettingsView()
                    .tabItem {
                        Label("Settings", systemImage: "gear")
                    }
                    .tag(4)
            }

            // Mini player overlay when video is playing but not fullscreen
            if playerService.currentVideo != nil && !playerService.isFullScreen {
                MiniPlayerView()
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .padding(.bottom, 49) // Tab bar height
            }
        }
        .animation(.spring(response: 0.3), value: playerService.currentVideo != nil)
    }
}

// MARK: - Placeholder Views (to be implemented)

struct DiscoverView: View {
    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                "Discover",
                systemImage: "magnifyingglass",
                description: Text("Search for videos across platforms")
            )
            .navigationTitle("Discover")
        }
    }
}

struct SavedVideosView: View {
    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                "Saved Videos",
                systemImage: "bookmark.fill",
                description: Text("Your saved videos will appear here")
            )
            .navigationTitle("Saved")
        }
    }
}

struct SubscriptionsView: View {
    var body: some View {
        NavigationStack {
            ContentUnavailableView(
                "Subscriptions",
                systemImage: "person.2.fill",
                description: Text("Your channel subscriptions")
            )
            .navigationTitle("Channels")
        }
    }
}

struct SettingsView: View {
    @StateObject private var authService = AuthService.shared

    var body: some View {
        NavigationStack {
            List {
                Section("Account") {
                    HStack {
                        Circle()
                            .fill(Color(hex: authService.avatarColor) ?? .indigo)
                            .frame(width: 40, height: 40)
                            .overlay {
                                Text(authService.displayName.prefix(1).uppercased())
                                    .font(.headline)
                                    .foregroundColor(.white)
                            }

                        VStack(alignment: .leading) {
                            Text(authService.displayName)
                                .font(.headline)
                            if let user = authService.currentUser {
                                Text("@\(user.username)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }

                Section("App") {
                    Label("About", systemImage: "info.circle")
                    Label("Help & Feedback", systemImage: "questionmark.circle")
                }

                Section {
                    Button(role: .destructive) {
                        Task {
                            await authService.logout()
                        }
                    } label: {
                        Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }
            .navigationTitle("Settings")
        }
    }
}

// MARK: - Mini Player View

struct MiniPlayerView: View {
    @StateObject private var playerService = PlayerService.shared

    var body: some View {
        HStack(spacing: 12) {
            // Thumbnail
            if let thumbnailUrl = playerService.currentVideo?.thumbnailUrl,
               let url = URL(string: thumbnailUrl) {
                AsyncImage(url: url) { image in
                    image
                        .resizable()
                        .aspectRatio(16/9, contentMode: .fill)
                } placeholder: {
                    Rectangle()
                        .fill(.quaternary)
                }
                .frame(width: 80, height: 45)
                .clipShape(RoundedRectangle(cornerRadius: 4))
            }

            // Title and channel
            VStack(alignment: .leading, spacing: 2) {
                Text(playerService.currentVideo?.title ?? "Unknown")
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .lineLimit(1)

                Text(playerService.currentVideo?.channelName ?? "Unknown")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }

            Spacer()

            // Controls
            HStack(spacing: 16) {
                Button {
                    playerService.togglePlayPause()
                } label: {
                    Image(systemName: playerService.isPlaying ? "pause.fill" : "play.fill")
                        .font(.title2)
                }

                Button {
                    playerService.stop()
                } label: {
                    Image(systemName: "xmark")
                        .font(.body)
                }
            }
            .foregroundStyle(.primary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(.regularMaterial)
        .overlay(alignment: .bottom) {
            // Progress bar
            GeometryReader { geo in
                Rectangle()
                    .fill(.tint)
                    .frame(
                        width: geo.size.width * (playerService.duration > 0 ? playerService.currentTime / playerService.duration : 0),
                        height: 2
                    )
            }
            .frame(height: 2)
        }
        .onTapGesture {
            playerService.setFullScreen(true)
        }
    }
}

// MARK: - Color Extension

extension Color {
    init?(hex: String) {
        var hexSanitized = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        hexSanitized = hexSanitized.replacingOccurrences(of: "#", with: "")

        var rgb: UInt64 = 0
        guard Scanner(string: hexSanitized).scanHexInt64(&rgb) else { return nil }

        let r = Double((rgb & 0xFF0000) >> 16) / 255.0
        let g = Double((rgb & 0x00FF00) >> 8) / 255.0
        let b = Double(rgb & 0x0000FF) / 255.0

        self.init(red: r, green: g, blue: b)
    }
}

#Preview {
    ContentView()
}
