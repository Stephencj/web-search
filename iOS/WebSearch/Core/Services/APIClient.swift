import Foundation

// MARK: - API Errors
enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case notFound
    case serverError(Int)
    case networkError(Error)
    case decodingError(Error)
    case encodingError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .unauthorized:
            return "Authentication required"
        case .notFound:
            return "Resource not found"
        case .serverError(let code):
            return "Server error: \(code)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .encodingError(let error):
            return "Failed to encode request: \(error.localizedDescription)"
        }
    }
}

// MARK: - HTTP Method
enum HTTPMethod: String {
    case GET, POST, PUT, DELETE, PATCH
}

// MARK: - API Endpoints
enum Endpoint {
    // Feed
    case getFeed(filter: String?, platform: String?, mode: String?, page: Int, perPage: Int)
    case markWatched(id: Int, watched: Bool)
    case updateProgress(id: Int, seconds: Int)

    // Channels/Subscriptions
    case getChannels
    case addChannel(url: String)
    case syncChannel(id: Int)
    case deleteChannel(id: Int)

    // Saved Videos
    case getSavedVideos
    case saveVideo(videoUrl: String)
    case unsaveVideo(id: Int)

    // Collections
    case getCollections
    case getCollection(id: Int)
    case createCollection(name: String, description: String?)
    case deleteCollection(id: Int)
    case addToCollection(collectionId: Int, videoUrl: String)
    case removeFromCollection(collectionId: Int, itemId: Int)

    // Discovery
    case discoverVideos(query: String, platforms: [String], page: Int)

    // Auth
    case getAuthUsers
    case login(username: String, pin: String?)
    case getCurrentUser
    case logout

    var path: String {
        switch self {
        case .getFeed:
            return "/feed"
        case .markWatched(let id, _):
            return "/feed/\(id)/watched"
        case .updateProgress(let id, _):
            return "/feed/\(id)/progress"
        case .getChannels, .addChannel:
            return "/subscriptions"
        case .syncChannel(let id):
            return "/subscriptions/\(id)/sync"
        case .deleteChannel(let id):
            return "/subscriptions/\(id)"
        case .getSavedVideos, .saveVideo:
            return "/saved-videos"
        case .unsaveVideo(let id):
            return "/saved-videos/\(id)"
        case .getCollections, .createCollection:
            return "/collections"
        case .getCollection(let id):
            return "/collections/\(id)"
        case .deleteCollection(let id):
            return "/collections/\(id)"
        case .addToCollection(let collectionId, _):
            return "/collections/\(collectionId)/items"
        case .removeFromCollection(let collectionId, let itemId):
            return "/collections/\(collectionId)/items/\(itemId)"
        case .discoverVideos:
            return "/discover/search"
        case .getAuthUsers:
            return "/auth/users"
        case .login:
            return "/auth/login"
        case .getCurrentUser:
            return "/auth/me"
        case .logout:
            return "/auth/logout"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .getFeed, .getChannels, .getSavedVideos, .getCollections, .getCollection,
             .getAuthUsers, .getCurrentUser:
            return .GET
        case .addChannel, .saveVideo, .createCollection, .addToCollection,
             .discoverVideos, .login, .syncChannel, .logout:
            return .POST
        case .markWatched, .updateProgress:
            return .PATCH
        case .deleteChannel, .unsaveVideo, .deleteCollection, .removeFromCollection:
            return .DELETE
        }
    }

    var queryItems: [URLQueryItem]? {
        switch self {
        case .getFeed(let filter, let platform, let mode, let page, let perPage):
            var items: [URLQueryItem] = [
                URLQueryItem(name: "page", value: String(page)),
                URLQueryItem(name: "per_page", value: String(perPage))
            ]
            if let filter = filter {
                items.append(URLQueryItem(name: "filter", value: filter))
            }
            if let platform = platform {
                items.append(URLQueryItem(name: "platform", value: platform))
            }
            if let mode = mode {
                items.append(URLQueryItem(name: "mode", value: mode))
            }
            return items
        default:
            return nil
        }
    }

    var body: [String: Any]? {
        switch self {
        case .addChannel(let url):
            return ["url": url]
        case .saveVideo(let videoUrl):
            return ["video_url": videoUrl]
        case .createCollection(let name, let description):
            var body: [String: Any] = ["name": name]
            if let desc = description {
                body["description"] = desc
            }
            return body
        case .addToCollection(_, let videoUrl):
            return ["video_url": videoUrl]
        case .discoverVideos(let query, let platforms, let page):
            return [
                "query": query,
                "platforms": platforms,
                "page": page
            ]
        case .markWatched(_, let watched):
            return ["is_watched": watched]
        case .updateProgress(_, let seconds):
            return ["watch_progress_seconds": seconds]
        case .login(let username, let pin):
            var body: [String: Any] = ["username": username]
            if let pin = pin {
                body["pin"] = pin
            }
            return body
        default:
            return nil
        }
    }
}

// MARK: - API Client
actor APIClient {
    static let shared = APIClient()

    private let baseURL: URL
    private var authToken: String?
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    private init() {
        #if DEBUG
        // For development, use localhost or configure your dev server
        self.baseURL = URL(string: "http://localhost:8000/api")!
        #else
        self.baseURL = URL(string: "https://refinedaf.com/api")!
        #endif

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let dateString = try container.decode(String.self)

            // Try ISO8601 with fractional seconds
            let formatter = ISO8601DateFormatter()
            formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
            if let date = formatter.date(from: dateString) {
                return date
            }

            // Try ISO8601 without fractional seconds
            formatter.formatOptions = [.withInternetDateTime]
            if let date = formatter.date(from: dateString) {
                return date
            }

            // Try simple date format
            let simpleFormatter = DateFormatter()
            simpleFormatter.dateFormat = "yyyy-MM-dd"
            if let date = simpleFormatter.date(from: dateString) {
                return date
            }

            throw DecodingError.dataCorruptedError(
                in: container,
                debugDescription: "Cannot decode date: \(dateString)"
            )
        }

        self.encoder = JSONEncoder()
    }

    // MARK: - Token Management
    func setAuthToken(_ token: String?) {
        self.authToken = token
    }

    func getAuthToken() -> String? {
        return authToken
    }

    // MARK: - Request Methods
    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        let request = try buildRequest(for: endpoint)
        return try await execute(request)
    }

    func requestData(_ endpoint: Endpoint) async throws -> Data {
        let request = try buildRequest(for: endpoint)
        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        try validateResponse(httpResponse)
        return data
    }

    func requestVoid(_ endpoint: Endpoint) async throws {
        let request = try buildRequest(for: endpoint)
        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        try validateResponse(httpResponse)
    }

    // MARK: - Private Methods
    private func buildRequest(for endpoint: Endpoint) throws -> URLRequest {
        var urlComponents = URLComponents(url: baseURL.appendingPathComponent(endpoint.path), resolvingAgainstBaseURL: false)

        if let queryItems = endpoint.queryItems {
            urlComponents?.queryItems = queryItems
        }

        guard let url = urlComponents?.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 30

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = endpoint.body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            do {
                request.httpBody = try JSONSerialization.data(withJSONObject: body)
            } catch {
                throw APIError.encodingError(error)
            }
        }

        return request
    }

    private func execute<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        try validateResponse(httpResponse)

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            #if DEBUG
            if let jsonString = String(data: data, encoding: .utf8) {
                print("Failed to decode response: \(jsonString)")
            }
            #endif
            throw APIError.decodingError(error)
        }
    }

    private func validateResponse(_ response: HTTPURLResponse) throws {
        switch response.statusCode {
        case 200..<300:
            return
        case 401:
            throw APIError.unauthorized
        case 404:
            throw APIError.notFound
        case 500..<600:
            throw APIError.serverError(response.statusCode)
        default:
            throw APIError.invalidResponse
        }
    }
}

// MARK: - Convenience Extensions
extension APIClient {
    func getFeed(
        filter: String? = nil,
        platform: String? = nil,
        mode: String? = nil,
        page: Int = 1,
        perPage: Int = 20
    ) async throws -> FeedResponse {
        try await request(.getFeed(filter: filter, platform: platform, mode: mode, page: page, perPage: perPage))
    }

    func markWatched(id: Int, watched: Bool) async throws {
        try await requestVoid(.markWatched(id: id, watched: watched))
    }

    func updateProgress(id: Int, seconds: Int) async throws {
        try await requestVoid(.updateProgress(id: id, seconds: seconds))
    }

    func getChannels() async throws -> [ChannelResponse] {
        try await request(.getChannels)
    }

    func getSavedVideos() async throws -> [SavedVideoResponse] {
        try await request(.getSavedVideos)
    }

    func getCollections() async throws -> [CollectionResponse] {
        try await request(.getCollections)
    }
}
