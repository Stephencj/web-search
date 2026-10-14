import SwiftUI

struct LoginView: View {
    @EnvironmentObject var apiClient: APIClient
    @State private var users: [User] = []
    @State private var selectedUser: User?
    @State private var pin = ""
    @State private var isLoading = false
    @State private var error: String?
    @State private var showPinEntry = false
    @State private var authMode: AuthMode?

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                // Logo/Title
                VStack(spacing: 8) {
                    Image(systemName: "play.rectangle.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(.blue)

                    Text("Video Feed")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Select your profile")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 40)

                if isLoading && users.isEmpty {
                    ProgressView("Loading...")
                        .padding(.top, 40)
                } else if users.isEmpty {
                    ContentUnavailableView(
                        "No Users",
                        systemImage: "person.crop.circle.badge.exclamationmark",
                        description: Text("No users found. Check your server connection.")
                    )
                } else {
                    // User grid
                    LazyVGrid(columns: [
                        GridItem(.flexible()),
                        GridItem(.flexible())
                    ], spacing: 16) {
                        ForEach(users) { user in
                            UserButton(user: user, isSelected: selectedUser?.id == user.id) {
                                selectUser(user)
                            }
                        }
                    }
                    .padding(.horizontal)
                }

                Spacer()

                if let error = error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal)
                }
            }
            .navigationBarHidden(true)
            .task {
                await loadUsers()
            }
            .sheet(isPresented: $showPinEntry) {
                PinEntrySheet(
                    user: selectedUser,
                    pin: $pin,
                    isLoading: isLoading,
                    error: error,
                    onSubmit: { submitLogin() },
                    onCancel: {
                        showPinEntry = false
                        selectedUser = nil
                        pin = ""
                        error = nil
                    }
                )
            }
        }
    }

    private func loadUsers() async {
        isLoading = true
        error = nil

        do {
            authMode = try await apiClient.getAuthMode()
            users = try await apiClient.getUsers()
        } catch {
            self.error = "Failed to load users: \(error.localizedDescription)"
        }

        isLoading = false
    }

    private func selectUser(_ user: User) {
        selectedUser = user
        error = nil
        pin = ""

        // Check if user has PIN
        if user.hasPin == true {
            showPinEntry = true
        } else {
            // Direct login without PIN
            submitLogin()
        }
    }

    private func submitLogin() {
        guard let user = selectedUser else { return }

        isLoading = true
        error = nil

        Task {
            do {
                _ = try await apiClient.login(
                    username: user.username,
                    pin: pin.isEmpty ? nil : pin
                )
                showPinEntry = false
            } catch let apiError as APIError {
                error = apiError.errorDescription
            } catch {
                self.error = error.localizedDescription
            }
            isLoading = false
        }
    }
}

struct UserButton: View {
    let user: User
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 12) {
                // Avatar
                Circle()
                    .fill(Color(hex: user.avatarColor) ?? .blue)
                    .frame(width: 70, height: 70)
                    .overlay {
                        Text(user.initials)
                            .font(.title2)
                            .fontWeight(.semibold)
                            .foregroundStyle(.white)
                    }
                    .overlay {
                        Circle()
                            .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 3)
                    }

                // Name
                Text(user.displayName ?? user.username)
                    .font(.subheadline)
                    .fontWeight(.medium)
                    .foregroundStyle(.primary)
                    .lineLimit(1)

                // Admin badge
                if user.isAdmin == true {
                    Text("Admin")
                        .font(.caption2)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(Color.orange.opacity(0.2))
                        .foregroundStyle(.orange)
                        .clipShape(Capsule())
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .clipShape(RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
    }
}

struct PinEntrySheet: View {
    let user: User?
    @Binding var pin: String
    let isLoading: Bool
    let error: String?
    let onSubmit: () -> Void
    let onCancel: () -> Void

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                if let user = user {
                    // User avatar
                    Circle()
                        .fill(Color(hex: user.avatarColor) ?? .blue)
                        .frame(width: 80, height: 80)
                        .overlay {
                            Text(user.initials)
                                .font(.title)
                                .fontWeight(.semibold)
                                .foregroundStyle(.white)
                        }

                    Text(user.displayName ?? user.username)
                        .font(.title2)
                        .fontWeight(.semibold)
                }

                // PIN entry
                SecureField("Enter PIN", text: $pin)
                    .textFieldStyle(.roundedBorder)
                    .keyboardType(.numberPad)
                    .frame(maxWidth: 200)
                    .multilineTextAlignment(.center)

                if let error = error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                Button {
                    onSubmit()
                } label: {
                    if isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("Sign In")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(pin.isEmpty || isLoading)
                .frame(maxWidth: 200)

                Spacer()
            }
            .padding(.top, 40)
            .navigationTitle("Enter PIN")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        onCancel()
                    }
                }
            }
        }
        .presentationDetents([.medium])
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
    LoginView()
        .environmentObject(APIClient())
}
