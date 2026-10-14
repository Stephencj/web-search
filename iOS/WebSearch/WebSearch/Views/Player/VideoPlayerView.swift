import SwiftUI
import AVKit
import AVFoundation

struct VideoPlayerView: View {
    @EnvironmentObject var apiClient: APIClient
    @Environment(\.dismiss) private var dismiss
    @StateObject private var playerService = PlayerService.shared

    let video: FeedItem
    @Binding var isPresented: Bool

    // Player is now managed by PlayerService for mini player control
    private var player: AVPlayer? { playerService.player }

    @State private var isLoading = true
    @State private var error: String?
    @State private var streamInfo: StreamInfo?
    @State private var useWebFallback = false
    @State private var progressTimer: Timer?
    @State private var currentQuality: String = "Loading..."
    @State private var showAddToCollection = false
    @State private var collections: [Collection] = []
    @State private var isUpgradingQuality = false

    // MARK: - Device-Adaptive Quality Settings

    /// True if running on iPhone (smaller screen, optimize for speed)
    private var isPhone: Bool {
        UIDevice.current.userInterfaceIdiom == .phone
    }

    /// Initial quality for fastest load: 480p on phones, 720p on tablets
    private var initialQuality: String {
        isPhone ? "480p" : "720p"
    }

    /// Max quality to upgrade to: 720p on phones (saves bandwidth), best on tablets
    private var maxQuality: String {
        isPhone ? "720p" : "best"
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if isLoading {
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.5)
                        .tint(.white)
                    Text("Loading stream...")
                        .foregroundStyle(.white)
                        .font(.subheadline)
                }
            } else if useWebFallback {
                WebVideoPlayerView(video: video, isPresented: $isPresented)
            } else if let player = player {
                // Use AVPlayerViewController for proper PiP support
                AVPlayerControllerView(player: player)
                    .ignoresSafeArea()
                    .onAppear {
                        // Player is already playing from loadStream()
                        // Just start progress tracking
                        startProgressTracking()
                    }
                    .onDisappear {
                        stopProgressTracking()
                        saveProgress()
                    }
            } else if let error = error {
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 50))
                        .foregroundStyle(.yellow)

                    Text("Playback Error")
                        .font(.headline)
                        .foregroundStyle(.white)

                    Text(error)
                        .font(.subheadline)
                        .foregroundStyle(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    Button("Try Web Player") {
                        useWebFallback = true
                    }
                    .buttonStyle(.borderedProminent)
                    .padding(.top)
                }
            }

            // Overlay controls (only show when loading or error)
            if isLoading || error != nil {
                VStack {
                    HStack {
                        Button {
                            isPresented = false
                        } label: {
                            Image(systemName: "xmark.circle.fill")
                                .font(.title)
                                .foregroundStyle(.white.opacity(0.8))
                                .background(Circle().fill(.black.opacity(0.3)))
                        }
                        .padding()

                        Spacer()
                    }
                    Spacer()
                }
            }

            // Floating action buttons (always visible at bottom)
            if !isLoading && !useWebFallback && player != nil {
                VStack {
                    Spacer()

                    HStack(spacing: 20) {
                        // Quality indicator
                        Text(currentQuality)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(.ultraThinMaterial)
                            .clipShape(Capsule())

                        Spacer()

                        // Add to collection button
                        Button {
                            showAddToCollection = true
                        } label: {
                            Image(systemName: "plus.rectangle.on.folder")
                                .font(.title2)
                                .foregroundStyle(.white)
                                .padding(12)
                                .background(.ultraThinMaterial)
                                .clipShape(Circle())
                        }

                        // Minimize button (keeps playing in background)
                        Button {
                            playerService.minimize()
                        } label: {
                            Image(systemName: "chevron.down")
                                .font(.title2)
                                .foregroundStyle(.white)
                                .padding(12)
                                .background(.ultraThinMaterial)
                                .clipShape(Circle())
                        }
                    }
                    .padding()
                    .padding(.bottom, 60) // Above player controls
                }
            }
        }
        .task {
            await loadStream()
        }
        .onAppear {
            setupAudioSession()
        }
        .sheet(isPresented: $showAddToCollection) {
            AddToCollectionSheet(video: video, collections: $collections)
                .environmentObject(apiClient)
        }
        .task {
            await loadCollections()
        }
    }

    private func setupAudioSession() {
        do {
            // Enable background audio playback
            try AVAudioSession.sharedInstance().setCategory(
                .playback,
                mode: .moviePlayback,
                options: [.allowAirPlay, .allowBluetooth]
            )
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }

    private func loadStream() async {
        // Only reuse existing player if it's the SAME video (maximize from mini player)
        // If it's a different video, we need to load fresh (PlayerService already stopped the old one)
        if let existingPlayer = player,
           playerService.currentVideo?.id == video.id {
            isLoading = false
            currentQuality = streamInfo?.quality ?? "Playing"
            // Resume playback if paused
            if existingPlayer.rate == 0 {
                existingPlayer.play()
                playerService.isPlaying = true
            }
            return
        }

        isLoading = true
        error = nil
        currentQuality = "Loading..."

        let config = isPhone ? StreamLoadingConfig.iPhoneDefault : StreamLoadingConfig.iPadDefault

        let result = await VideoStreamCoordinator.shared.loadStream(
            video: video,
            apiClient: apiClient,
            config: config,
            resumeFromSeconds: video.watchProgressSeconds
        )

        switch result {
        case .success(let newPlayer, let info, let quality):
            // Register player with PlayerService so MiniPlayerView can control it
            playerService.registerPlayer(newPlayer)
            streamInfo = info
            currentQuality = quality
            playerService.isPlaying = true
            isLoading = false

            // Upgrade to higher quality in background
            Task {
                await upgradeToHighQuality(config: config)
            }

        case .fallbackRequired(let reason):
            print("Fallback required: \(reason)")
            useWebFallback = true
            isLoading = false

        case .error(let message):
            self.error = message
            isLoading = false
        }
    }

    private func upgradeToHighQuality(config: StreamLoadingConfig) async {
        guard let currentPlayer = player, !isUpgradingQuality else { return }
        guard let currentInfo = streamInfo else { return }

        // Don't upgrade if already at max quality for this device
        if let current = currentInfo.quality, current == config.maxQuality {
            return
        }

        isUpgradingQuality = true

        let result = await VideoStreamCoordinator.shared.upgradeToHighQuality(
            currentPlayer: currentPlayer,
            currentStreamInfo: currentInfo,
            video: video,
            apiClient: apiClient,
            config: config
        )

        switch result {
        case .upgraded(let newQuality, let newInfo):
            streamInfo = newInfo
            currentQuality = newQuality
        case .notNeeded, .failed:
            break
        }

        isUpgradingQuality = false
    }

    private func loadCollections() async {
        do {
            collections = try await apiClient.getCollections()
        } catch {
            print("Failed to load collections: \(error)")
        }
    }

    private func startProgressTracking() {
        progressTimer = Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { _ in
            saveProgress()
        }
    }

    private func stopProgressTracking() {
        progressTimer?.invalidate()
        progressTimer = nil
    }

    private func saveProgress() {
        guard let player = player else { return }

        let currentTime = player.currentTime()
        let seconds = Int(CMTimeGetSeconds(currentTime))

        guard seconds > 0 else { return }

        Task {
            do {
                _ = try await apiClient.updateWatchProgress(itemId: video.id, seconds: seconds)
            } catch {
                print("Failed to save progress: \(error)")
            }
        }
    }
}

// MARK: - AVPlayerViewController Wrapper for PiP Support

struct AVPlayerControllerView: UIViewControllerRepresentable {
    let player: AVPlayer

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let controller = AVPlayerViewController()
        controller.player = player
        controller.allowsPictureInPicturePlayback = true
        controller.canStartPictureInPictureAutomaticallyFromInline = true

        // Enable background playback continuation
        controller.updatesNowPlayingInfoCenter = true

        return controller
    }

    func updateUIViewController(_ uiViewController: AVPlayerViewController, context: Context) {
        uiViewController.player = player
    }
}

// MARK: - Add to Collection Sheet

struct AddToCollectionSheet: View {
    @EnvironmentObject var apiClient: APIClient
    @Environment(\.dismiss) private var dismiss

    let video: FeedItem
    @Binding var collections: [Collection]

    @State private var isLoading = false
    @State private var error: String?
    @State private var successMessage: String?
    @State private var newCollectionName = ""
    @State private var showCreateNew = false

    var body: some View {
        NavigationStack {
            List {
                if collections.isEmpty && !isLoading {
                    Section {
                        Text("No collections yet")
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Section("Add to Collection") {
                        ForEach(collections) { collection in
                            Button {
                                addToCollection(collection)
                            } label: {
                                HStack {
                                    Image(systemName: "folder")
                                        .foregroundStyle(.blue)
                                    Text(collection.name)
                                        .foregroundStyle(.primary)
                                    Spacer()
                                    Text("\(collection.itemCount) items")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                            .disabled(isLoading)
                        }
                    }
                }

                Section {
                    if showCreateNew {
                        HStack {
                            TextField("Collection name", text: $newCollectionName)
                            Button("Create") {
                                createAndAdd()
                            }
                            .disabled(newCollectionName.trimmingCharacters(in: .whitespaces).isEmpty || isLoading)
                        }
                    } else {
                        Button {
                            showCreateNew = true
                        } label: {
                            Label("Create New Collection", systemImage: "plus.circle")
                        }
                    }
                }

                if let error = error {
                    Section {
                        Text(error)
                            .foregroundStyle(.red)
                    }
                }

                if let success = successMessage {
                    Section {
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                            Text(success)
                        }
                    }
                }
            }
            .navigationTitle("Add to Collection")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
        .presentationDetents([.medium])
    }

    private func addToCollection(_ collection: Collection) {
        isLoading = true
        error = nil
        successMessage = nil

        Task {
            do {
                let item = AddCollectionItemRequest(
                    itemType: "video",
                    url: video.videoUrl,
                    thumbnailUrl: video.thumbnailUrl,
                    title: video.title,
                    sourceUrl: video.videoUrl,
                    videoId: video.videoId
                )
                _ = try await apiClient.addItemToCollection(collectionId: collection.id, item: item)
                successMessage = "Added to \(collection.name)"

                // Refresh collections
                collections = try await apiClient.getCollections()

                // Auto-dismiss after success
                try? await Task.sleep(nanoseconds: 1_000_000_000)
                dismiss()
            } catch {
                self.error = "Failed to add: \(error.localizedDescription)"
            }
            isLoading = false
        }
    }

    private func createAndAdd() {
        let name = newCollectionName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }

        isLoading = true
        error = nil

        Task {
            do {
                let newCollection = try await apiClient.createCollection(name: name)
                collections.insert(newCollection, at: 0)
                newCollectionName = ""
                showCreateNew = false

                // Add the video to the new collection
                addToCollection(newCollection)
            } catch {
                self.error = "Failed to create: \(error.localizedDescription)"
                isLoading = false
            }
        }
    }
}

#Preview {
    VideoPlayerView(
        video: FeedItem(
            id: 1,
            channelId: 1,
            platform: "youtube",
            videoId: "dQw4w9WgXcQ",
            videoUrl: "https://youtube.com/watch?v=dQw4w9WgXcQ",
            title: "Test Video",
            description: nil,
            thumbnailUrl: nil,
            durationSeconds: 300,
            viewCount: 1000,
            uploadDate: nil,
            categories: nil,
            isWatched: false,
            watchedAt: nil,
            watchProgressSeconds: nil,
            discoveredAt: nil,
            channelName: "Test Channel"
        ),
        isPresented: .constant(true)
    )
    .environmentObject(APIClient())
}
