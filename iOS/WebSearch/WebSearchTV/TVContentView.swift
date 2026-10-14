import SwiftUI

// Navigation state for cross-tab communication
class TVNavigationState: ObservableObject {
    static let shared = TVNavigationState()
    @Published var searchChannelName: String?

    func searchChannel(_ name: String) {
        searchChannelName = name
    }

    func clearChannelSearch() {
        searchChannelName = nil
    }
}

struct TVContentView: View {
    @EnvironmentObject var apiClient: APIClient
    @StateObject private var navigationState = TVNavigationState.shared
    @State private var selectedTab = 0
    @State private var isCheckingAuth = true

    var body: some View {
        Group {
            if isCheckingAuth {
                // Loading state
                VStack {
                    ProgressView()
                    Text("Loading...")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                        .padding(.top, 16)
                }
            } else if apiClient.currentUser == nil {
                // Not logged in
                TVLoginView()
            } else {
                // Logged in - show main app
                TabView(selection: $selectedTab) {
                    TVFeedView()
                        .tabItem {
                            Label("Feed", systemImage: "play.rectangle.fill")
                        }
                        .tag(0)

                    TVChannelsView(selectedTab: $selectedTab)
                        .tabItem {
                            Label("Channels", systemImage: "person.2.fill")
                        }
                        .tag(1)

                    TVDiscoverView()
                        .environmentObject(navigationState)
                        .tabItem {
                            Label("Discover", systemImage: "magnifyingglass")
                        }
                        .tag(2)

                    TVCollectionsView()
                        .tabItem {
                            Label("Collections", systemImage: "square.stack.fill")
                        }
                        .tag(3)

                    TVSettingsView()
                        .tabItem {
                            Label("Settings", systemImage: "gear")
                        }
                        .tag(4)
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
    TVContentView()
        .environmentObject(APIClient())
}
