import SwiftUI

// Shared navigation state for cross-tab navigation
class NavigationState: ObservableObject {
    static let shared = NavigationState()

    @Published var discoverChannelName: String?

    func searchChannel(_ channelName: String) {
        discoverChannelName = channelName
    }

    func clearChannelSearch() {
        discoverChannelName = nil
    }
}

struct ContentView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var playerService = PlayerService.shared
    @StateObject private var navigationState = NavigationState.shared
    @State private var selectedTab = 0
    @State private var isCheckingAuth = true

    var body: some View {
        Group {
            if isCheckingAuth {
                // Loading state
                VStack {
                    ProgressView()
                    Text("Loading...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding(.top, 8)
                }
            } else if apiClient.currentUser == nil {
                // Not logged in
                LoginView()
            } else {
                // Logged in - show main app
                ZStack(alignment: .bottom) {
                    TabView(selection: $selectedTab) {
                        FeedView(selectedTab: $selectedTab)
                            .tabItem {
                                Label("Feed", systemImage: "play.rectangle.fill")
                            }
                            .tag(0)

                        ChannelsView()
                            .tabItem {
                                Label("Channels", systemImage: "person.2.fill")
                            }
                            .tag(1)

                        DiscoverView()
                            .environmentObject(navigationState)
                            .tabItem {
                                Label("Discover", systemImage: "magnifyingglass")
                            }
                            .tag(2)

                        CollectionsView(selectedTab: $selectedTab)
                            .tabItem {
                                Label("Collections", systemImage: "square.stack.fill")
                            }
                            .tag(3)

                        SavedVideosView(selectedTab: $selectedTab)
                            .environmentObject(navigationState)
                            .tabItem {
                                Label("Saved", systemImage: "bookmark.fill")
                            }
                            .tag(4)

                        SettingsView()
                            .tabItem {
                                Label("Settings", systemImage: "gear")
                            }
                            .tag(5)
                    }

                    // Mini player overlay
                    if playerService.currentVideo != nil && !playerService.showPlayer {
                        MiniPlayerView()
                            .transition(.move(edge: .bottom))
                            .padding(.bottom, 49) // Tab bar height
                    }
                }
                .fullScreenCover(isPresented: $playerService.showPlayer) {
                    if let video = playerService.currentVideo {
                        VideoPlayerView(video: video, isPresented: $playerService.showPlayer)
                            .environmentObject(apiClient)
                    }
                }
            }
        }
        .task {
            await checkAuth()
        }
    }

    private func checkAuth() async {
        isCheckingAuth = true

        // Test connection first
        await apiClient.testConnection()

        // Validate existing session
        if apiClient.authToken != nil {
            _ = await apiClient.validateSession()
        }

        isCheckingAuth = false
    }
}

#Preview {
    ContentView()
        .environmentObject(APIClient())
}
