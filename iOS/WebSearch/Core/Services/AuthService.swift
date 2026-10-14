import Foundation
import Combine
import SwiftData

@MainActor
final class AuthService: ObservableObject {
    static let shared = AuthService()

    @Published private(set) var isAuthenticated = false
    @Published private(set) var currentUser: UserPublic?
    @Published private(set) var isLoading = false
    @Published var error: String?

    private let keychain = KeychainManager.shared

    private init() {
        // Check for existing token on init
        Task {
            await restoreSession()
        }
    }

    // MARK: - Authentication
    func login(username: String, pin: String?) async -> Bool {
        isLoading = true
        error = nil

        do {
            let response: LoginAPIResponse = try await APIClient.shared.request(.login(username: username, pin: pin))

            guard response.success, let token = response.token else {
                error = response.message ?? "Login failed"
                isLoading = false
                return false
            }

            // Save token to keychain
            try keychain.save(token, forKey: KeychainManager.Keys.authToken)

            // Set token in API client
            await APIClient.shared.setAuthToken(token)

            // Update state
            currentUser = response.user
            isAuthenticated = true
            isLoading = false

            return true
        } catch let apiError as APIError {
            error = apiError.errorDescription
            isLoading = false
            return false
        } catch {
            self.error = error.localizedDescription
            isLoading = false
            return false
        }
    }

    func logout() async {
        // Call logout endpoint
        do {
            try await APIClient.shared.requestVoid(.logout)
        } catch {
            // Continue with local logout even if API fails
            print("Logout API error: \(error)")
        }

        // Clear keychain
        try? keychain.delete(forKey: KeychainManager.Keys.authToken)
        try? keychain.delete(forKey: KeychainManager.Keys.userId)

        // Clear API client token
        await APIClient.shared.setAuthToken(nil)

        // Update state
        currentUser = nil
        isAuthenticated = false
    }

    func restoreSession() async {
        guard let token = try? keychain.readString(forKey: KeychainManager.Keys.authToken) else {
            return
        }

        // Set token in API client
        await APIClient.shared.setAuthToken(token)

        // Verify token by fetching current user
        do {
            let response: CurrentUserResponse = try await APIClient.shared.request(.getCurrentUser)
            if response.authenticated, let user = response.user {
                currentUser = user
                isAuthenticated = true
            } else {
                // Token invalid, clear it
                try? keychain.delete(forKey: KeychainManager.Keys.authToken)
                await APIClient.shared.setAuthToken(nil)
            }
        } catch {
            // Token invalid, clear it
            try? keychain.delete(forKey: KeychainManager.Keys.authToken)
            await APIClient.shared.setAuthToken(nil)
        }
    }

    // MARK: - Helpers
    var displayName: String {
        currentUser?.displayName ?? currentUser?.username ?? "User"
    }

    var avatarColor: String {
        currentUser?.avatarColor ?? "#6366f1"
    }
}

// MARK: - API Response Models
struct CurrentUserResponse: Codable {
    let authenticated: Bool
    let user: UserPublic?
}
