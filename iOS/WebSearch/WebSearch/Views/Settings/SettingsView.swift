import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var apiClient: APIClient
    @State private var serverURL: String = ""
    @State private var isTestingConnection = false
    @State private var connectionStatus: ConnectionStatus = .unknown
    @State private var feedStats: FeedStats?
    @State private var showLogoutConfirmation = false

    enum ConnectionStatus {
        case unknown, testing, connected, failed(String)
    }

    var body: some View {
        NavigationStack {
            List {
                // Current user
                if let user = apiClient.currentUser {
                    Section {
                        HStack(spacing: 12) {
                            Circle()
                                .fill(Color(hex: user.avatarColor) ?? .blue)
                                .frame(width: 50, height: 50)
                                .overlay {
                                    Text(user.initials)
                                        .font(.title3)
                                        .fontWeight(.semibold)
                                        .foregroundStyle(.white)
                                }

                            VStack(alignment: .leading, spacing: 4) {
                                Text(user.displayName ?? user.username)
                                    .font(.headline)

                                Text("@\(user.username)")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)

                                if user.isAdmin == true {
                                    Text("Administrator")
                                        .font(.caption)
                                        .foregroundStyle(.orange)
                                }
                            }

                            Spacer()
                        }

                        Button(role: .destructive) {
                            showLogoutConfirmation = true
                        } label: {
                            Label("Sign Out", systemImage: "rectangle.portrait.and.arrow.right")
                        }
                    } header: {
                        Text("Account")
                    }
                }

                // Server connection
                Section {
                    HStack {
                        TextField("Server URL", text: $serverURL)
                            .textContentType(.URL)
                            .autocapitalization(.none)
                            .autocorrectionDisabled()
                            .keyboardType(.URL)

                        connectionStatusView
                    }

                    Button {
                        testConnection()
                    } label: {
                        HStack {
                            Text("Test Connection")
                            Spacer()
                            if isTestingConnection {
                                ProgressView()
                            }
                        }
                    }
                    .disabled(isTestingConnection)
                } header: {
                    Text("Server")
                } footer: {
                    Text("The URL of your video feed backend server")
                }

                // Feed stats
                if let stats = feedStats {
                    Section {
                        LabeledContent("Total Videos", value: "\(stats.totalVideos)")
                        LabeledContent("Watched", value: "\(stats.watchedCount)")
                        LabeledContent("Unwatched", value: "\(stats.unwatchedCount)")

                        if let byPlatform = stats.byPlatform {
                            ForEach(Array(byPlatform.keys.sorted()), id: \.self) { platform in
                                if let count = byPlatform[platform] {
                                    HStack {
                                        PlatformBadge(platform: platform)
                                        Spacer()
                                        Text("\(count)")
                                            .foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    } header: {
                        Text("Feed Statistics")
                    }
                }

                // About
                Section {
                    LabeledContent("App Version", value: "1.0.0")
                    LabeledContent("Build", value: "1")
                } header: {
                    Text("About")
                }
            }
            .navigationTitle("Settings")
            .onAppear {
                serverURL = apiClient.baseURL
                loadStats()
            }
            .onChange(of: serverURL) { _, newValue in
                apiClient.baseURL = newValue
                connectionStatus = .unknown
            }
            .alert("Sign Out", isPresented: $showLogoutConfirmation) {
                Button("Cancel", role: .cancel) {}
                Button("Sign Out", role: .destructive) {
                    logout()
                }
            } message: {
                Text("Are you sure you want to sign out?")
            }
        }
    }

    @ViewBuilder
    private var connectionStatusView: some View {
        switch connectionStatus {
        case .unknown:
            Image(systemName: "circle")
                .foregroundStyle(.secondary)
        case .testing:
            ProgressView()
                .scaleEffect(0.7)
        case .connected:
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .failed:
            Image(systemName: "xmark.circle.fill")
                .foregroundStyle(.red)
        }
    }

    private func testConnection() {
        isTestingConnection = true
        connectionStatus = .testing

        Task {
            await apiClient.testConnection()

            if apiClient.isConnected {
                connectionStatus = .connected
            } else {
                connectionStatus = .failed(apiClient.connectionError ?? "Unknown error")
            }
            isTestingConnection = false
        }
    }

    private func loadStats() {
        Task {
            do {
                feedStats = try await apiClient.getFeedStats()
            } catch {
                print("Failed to load stats: \(error)")
            }
        }
    }

    private func logout() {
        Task {
            do {
                try await apiClient.logout()
            } catch {
                // Force logout anyway
                apiClient.authToken = nil
                apiClient.currentUser = nil
            }
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(APIClient())
}
