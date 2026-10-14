import SwiftUI
import SwiftData

@main
struct WebSearchApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            RootView()
        }
        .modelContainer(for: [
            User.self,
            Channel.self,
            FeedItem.self,
            SavedVideo.self,
            Collection.self,
            CollectionItem.self,
            WatchState.self
        ])
    }
}

// MARK: - Root View
struct RootView: View {
    @StateObject private var authService = AuthService.shared

    var body: some View {
        Group {
            if authService.isAuthenticated {
                ContentView()
            } else {
                LoginView()
            }
        }
        .animation(.easeInOut, value: authService.isAuthenticated)
    }
}
