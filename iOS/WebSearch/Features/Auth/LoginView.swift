import SwiftUI

struct LoginView: View {
    @StateObject private var authService = AuthService.shared
    @State private var users: [UserPublic] = []
    @State private var selectedUser: UserPublic?
    @State private var pin = ""
    @State private var isLoading = true
    @State private var showPinEntry = false
    @FocusState private var pinFocused: Bool

    var body: some View {
        NavigationStack {
            Group {
                if isLoading {
                    loadingView
                } else if showPinEntry, let user = selectedUser {
                    pinEntryView(for: user)
                } else {
                    userSelectionView
                }
            }
            .navigationBarHidden(true)
        }
        .task {
            await loadUsers()
        }
    }

    // MARK: - Loading View
    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)
            Text("Loading...")
                .foregroundStyle(.secondary)
        }
    }

    // MARK: - User Selection View
    private var userSelectionView: some View {
        ScrollView {
            VStack(spacing: 32) {
                // Header
                VStack(spacing: 12) {
                    Image(systemName: "play.rectangle.fill")
                        .font(.system(size: 60))
                        .foregroundStyle(.tint)

                    Text("WebSearch")
                        .font(.largeTitle)
                        .fontWeight(.bold)

                    Text("Select your profile")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.top, 60)

                // User Grid
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 16) {
                    ForEach(users, id: \.id) { user in
                        UserCard(user: user) {
                            selectUser(user)
                        }
                    }
                }
                .padding(.horizontal, 24)

                // Error
                if let error = authService.error {
                    Text(error)
                        .font(.subheadline)
                        .foregroundStyle(.red)
                        .padding()
                }

                Spacer(minLength: 100)
            }
        }
    }

    // MARK: - PIN Entry View
    private func pinEntryView(for user: UserPublic) -> some View {
        VStack(spacing: 32) {
            Spacer()

            // User Avatar
            Circle()
                .fill(Color(hex: user.avatarColor) ?? .indigo)
                .frame(width: 100, height: 100)
                .overlay {
                    Text(user.displayName.prefix(1).uppercased())
                        .font(.system(size: 40, weight: .bold))
                        .foregroundColor(.white)
                }

            VStack(spacing: 4) {
                Text(user.displayName)
                    .font(.title2)
                    .fontWeight(.semibold)

                Text("@\(user.username)")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            // PIN Field
            VStack(spacing: 16) {
                SecureField("Enter PIN", text: $pin)
                    .keyboardType(.numberPad)
                    .textContentType(.password)
                    .multilineTextAlignment(.center)
                    .font(.title2)
                    .padding()
                    .background(.quaternary)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .frame(maxWidth: 200)
                    .focused($pinFocused)
                    .onSubmit {
                        login()
                    }

                if let error = authService.error {
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.red)
                }

                Button(action: login) {
                    if authService.isLoading {
                        ProgressView()
                            .tint(.white)
                    } else {
                        Text("Continue")
                            .fontWeight(.semibold)
                    }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(pin.isEmpty || authService.isLoading)
            }

            Spacer()

            // Back button
            Button {
                withAnimation {
                    showPinEntry = false
                    selectedUser = nil
                    pin = ""
                    authService.error = nil
                }
            } label: {
                Label("Choose Different User", systemImage: "arrow.left")
            }
            .padding(.bottom, 40)
        }
        .padding(.horizontal, 24)
        .onAppear {
            pinFocused = true
        }
    }

    // MARK: - Actions
    private func loadUsers() async {
        isLoading = true
        do {
            let response: UsersListResponse = try await APIClient.shared.request(.getAuthUsers)
            users = response.users
        } catch {
            authService.error = "Failed to load users"
        }
        isLoading = false
    }

    private func selectUser(_ user: UserPublic) {
        selectedUser = user
        authService.error = nil

        if user.hasPin {
            withAnimation {
                showPinEntry = true
            }
        } else {
            // No PIN required, log in directly
            Task {
                _ = await authService.login(username: user.username, pin: nil)
            }
        }
    }

    private func login() {
        guard let user = selectedUser else { return }

        Task {
            let success = await authService.login(username: user.username, pin: pin)
            if !success {
                pin = ""
            }
        }
    }
}

// MARK: - User Card
struct UserCard: View {
    let user: UserPublic
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(spacing: 12) {
                // Avatar
                Circle()
                    .fill(Color(hex: user.avatarColor) ?? .indigo)
                    .frame(width: 64, height: 64)
                    .overlay {
                        Text(user.displayName.prefix(1).uppercased())
                            .font(.title)
                            .fontWeight(.bold)
                            .foregroundColor(.white)
                    }

                // Name
                VStack(spacing: 2) {
                    Text(user.displayName)
                        .font(.subheadline)
                        .fontWeight(.medium)
                        .lineLimit(1)

                    // PIN indicator
                    if user.hasPin {
                        HStack(spacing: 2) {
                            Image(systemName: "lock.fill")
                            Text("PIN")
                        }
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                    }
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 20)
            .background(.quaternary.opacity(0.5))
            .clipShape(RoundedRectangle(cornerRadius: 16))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - API Response Models
struct UserPublic: Codable, Identifiable {
    let id: Int
    let username: String
    let displayName: String
    let avatarColor: String
    let hasPin: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case username
        case displayName = "display_name"
        case avatarColor = "avatar_color"
        case hasPin = "has_pin"
    }
}

struct UsersListResponse: Codable {
    let users: [UserPublic]
    let authMode: String

    enum CodingKeys: String, CodingKey {
        case users
        case authMode = "auth_mode"
    }
}

struct LoginAPIResponse: Codable {
    let success: Bool
    let token: String?
    let user: UserPublic?
    let message: String?
}

#Preview {
    LoginView()
}
