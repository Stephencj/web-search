import SwiftUI

@main
struct WebSearchTVApp: App {
    @StateObject private var apiClient = APIClient()

    var body: some Scene {
        WindowGroup {
            TVContentView()
                .environmentObject(apiClient)
        }
    }
}
