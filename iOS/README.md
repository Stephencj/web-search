# WebSearch iOS App Development Guide

Native iOS app using Swift/SwiftUI with full feature parity to the web app.

## Technology Stack

| Layer | Technology |
|-------|------------|
| UI Framework | SwiftUI |
| Architecture | MVVM with Combine |
| Networking | URLSession + async/await |
| Local Database | SwiftData (iOS 17+) |
| Video Playback | AVKit + AVFoundation |
| Background Audio | AVAudioSession + Background Modes |
| Image Loading | AsyncImage + NSCache |
| Keychain | For auth tokens |

---

## Project Structure

```
WebSearch/
├── App/
│   ├── WebSearchApp.swift          # App entry point
│   └── AppDelegate.swift           # Background/push handling
├── Core/
│   ├── Models/                     # SwiftData models
│   │   ├── User.swift
│   │   ├── Channel.swift
│   │   ├── FeedItem.swift
│   │   ├── SavedVideo.swift
│   │   ├── Collection.swift
│   │   └── WatchState.swift
│   ├── Services/
│   │   ├── APIClient.swift         # Network layer
│   │   ├── AuthService.swift       # Authentication
│   │   ├── SyncService.swift       # Local/remote sync
│   │   ├── CacheService.swift      # Offline cache
│   │   └── PlayerService.swift     # Global player state
│   └── Utilities/
│       ├── KeychainManager.swift
│       ├── DateFormatter+Ext.swift
│       └── URL+Platform.swift
├── Features/
│   ├── Feed/
│   │   ├── FeedView.swift
│   │   ├── FeedViewModel.swift
│   │   ├── FeedItemRow.swift
│   │   └── FeedFilterSheet.swift
│   ├── Discover/
│   │   ├── DiscoverView.swift
│   │   ├── DiscoverViewModel.swift
│   │   └── VideoSearchResults.swift
│   ├── Subscriptions/
│   │   ├── SubscriptionsView.swift
│   │   ├── ChannelRow.swift
│   │   └── AddChannelSheet.swift
│   ├── Saved/
│   │   ├── SavedVideosView.swift
│   │   └── SavedVideoRow.swift
│   ├── Collections/
│   │   ├── CollectionsView.swift
│   │   ├── CollectionDetailView.swift
│   │   └── AddToCollectionSheet.swift
│   ├── History/
│   │   ├── HistoryView.swift
│   │   └── HistoryRow.swift
│   ├── Player/
│   │   ├── VideoPlayerView.swift
│   │   ├── MiniPlayerView.swift
│   │   ├── PlayerControls.swift
│   │   └── NowPlayingInfo.swift
│   ├── Settings/
│   │   ├── SettingsView.swift
│   │   ├── AccountsView.swift
│   │   └── PreferencesView.swift
│   └── Auth/
│       ├── LoginView.swift
│       └── UserSwitcher.swift
└── Resources/
    ├── Assets.xcassets
    └── Info.plist
```

---

## Getting Started

### 1. Create Xcode Project

1. Open Xcode
2. File → New → Project
3. Select "App" under iOS
4. Configure:
   - Product Name: `WebSearch`
   - Team: Your Apple Developer Team
   - Organization Identifier: `com.yourname`
   - Interface: SwiftUI
   - Language: Swift
   - Storage: SwiftData
   - Include Tests: Yes

### 2. Configure Info.plist

Add these entries for background audio and capabilities:

```xml
<key>UIBackgroundModes</key>
<array>
    <string>audio</string>
    <string>fetch</string>
</array>
```

### 3. Add Capabilities

In Xcode → Target → Signing & Capabilities:
- Background Modes (Audio, Background fetch)
- Keychain Sharing (for secure token storage)

---

## Core Data Models (SwiftData)

### User.swift
```swift
import SwiftData

@Model
class User {
    @Attribute(.unique) var id: Int
    var username: String
    var displayName: String?
    var avatarColor: String
    var isAdmin: Bool
    var lastLoginAt: Date?

    @Relationship(deleteRule: .cascade) var watchStates: [WatchState]
    @Relationship(deleteRule: .cascade) var savedVideos: [SavedVideo]
    @Relationship(deleteRule: .cascade) var collections: [Collection]

    init(id: Int, username: String, displayName: String? = nil, avatarColor: String = "#6366f1", isAdmin: Bool = false) {
        self.id = id
        self.username = username
        self.displayName = displayName
        self.avatarColor = avatarColor
        self.isAdmin = isAdmin
    }
}
```

### Channel.swift
```swift
import SwiftData

@Model
class Channel {
    @Attribute(.unique) var id: Int
    var platform: String  // youtube, rumble, podcast
    var channelId: String
    var url: String
    var name: String
    var avatarUrl: String?
    var subscriberCount: Int?
    var videoCount: Int?
    var isActive: Bool
    var lastSyncedAt: Date?
    var syncError: String?

    @Relationship(deleteRule: .cascade) var feedItems: [FeedItem]

    init(id: Int, platform: String, channelId: String, url: String, name: String) {
        self.id = id
        self.platform = platform
        self.channelId = channelId
        self.url = url
        self.name = name
        self.isActive = true
    }
}
```

### FeedItem.swift
```swift
import SwiftData

@Model
class FeedItem {
    @Attribute(.unique) var id: Int
    var platform: String
    var videoId: String
    var videoUrl: String
    var title: String
    var thumbnailUrl: String?
    var channelName: String?
    var durationSeconds: Int?
    var viewCount: Int?
    var uploadDate: Date?
    var discoveredAt: Date

    var channel: Channel?
    @Relationship var watchState: WatchState?

    init(id: Int, platform: String, videoId: String, videoUrl: String, title: String) {
        self.id = id
        self.platform = platform
        self.videoId = videoId
        self.videoUrl = videoUrl
        self.title = title
        self.discoveredAt = Date()
    }
}
```

### WatchState.swift
```swift
import SwiftData

@Model
class WatchState {
    var isWatched: Bool
    var watchProgressSeconds: Int?
    var watchedAt: Date?
    var updatedAt: Date

    var user: User?
    var feedItem: FeedItem?

    init(isWatched: Bool = false) {
        self.isWatched = isWatched
        self.updatedAt = Date()
    }
}
```

### SavedVideo.swift
```swift
import SwiftData

@Model
class SavedVideo {
    @Attribute(.unique) var id: Int
    var platform: String
    var videoId: String
    var videoUrl: String
    var title: String
    var thumbnailUrl: String?
    var channelName: String?
    var durationSeconds: Int?
    var isWatched: Bool
    var watchProgressSeconds: Int?
    var savedAt: Date
    var notes: String?

    var user: User?

    init(id: Int, platform: String, videoId: String, videoUrl: String, title: String) {
        self.id = id
        self.platform = platform
        self.videoId = videoId
        self.videoUrl = videoUrl
        self.title = title
        self.isWatched = false
        self.savedAt = Date()
    }
}
```

### Collection.swift
```swift
import SwiftData

@Model
class Collection {
    @Attribute(.unique) var id: Int
    var name: String
    var descriptionText: String?
    var coverUrl: String?
    var itemCount: Int
    var createdAt: Date

    var user: User?
    @Relationship(deleteRule: .cascade) var items: [CollectionItem]

    init(id: Int, name: String) {
        self.id = id
        self.name = name
        self.itemCount = 0
        self.createdAt = Date()
    }
}

@Model
class CollectionItem {
    @Attribute(.unique) var id: Int
    var videoId: String
    var videoUrl: String
    var title: String
    var thumbnailUrl: String?
    var addedAt: Date

    var collection: Collection?

    init(id: Int, videoId: String, videoUrl: String, title: String) {
        self.id = id
        self.videoId = videoId
        self.videoUrl = videoUrl
        self.title = title
        self.addedAt = Date()
    }
}
```

---

## API Client

### APIClient.swift
```swift
import Foundation

enum APIError: Error {
    case invalidURL
    case invalidResponse
    case unauthorized
    case networkError(Error)
    case decodingError(Error)
}

enum HTTPMethod: String {
    case GET, POST, PUT, DELETE, PATCH
}

actor APIClient {
    static let shared = APIClient()

    private let baseURL: URL
    private var authToken: String?

    private init() {
        // Configure your server URL
        #if DEBUG
        self.baseURL = URL(string: "http://localhost:8000/api")!
        #else
        self.baseURL = URL(string: "https://refinedaf.com/api")!
        #endif
    }

    func setAuthToken(_ token: String?) {
        self.authToken = token
    }

    func request<T: Decodable>(_ endpoint: Endpoint) async throws -> T {
        var request = URLRequest(url: baseURL.appendingPathComponent(endpoint.path))
        request.httpMethod = endpoint.method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let body = endpoint.body {
            request.httpBody = try JSONEncoder().encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard 200..<300 ~= httpResponse.statusCode else {
            if httpResponse.statusCode == 401 {
                throw APIError.unauthorized
            }
            throw APIError.invalidResponse
        }

        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }
}

// MARK: - Endpoints
enum Endpoint {
    case getFeed(filter: String?, platform: String?, mode: String?, page: Int)
    case markWatched(id: Int, watched: Bool)
    case updateProgress(id: Int, seconds: Int)
    case getChannels
    case addChannel(url: String)
    case syncChannel(id: Int)
    case deleteChannel(id: Int)
    case getSavedVideos
    case saveVideo(videoUrl: String)
    case unsaveVideo(id: Int)
    case getCollections
    case createCollection(name: String)
    case discoverVideos(query: String, platforms: [String])
    case login(username: String, password: String)
    case getUsers

    var path: String {
        switch self {
        case .getFeed: return "/feed"
        case .markWatched(let id, _): return "/feed/\(id)/watched"
        case .updateProgress(let id, _): return "/feed/\(id)/progress"
        case .getChannels: return "/subscriptions"
        case .addChannel: return "/subscriptions"
        case .syncChannel(let id): return "/subscriptions/\(id)/sync"
        case .deleteChannel(let id): return "/subscriptions/\(id)"
        case .getSavedVideos: return "/saved-videos"
        case .saveVideo: return "/saved-videos"
        case .unsaveVideo(let id): return "/saved-videos/\(id)"
        case .getCollections: return "/collections"
        case .createCollection: return "/collections"
        case .discoverVideos: return "/discover/search"
        case .login: return "/auth/login"
        case .getUsers: return "/users"
        }
    }

    var method: HTTPMethod {
        switch self {
        case .getFeed, .getChannels, .getSavedVideos, .getCollections, .getUsers:
            return .GET
        case .addChannel, .saveVideo, .createCollection, .discoverVideos, .login, .syncChannel:
            return .POST
        case .markWatched, .updateProgress:
            return .PATCH
        case .deleteChannel, .unsaveVideo:
            return .DELETE
        }
    }

    var body: Encodable? {
        switch self {
        case .addChannel(let url):
            return ["url": url]
        case .saveVideo(let videoUrl):
            return ["video_url": videoUrl]
        case .createCollection(let name):
            return ["name": name]
        case .discoverVideos(let query, let platforms):
            return ["query": query, "platforms": platforms]
        case .markWatched(_, let watched):
            return ["is_watched": watched]
        case .updateProgress(_, let seconds):
            return ["watch_progress_seconds": seconds]
        default:
            return nil
        }
    }
}
```

---

## Key Views

### App Entry Point
```swift
import SwiftUI
import SwiftData

@main
struct WebSearchApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(for: [User.self, Channel.self, FeedItem.self, SavedVideo.self, Collection.self, WatchState.self])
    }
}
```

### Main Tab View
```swift
import SwiftUI

struct ContentView: View {
    @StateObject private var playerService = PlayerService.shared

    var body: some View {
        ZStack(alignment: .bottom) {
            TabView {
                FeedView()
                    .tabItem { Label("Feed", systemImage: "play.rectangle.fill") }

                DiscoverView()
                    .tabItem { Label("Discover", systemImage: "magnifyingglass") }

                SavedVideosView()
                    .tabItem { Label("Saved", systemImage: "bookmark.fill") }

                SubscriptionsView()
                    .tabItem { Label("Channels", systemImage: "person.2.fill") }

                SettingsView()
                    .tabItem { Label("Settings", systemImage: "gear") }
            }

            // Mini player overlay
            if playerService.currentVideo != nil && !playerService.isFullScreen {
                MiniPlayerView()
                    .transition(.move(edge: .bottom))
            }
        }
    }
}
```

### Feed View
```swift
import SwiftUI

struct FeedView: View {
    @StateObject private var viewModel = FeedViewModel()

    var body: some View {
        NavigationStack {
            List {
                ForEach(viewModel.feedItems) { item in
                    FeedItemRow(item: item)
                        .swipeActions(edge: .trailing) {
                            Button {
                                viewModel.toggleWatched(item)
                            } label: {
                                Label(item.isWatched ? "Unwatched" : "Watched",
                                      systemImage: item.isWatched ? "eye.slash" : "eye")
                            }
                            .tint(item.isWatched ? .orange : .green)
                        }
                        .swipeActions(edge: .leading) {
                            Button {
                                viewModel.saveVideo(item)
                            } label: {
                                Label("Save", systemImage: "bookmark")
                            }
                            .tint(.blue)
                        }
                }
            }
            .refreshable {
                await viewModel.refresh()
            }
            .navigationTitle("Feed")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Menu {
                        ForEach(FeedMode.allCases, id: \.self) { mode in
                            Button(mode.rawValue) {
                                viewModel.setMode(mode)
                            }
                        }
                    } label: {
                        Label("Mode", systemImage: "line.3.horizontal.decrease.circle")
                    }
                }
            }
        }
        .task {
            await viewModel.loadFeed()
        }
    }
}

enum FeedMode: String, CaseIterable {
    case newest = "Newest"
    case catchUp = "Catch Up"
    case discovery = "Discovery"
    case shortForm = "Short Form"
}
```

---

## Background Audio Implementation

### AppDelegate.swift
```swift
import UIKit
import AVFoundation

class AppDelegate: NSObject, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey : Any]? = nil) -> Bool {
        configureAudioSession()
        return true
    }

    private func configureAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try session.setActive(true)
        } catch {
            print("Failed to configure audio session: \(error)")
        }
    }
}
```

### PlayerService.swift
```swift
import AVKit
import MediaPlayer
import Combine

@MainActor
class PlayerService: ObservableObject {
    static let shared = PlayerService()

    @Published var currentVideo: FeedItem?
    @Published var isPlaying = false
    @Published var isFullScreen = false
    @Published var currentTime: Double = 0
    @Published var duration: Double = 0

    private var player: AVPlayer?
    private var timeObserver: Any?

    private init() {
        setupRemoteCommands()
    }

    func play(video: FeedItem) {
        currentVideo = video

        // Create player with video URL
        guard let url = URL(string: video.videoUrl) else { return }
        player = AVPlayer(url: url)
        player?.play()
        isPlaying = true

        setupTimeObserver()
        updateNowPlayingInfo()
    }

    func togglePlayPause() {
        if isPlaying {
            player?.pause()
        } else {
            player?.play()
        }
        isPlaying.toggle()
        updatePlaybackState()
    }

    func seek(by seconds: Double) {
        guard let player = player else { return }
        let newTime = player.currentTime().seconds + seconds
        player.seek(to: CMTime(seconds: max(0, newTime), preferredTimescale: 1))
    }

    private func setupRemoteCommands() {
        let center = MPRemoteCommandCenter.shared()

        center.playCommand.addTarget { [weak self] _ in
            self?.player?.play()
            self?.isPlaying = true
            return .success
        }

        center.pauseCommand.addTarget { [weak self] _ in
            self?.player?.pause()
            self?.isPlaying = false
            return .success
        }

        center.skipForwardCommand.preferredIntervals = [15]
        center.skipForwardCommand.addTarget { [weak self] _ in
            self?.seek(by: 15)
            return .success
        }

        center.skipBackwardCommand.preferredIntervals = [15]
        center.skipBackwardCommand.addTarget { [weak self] _ in
            self?.seek(by: -15)
            return .success
        }
    }

    private func updateNowPlayingInfo() {
        guard let video = currentVideo else { return }

        var info = [String: Any]()
        info[MPMediaItemPropertyTitle] = video.title
        info[MPMediaItemPropertyArtist] = video.channelName ?? "Unknown"
        info[MPNowPlayingInfoPropertyElapsedPlaybackTime] = currentTime
        info[MPMediaItemPropertyPlaybackDuration] = duration
        info[MPNowPlayingInfoPropertyPlaybackRate] = isPlaying ? 1.0 : 0.0

        // Load artwork async
        if let thumbnailUrl = video.thumbnailUrl, let url = URL(string: thumbnailUrl) {
            Task {
                if let (data, _) = try? await URLSession.shared.data(from: url),
                   let image = UIImage(data: data) {
                    let artwork = MPMediaItemArtwork(boundsSize: image.size) { _ in image }
                    info[MPMediaItemPropertyArtwork] = artwork
                    MPNowPlayingInfoCenter.default().nowPlayingInfo = info
                }
            }
        }

        MPNowPlayingInfoCenter.default().nowPlayingInfo = info
    }

    private func updatePlaybackState() {
        var info = MPNowPlayingInfoCenter.default().nowPlayingInfo ?? [:]
        info[MPNowPlayingInfoPropertyElapsedPlaybackTime] = currentTime
        info[MPNowPlayingInfoPropertyPlaybackRate] = isPlaying ? 1.0 : 0.0
        MPNowPlayingInfoCenter.default().nowPlayingInfo = info
    }

    private func setupTimeObserver() {
        timeObserver = player?.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 1, preferredTimescale: 1),
            queue: .main
        ) { [weak self] time in
            self?.currentTime = time.seconds
            if let duration = self?.player?.currentItem?.duration.seconds, !duration.isNaN {
                self?.duration = duration
            }
        }
    }
}
```

---

## Sync Strategy

```
┌─────────────────────────────────────────────────────┐
│                    SyncService                       │
├─────────────────────────────────────────────────────┤
│  On App Launch:                                      │
│  1. Load cached data from SwiftData                 │
│  2. Display immediately (offline-first)             │
│  3. Background fetch from API                       │
│  4. Merge changes, update UI                        │
├─────────────────────────────────────────────────────┤
│  On Pull-to-Refresh:                                │
│  1. Fetch fresh data from API                       │
│  2. Update local database                           │
│  3. Resolve conflicts (server wins)                 │
├─────────────────────────────────────────────────────┤
│  On User Action (mark watched, save, etc.):         │
│  1. Update local database immediately              │
│  2. Queue API request                               │
│  3. Retry on failure (exponential backoff)          │
│  4. Sync when back online                           │
└─────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation
- [ ] Xcode project setup with SwiftUI
- [ ] SwiftData models and schema
- [ ] APIClient with auth
- [ ] Basic navigation (TabView)
- [ ] Login/user selection view

### Phase 2: Core Feed
- [ ] Feed view with list
- [ ] Feed filtering and modes
- [ ] Pull-to-refresh sync
- [ ] Mark watched/unwatched
- [ ] Pagination

### Phase 3: Video Player
- [ ] AVPlayer integration
- [ ] Full-screen player view
- [ ] Mini player overlay
- [ ] Background audio
- [ ] Lock screen controls
- [ ] Progress tracking

### Phase 4: Subscriptions
- [ ] Channel list view
- [ ] Add channel (URL/search)
- [ ] Sync channels
- [ ] Channel management

### Phase 5: Discovery & Saved
- [ ] Discover search view
- [ ] Platform search tabs
- [ ] Save videos
- [ ] Saved videos view
- [ ] Collections

### Phase 6: Polish
- [ ] Settings view
- [ ] Theme support (dark/light)
- [ ] History view
- [ ] Offline cache
- [ ] Error handling
- [ ] Loading states

### Phase 7: App Store
- [ ] App icons and assets
- [ ] Screenshots
- [ ] App Store listing
- [ ] TestFlight beta
- [ ] Submit for review

---

## Backend Connection

The iOS app connects to the same Python FastAPI backend:

```
iOS App  ──────►  https://refinedaf.com/api/
                         │
                         ▼
              ┌──────────────────────┐
              │   FastAPI Backend    │
              │   (existing)         │
              └──────────────────────┘
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
         SQLite DB            External APIs
         (server)             (YouTube, etc.)
```

For development, you can use:
1. `http://localhost:8000` (Mac running backend)
2. `http://192.168.x.x:8000` (local network IP)
3. ngrok tunnel for remote testing

---

## Resources

- [SwiftUI Documentation](https://developer.apple.com/documentation/swiftui)
- [SwiftData Documentation](https://developer.apple.com/documentation/swiftdata)
- [AVFoundation Guide](https://developer.apple.com/documentation/avfoundation)
- [Now Playing Guide](https://developer.apple.com/documentation/mediaplayer/becoming_a_now_playable_app)
