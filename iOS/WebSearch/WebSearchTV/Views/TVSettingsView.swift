import SwiftUI

struct TVSettingsView: View {
    @EnvironmentObject var apiClient: APIClient

    @State private var showLogoutConfirmation = false
    @State private var showServerSettings = false

    @AppStorage(AdBlocking.settingKey) private var blockAds = true

    var body: some View {
        NavigationStack {
            List {
                // User section
                if let user = apiClient.currentUser {
                    Section("Account") {
                        HStack(spacing: 20) {
                            Circle()
                                .fill(Color(hex: user.avatarColor) ?? .blue)
                                .frame(width: 60, height: 60)
                                .overlay {
                                    Text(user.initials)
                                        .font(.title2)
                                        .fontWeight(.bold)
                                        .foregroundStyle(.white)
                                }

                            VStack(alignment: .leading, spacing: 4) {
                                Text(user.displayName ?? user.username)
                                    .font(.headline)
                                Text("@\(user.username)")
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 8)
                    }
                }

                Section {
                    Toggle("Block Ads", isOn: $blockAds)
                } header: {
                    Text("Playback")
                } footer: {
                    Text("Skips sponsor and self-promotion segments in YouTube videos, using SponsorBlock.")
                }

                // Server section
                Section("Server") {
                    HStack {
                        Text("Server URL")
                        Spacer()
                        Text(apiClient.baseURL)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Connection")
                        Spacer()
                        if apiClient.isConnected {
                            Label("Connected", systemImage: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                        } else {
                            Label("Disconnected", systemImage: "xmark.circle.fill")
                                .foregroundStyle(.red)
                        }
                    }
                }

                // App info section
                Section("About") {
                    HStack {
                        Text("Version")
                        Spacer()
                        Text(Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0")
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Build")
                        Spacer()
                        Text(Bundle.main.infoDictionary?["CFBundleVersion"] as? String ?? "1")
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Platform")
                        Spacer()
                        Text("tvOS")
                            .foregroundStyle(.secondary)
                    }
                }

                // Actions section
                Section {
                    Button {
                        Task {
                            await apiClient.testConnection()
                        }
                    } label: {
                        Label("Test Connection", systemImage: "arrow.triangle.2.circlepath")
                    }

                    Button(role: .destructive) {
                        showLogoutConfirmation = true
                    } label: {
                        Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }
            .navigationTitle("Settings")
            .confirmationDialog("Log Out", isPresented: $showLogoutConfirmation, titleVisibility: .visible) {
                Button("Log Out", role: .destructive) {
                    Task {
                        try? await apiClient.logout()
                    }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("Are you sure you want to log out?")
            }
        }
    }
}

#Preview {
    TVSettingsView()
        .environmentObject(APIClient())
}
