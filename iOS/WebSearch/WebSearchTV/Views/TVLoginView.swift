import SwiftUI

struct TVLoginView: View {
    @EnvironmentObject var apiClient: APIClient

    @State private var users: [User] = []
    @State private var selectedUser: User?
    @State private var showPinEntry = false
    @State private var pin = ""
    @State private var isLoading = false
    @State private var error: String?

    private let columns = [
        GridItem(.adaptive(minimum: 200, maximum: 250), spacing: 40)
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 40) {
                Text("Who's Watching?")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                if isLoading && users.isEmpty {
                    ProgressView("Loading users...")
                } else if users.isEmpty {
                    Text("No users found")
                        .foregroundStyle(.secondary)
                } else {
                    LazyVGrid(columns: columns, spacing: 40) {
                        ForEach(users) { user in
                            UserAvatarButton(user: user) {
                                selectUser(user)
                            }
                        }
                    }
                    .padding(.horizontal, 80)
                }

                if let error = error {
                    Text(error)
                        .foregroundStyle(.red)
                        .font(.callout)
                }

                Spacer()

                // Server info
                VStack(spacing: 8) {
                    Text("Server: \(apiClient.baseURL)")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if !apiClient.isConnected {
                        Text("Not connected to server")
                            .font(.caption)
                            .foregroundStyle(.red)
                    }
                }
            }
            .padding(.top, 60)
            .fullScreenCover(isPresented: $showPinEntry) {
                if let user = selectedUser {
                    TVPinEntryView(user: user, onSubmit: { enteredPin in
                        login(user: user, pin: enteredPin)
                    }, onCancel: {
                        showPinEntry = false
                        selectedUser = nil
                        pin = ""
                    })
                }
            }
        }
        .task {
            await loadUsers()
        }
    }

    private func loadUsers() async {
        isLoading = true
        error = nil

        do {
            users = try await apiClient.getUsers()
        } catch {
            self.error = "Failed to load users: \(error.localizedDescription)"
        }

        isLoading = false
    }

    private func selectUser(_ user: User) {
        selectedUser = user

        if user.hasPin == true {
            showPinEntry = true
        } else {
            login(user: user, pin: nil)
        }
    }

    private func login(user: User, pin: String?) {
        isLoading = true
        error = nil

        Task {
            do {
                _ = try await apiClient.login(username: user.username, pin: pin)
                showPinEntry = false
            } catch {
                self.error = "Login failed: \(error.localizedDescription)"
            }
            isLoading = false
        }
    }
}

// MARK: - User Avatar Button

struct UserAvatarButton: View {
    let user: User
    let action: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        Button(action: action) {
            VStack(spacing: 16) {
                // Avatar circle
                Circle()
                    .fill(Color(hex: user.avatarColor) ?? .blue)
                    .frame(width: 120, height: 120)
                    .overlay {
                        Text(user.initials)
                            .font(.system(size: 40, weight: .bold))
                            .foregroundStyle(.white)
                    }
                    .shadow(radius: isFocused ? 20 : 5)

                // Name
                Text(user.displayName ?? user.username)
                    .font(.headline)
                    .lineLimit(1)
            }
        }
        .buttonStyle(.plain)
        .scaleEffect(isFocused ? 1.1 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isFocused)
        .focused($isFocused)
    }
}

// MARK: - PIN Entry View

struct TVPinEntryView: View {
    let user: User
    let onSubmit: (String) -> Void
    let onCancel: () -> Void

    @State private var pin = ""
    @FocusState private var focusedDigit: Int?

    private let pinLength = 4

    var body: some View {
        VStack(spacing: 40) {
            Text("Enter PIN for \(user.displayName ?? user.username)")
                .font(.title2)

            // PIN display
            HStack(spacing: 20) {
                ForEach(0..<pinLength, id: \.self) { index in
                    PinDigitView(
                        digit: digit(at: index),
                        isFilled: index < pin.count
                    )
                }
            }

            // Number pad
            LazyVGrid(columns: Array(repeating: GridItem(.fixed(100)), count: 3), spacing: 20) {
                ForEach(1...9, id: \.self) { number in
                    NumberButton(number: "\(number)") {
                        appendDigit("\(number)")
                    }
                }

                // Empty space
                Color.clear.frame(width: 100, height: 80)

                NumberButton(number: "0") {
                    appendDigit("0")
                }

                // Delete button
                Button {
                    deleteDigit()
                } label: {
                    Image(systemName: "delete.left")
                        .font(.title)
                        .frame(width: 100, height: 80)
                }
                .buttonStyle(.plain)
            }

            HStack(spacing: 40) {
                Button("Cancel", action: onCancel)
                    .buttonStyle(.bordered)

                Button("Submit") {
                    onSubmit(pin)
                }
                .buttonStyle(.borderedProminent)
                .disabled(pin.count < pinLength)
            }
        }
        .padding(60)
    }

    private func digit(at index: Int) -> String? {
        guard index < pin.count else { return nil }
        let pinIndex = pin.index(pin.startIndex, offsetBy: index)
        return String(pin[pinIndex])
    }

    private func appendDigit(_ digit: String) {
        guard pin.count < pinLength else { return }
        pin += digit

        if pin.count == pinLength {
            onSubmit(pin)
        }
    }

    private func deleteDigit() {
        guard !pin.isEmpty else { return }
        pin.removeLast()
    }
}

struct PinDigitView: View {
    let digit: String?
    let isFilled: Bool

    var body: some View {
        Circle()
            .fill(isFilled ? Color.primary : Color.secondary.opacity(0.3))
            .frame(width: 24, height: 24)
    }
}

struct NumberButton: View {
    let number: String
    let action: () -> Void

    @FocusState private var isFocused: Bool

    var body: some View {
        Button(action: action) {
            Text(number)
                .font(.title)
                .fontWeight(.semibold)
                .frame(width: 100, height: 80)
                .background(isFocused ? Color.blue : Color.secondary.opacity(0.2))
                .clipShape(RoundedRectangle(cornerRadius: 12))
        }
        .buttonStyle(.plain)
        .focused($isFocused)
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
    TVLoginView()
        .environmentObject(APIClient())
}
