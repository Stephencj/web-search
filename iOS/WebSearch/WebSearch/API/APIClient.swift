import Foundation

@MainActor
class APIClient: ObservableObject {
    @Published var baseURL: String {
        didSet {
            UserDefaults.standard.set(baseURL, forKey: "serverURL")
        }
    }
    @Published var isConnected = false
    @Published var connectionError: String?
    @Published var currentUser: User?
    @Published var authToken: String? {
        didSet {
            if let token = authToken {
                UserDefaults.standard.set(token, forKey: "authToken")
            } else {
                UserDefaults.standard.removeObject(forKey: "authToken")
            }
        }
    }

    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init() {
        let savedURL = UserDefaults.standard.string(forKey: "serverURL") ?? "https://refinedaf.com"
        self.baseURL = savedURL
        self.authToken = UserDefaults.standard.string(forKey: "authToken")

        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 120
        self.session = URLSession(configuration: config)

        self.decoder = JSONDecoder()
        self.encoder = JSONEncoder()
    }

    // MARK: - Generic Request Methods

    private func request<T: Decodable>(_ method: String, _ path: String, body: (any Encodable)? = nil, queryParams: [String: String]? = nil) async throws -> T {
        var urlString = baseURL + path

        if let params = queryParams, !params.isEmpty {
            let queryString = params.map { "\($0.key)=\($0.value.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? $0.value)" }.joined(separator: "&")
            urlString += "?\(queryString)"
        }

        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = body {
            request.httpBody = try encoder.encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        if httpResponse.statusCode == 401 {
            // Unauthorized - clear auth
            authToken = nil
            currentUser = nil
            throw APIError(detail: "Unauthorized", message: nil)
        }

        if httpResponse.statusCode >= 400 {
            if let apiError = try? decoder.decode(APIError.self, from: data) {
                throw apiError
            }
            throw URLError(.badServerResponse)
        }

        return try decoder.decode(T.self, from: data)
    }

    private func get<T: Decodable>(_ path: String, queryParams: [String: String]? = nil) async throws -> T {
        try await request("GET", path, queryParams: queryParams)
    }

    private func post<T: Decodable>(_ path: String, body: (any Encodable)? = nil) async throws -> T {
        try await request("POST", path, body: body)
    }

    private func put<T: Decodable>(_ path: String, body: (any Encodable)? = nil) async throws -> T {
        try await request("PUT", path, body: body)
    }

    private func delete(_ path: String) async throws {
        guard let url = URL(string: baseURL + path) else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }

        if httpResponse.statusCode >= 400 && httpResponse.statusCode != 404 {
            if let apiError = try? decoder.decode(APIError.self, from: data) {
                throw apiError
            }
            throw URLError(.badServerResponse)
        }
    }

    // MARK: - Connection Test

    func testConnection() async {
        do {
            let _: AuthMode = try await get("/api/auth/mode")
            isConnected = true
            connectionError = nil
        } catch {
            isConnected = false
            connectionError = error.localizedDescription
        }
    }

    // MARK: - Auth

    func getAuthMode() async throws -> AuthMode {
        try await get("/api/auth/mode")
    }

    func getUsers() async throws -> [User] {
        let response: UsersResponse = try await get("/api/auth/users")
        return response.users
    }

    func login(username: String, pin: String? = nil) async throws -> LoginResponse {
        let request = LoginRequest(username: username, pin: pin)
        let response: LoginResponse = try await post("/api/auth/login", body: request)
        authToken = response.token
        currentUser = response.user
        return response
    }

    func logout() async throws {
        let _: MessageResponse = try await post("/api/auth/logout")
        authToken = nil
        currentUser = nil
    }

    func getCurrentUser() async throws -> User {
        let user: User = try await get("/api/auth/me")
        currentUser = user
        return user
    }

    func validateSession() async -> Bool {
        guard authToken != nil else { return false }
        do {
            _ = try await getCurrentUser()
            return true
        } catch {
            authToken = nil
            currentUser = nil
            return false
        }
    }

    // MARK: - Feed

    func getFeed(
        platform: String? = nil,
        watched: WatchFilter = .all,
        mode: FeedMode = .newest,
        page: Int = 1,
        perPage: Int = 20
    ) async throws -> FeedResponse {
        var params: [String: String] = [
            "page": "\(page)",
            "per_page": "\(perPage)",
            "mode": mode.rawValue
        ]

        if let platform = platform {
            params["platform"] = platform
        }

        if watched != .all {
            params["watched"] = watched.rawValue
        }

        return try await get("/api/feed", queryParams: params)
    }

    func getFeedByChannel() async throws -> FeedByChannelResponse {
        try await get("/api/feed/by-channel")
    }

    func getFeedStats() async throws -> FeedStats {
        try await get("/api/feed/stats")
    }

    func markWatched(itemId: Int) async throws -> FeedItem {
        let request = WatchedRequest(isWatched: true)
        return try await put("/api/feed/items/\(itemId)/watched", body: request)
    }

    func markUnwatched(itemId: Int) async throws -> FeedItem {
        let request = WatchedRequest(isWatched: false)
        return try await put("/api/feed/items/\(itemId)/unwatched", body: request)
    }

    func updateWatchProgress(itemId: Int, seconds: Int) async throws -> FeedItem {
        let request = ProgressRequest(watchProgressSeconds: seconds)
        return try await put("/api/feed/items/\(itemId)/progress", body: request)
    }

    func syncFeed() async throws -> MessageResponse {
        try await post("/api/feed/sync")
    }

    func getWatchHistory(limit: Int = 100) async throws -> [FeedItem] {
        let params: [String: String] = [
            "watched": "watched",
            "mode": "newest",
            "per_page": "\(limit)"
        ]
        let response: FeedResponse = try await get("/api/feed", queryParams: params)
        // Sort by watched date descending (most recent first)
        return response.items.sorted { item1, item2 in
            guard let date1 = item1.watchedAt, let date2 = item2.watchedAt else {
                return false
            }
            return date1 > date2
        }
    }

    // MARK: - Channels

    func getChannels(platform: String? = nil) async throws -> [Channel] {
        var params: [String: String]? = nil
        if let platform = platform {
            params = ["platform": platform]
        }
        let response: ChannelsResponse = try await get("/api/channels", queryParams: params)
        return response.items
    }

    func searchChannels(query: String, platform: String? = nil) async throws -> [ChannelSearchResult] {
        var params: [String: String] = ["query": query]
        if let platform = platform {
            params["platform"] = platform
        }
        return try await get("/api/channels/search", queryParams: params)
    }

    func addChannel(url: String) async throws -> Channel {
        let request = AddChannelRequest(url: url)
        return try await post("/api/channels", body: request)
    }

    func deleteChannel(id: Int) async throws {
        try await delete("/api/channels/\(id)")
    }

    func syncChannel(id: Int) async throws -> MessageResponse {
        try await post("/api/channels/\(id)/sync")
    }

    func importChannels(urls: [String]) async throws -> MessageResponse {
        let request = ImportChannelsRequest(urls: urls)
        return try await post("/api/channels/import/urls", body: request)
    }

    // MARK: - Discover

    func getPlatforms() async throws -> [Platform] {
        try await get("/api/discover/platforms")
    }

    func searchVideos(query: String, platforms: [String]? = nil, maxResults: Int = 20) async throws -> DiscoverSearchResponse {
        let request = DiscoverSearchRequest(
            query: query,
            searchType: "videos",
            platforms: platforms,
            maxResults: maxResults
        )
        return try await post("/api/discover/search", body: request)
    }

    func searchDiscoverChannels(query: String, platforms: [String]? = nil) async throws -> DiscoverSearchResponse {
        let request = DiscoverSearchRequest(
            query: query,
            searchType: "channels",
            platforms: platforms,
            maxResults: 20
        )
        return try await post("/api/discover/search", body: request)
    }

    func quickSave(url: String) async throws -> SavedVideo {
        let request = QuickSaveRequest(url: url)
        return try await post("/api/discover/quick-save", body: request)
    }

    // MARK: - Saved Videos

    func getSavedVideos(platform: String? = nil, watched: WatchFilter = .all) async throws -> [SavedVideo] {
        var params: [String: String] = [:]
        if let platform = platform {
            params["platform"] = platform
        }
        if watched != .all {
            params["watched"] = watched.rawValue
        }
        return try await get("/api/saved-videos", queryParams: params.isEmpty ? nil : params)
    }

    func saveVideoFromUrl(url: String) async throws -> SavedVideo {
        let request = SavedVideoRequest(url: url)
        return try await post("/api/saved-videos/from-url", body: request)
    }

    func deleteSavedVideo(id: Int) async throws {
        try await delete("/api/saved-videos/\(id)")
    }

    func markSavedVideoWatched(id: Int, watched: Bool) async throws -> SavedVideo {
        let request = WatchedRequest(isWatched: watched)
        return try await put("/api/saved-videos/\(id)/watched", body: request)
    }

    func updateSavedVideoProgress(id: Int, seconds: Int) async throws -> SavedVideo {
        let request = ProgressRequest(watchProgressSeconds: seconds)
        return try await put("/api/saved-videos/\(id)/progress", body: request)
    }

    func getSavedVideoStats() async throws -> SavedVideoStats {
        try await get("/api/saved-videos/stats")
    }

    // MARK: - Collections

    func getCollections() async throws -> [Collection] {
        let response: CollectionsResponse = try await get("/api/collections")
        return response.items
    }

    func getCollection(id: Int) async throws -> CollectionWithItems {
        try await get("/api/collections/\(id)")
    }

    func createCollection(name: String, description: String? = nil) async throws -> Collection {
        let request = CreateCollectionRequest(name: name, description: description)
        return try await post("/api/collections", body: request)
    }

    func deleteCollection(id: Int) async throws {
        try await delete("/api/collections/\(id)")
    }

    func addItemToCollection(collectionId: Int, item: AddCollectionItemRequest) async throws -> CollectionItem {
        try await post("/api/collections/\(collectionId)/items", body: item)
    }

    func removeItemFromCollection(collectionId: Int, itemId: Int) async throws {
        try await delete("/api/collections/\(collectionId)/items/\(itemId)")
    }

    func quickAddToFavorites(item: QuickAddRequest) async throws -> CollectionItem {
        try await post("/api/collections/quick-add", body: item)
    }

    // MARK: - Stream

    func getStreamInfo(platform: String, videoId: String, quality: String = "best") async throws -> StreamInfo {
        let params = ["quality": quality]
        return try await get("/api/stream/\(platform)/\(videoId)", queryParams: params)
    }
}
