import SwiftUI
import AVKit
import AVFoundation

struct TVVideoPlayerView: View {
    @EnvironmentObject var apiClient: APIClient
    @Environment(\.dismiss) private var dismiss

    let video: FeedItem
    @Binding var isPresented: Bool

    @State private var player: AVPlayer?
    @State private var isLoading = true
    @State private var error: String?
    @State private var streamInfo: StreamInfo?
    @State private var currentQuality: String = "Loading..."
    @State private var isUpgradingQuality = false
    @State private var showAddToCollection = false
    @State private var collections: [Collection] = []
    @State private var statusObserver: NSKeyValueObservation?
    @State private var useWebFallback = false
    @State private var endPlaybackObserver: NSObjectProtocol?
    @State private var showWatchedToast = false
    @State private var showOverlays = true
    @State private var hideOverlaysTask: Task<Void, Never>?
    @State private var sponsorSkipper = SponsorSkipper()
    @State private var sponsorTimeObserver: Any?
    @State private var lastSkippedSegment: SponsorSegment?
    @State private var skipNoticeTask: Task<Void, Never>?

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if isLoading {
                VStack(spacing: 20) {
                    ProgressView()
                        .scaleEffect(2)
                    Text("Loading stream...")
                        .font(.headline)
                        .foregroundStyle(.white)
                }
            } else if useWebFallback {
                TVWebVideoPlayerView(video: video, isPresented: $isPresented)
            } else if let player = player {
                // Full-screen AVPlayerViewController for tvOS
                TVPlayerControllerView(player: player, actions: skipActions)
                    .ignoresSafeArea()
                    .onAppear {
                        // Backup: ensure playback is running (play() was already called in loadStream)
                        if player.rate == 0 {
                            player.play()
                        }
                    }
                    .onDisappear {
                        saveProgress()
                    }
            } else if let error = error {
                VStack(spacing: 24) {
                    Image(systemName: "tv.slash")
                        .font(.system(size: 80))
                        .foregroundStyle(.yellow)

                    Text("Playback Error")
                        .font(.title)
                        .foregroundStyle(.white)

                    Text(error)
                        .font(.headline)
                        .foregroundStyle(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 100)

                    HStack(spacing: 30) {
                        Button("Try Web Player") {
                            useWebFallback = true
                        }
                        .buttonStyle(.borderedProminent)

                        Button("Go Back") {
                            isPresented = false
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding(.top)
                }
            }

            // Overlay controls (top corners) - auto-hide with playback controls
            if !isLoading && player != nil && showOverlays {
                VStack {
                    HStack {
                        // Add to collection button (top left)
                        Button {
                            showAddToCollection = true
                        } label: {
                            Label("Add to Collection", systemImage: "plus.rectangle.on.folder")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(.black.opacity(0.6))
                                .clipShape(Capsule())
                        }
                        .buttonStyle(.plain)
                        .padding(40)

                        Spacer()

                        // Quality indicator (top right)
                        Text(currentQuality)
                            .font(.caption)
                            .fontWeight(.semibold)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 8)
                            .background(.black.opacity(0.6))
                            .clipShape(Capsule())
                            .padding(40)
                    }
                    Spacer()
                }
                .transition(.opacity)
            }

            // "Marked as Watched" toast
            if showWatchedToast {
                VStack {
                    Spacer()
                    HStack {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundStyle(.green)
                        Text("Marked as Watched")
                            .font(.headline)
                    }
                    .padding(.horizontal, 24)
                    .padding(.vertical, 16)
                    .background(.black.opacity(0.8))
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .padding(.bottom, 100)
                }
                .transition(.opacity.combined(with: .move(edge: .bottom)))
            }
        }
        .task {
            await loadStream()
        }
        .task {
            await loadCollections()
        }
        .onAppear {
            setupAudioSession()
        }
        .onDisappear {
            cleanupEndPlaybackObserver()
            hideOverlaysTask?.cancel()
            stopSponsorSkipping()
        }
        .onPlayPauseCommand {
            showOverlaysTemporarily()
        }
        .onMoveCommand { _ in
            showOverlaysTemporarily()
        }
        .fullScreenCover(isPresented: $showAddToCollection) {
            TVAddToCollectionView(video: video, collections: $collections, isPresented: $showAddToCollection)
                .environmentObject(apiClient)
        }
    }

    // MARK: - Sponsor skipping

    /// While a skip is fresh, the player offers a button to go back to it.
    private var skipActions: [UIAction] {
        guard let segment = lastSkippedSegment else { return [] }
        return [UIAction(title: "Watch \(segment.label)", image: UIImage(systemName: "backward.fill")) { _ in
            unskip(segment)
        }]
    }

    private func startSponsorSkipping(on player: AVPlayer) {
        stopSponsorSkipping()
        guard AdBlocking.isEnabled, video.platform == "youtube" else { return }
        let videoId = video.videoId
        Task { @MainActor in
            let segments = await SponsorSegments.fetch(videoId: videoId)
            guard !segments.isEmpty, self.player === player else { return }
            sponsorSkipper = SponsorSkipper(segments: segments)
            // Lives on the player, not the item, so it survives the quality
            // upgrade swapping in a better stream.
            sponsorTimeObserver = player.addPeriodicTimeObserver(
                forInterval: CMTime(seconds: 0.5, preferredTimescale: 600),
                queue: .main
            ) { time in
                skipSponsorIfNeeded(at: time.seconds, on: player)
            }
        }
    }

    private func skipSponsorIfNeeded(at time: TimeInterval, on player: AVPlayer) {
        guard let segment = sponsorSkipper.segmentToSkip(at: time) else { return }
        var target = segment.end
        if let duration = player.currentItem?.duration.seconds, duration.isFinite {
            target = min(target, duration)
        }
        player.seek(to: CMTime(seconds: target, preferredTimescale: 600),
                    toleranceBefore: .zero, toleranceAfter: .zero)
        lastSkippedSegment = segment
        skipNoticeTask?.cancel()
        skipNoticeTask = Task { @MainActor in
            try? await Task.sleep(nanoseconds: 8_000_000_000)
            guard !Task.isCancelled else { return }
            lastSkippedSegment = nil
        }
    }

    private func unskip(_ segment: SponsorSegment) {
        skipNoticeTask?.cancel()
        lastSkippedSegment = nil
        player?.seek(to: CMTime(seconds: segment.start, preferredTimescale: 600),
                     toleranceBefore: .zero, toleranceAfter: .zero)
    }

    private func stopSponsorSkipping() {
        if let observer = sponsorTimeObserver {
            player?.removeTimeObserver(observer)
            sponsorTimeObserver = nil
        }
        skipNoticeTask?.cancel()
        lastSkippedSegment = nil
        sponsorSkipper = SponsorSkipper()
    }

    private func loadCollections() async {
        do {
            collections = try await apiClient.getCollections()
        } catch {
            print("Failed to load collections: \(error)")
        }
    }

    private func showOverlaysTemporarily() {
        hideOverlaysTask?.cancel()

        withAnimation(.easeInOut(duration: 0.3)) {
            showOverlays = true
        }

        hideOverlaysTask = Task {
            try? await Task.sleep(nanoseconds: 5_000_000_000) // 5 seconds
            withAnimation(.easeInOut(duration: 0.3)) {
                showOverlays = false
            }
        }
    }

    private func startOverlayHideTimer() {
        hideOverlaysTask?.cancel()
        hideOverlaysTask = Task {
            try? await Task.sleep(nanoseconds: 5_000_000_000) // 5 seconds
            withAnimation(.easeInOut(duration: 0.3)) {
                showOverlays = false
            }
        }
    }

    private func setupAudioSession() {
        do {
            try AVAudioSession.sharedInstance().setCategory(
                .playback,
                mode: .moviePlayback
            )
            try AVAudioSession.sharedInstance().setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }

    private func setupStatusObserver(for playerItem: AVPlayerItem) {
        // Clear any existing observer
        statusObserver?.invalidate()

        // Observe player item status to catch and log errors
        statusObserver = playerItem.observe(\.status, options: [.new]) { [self] item, _ in
            Task { @MainActor in
                switch item.status {
                case .readyToPlay:
                    print("AVPlayerItem status: readyToPlay")
                case .failed:
                    let errorMessage: String
                    if let error = item.error {
                        print("AVPlayerItem FAILED: \(error.localizedDescription)")
                        if let nsError = error as NSError? {
                            print("  Error domain: \(nsError.domain), code: \(nsError.code)")
                            if let underlyingError = nsError.userInfo[NSUnderlyingErrorKey] as? NSError {
                                print("  Underlying error: \(underlyingError.localizedDescription)")
                            }
                        }
                        errorMessage = error.localizedDescription
                    } else {
                        print("AVPlayerItem FAILED with unknown error")
                        errorMessage = "Playback failed unexpectedly"
                    }
                    // Update UI to show error
                    self.player = nil
                    self.error = errorMessage
                    self.isLoading = false
                case .unknown:
                    print("AVPlayerItem status: unknown")
                @unknown default:
                    print("AVPlayerItem status: unhandled case")
                }
            }
        }
    }

    private func loadStream() async {
        isLoading = true
        error = nil
        currentQuality = "Loading..."

        let config = StreamLoadingConfig.tvOSDefault

        let result = await VideoStreamCoordinator.shared.loadStream(
            video: video,
            apiClient: apiClient,
            config: config,
            resumeFromSeconds: video.watchProgressSeconds
        )

        switch result {
        case .success(let newPlayer, let info, let quality):
            // Set up status observer for debugging
            if let playerItem = newPlayer.currentItem {
                setupStatusObserver(for: playerItem)
                setupEndPlaybackObserver(for: playerItem)
            }

            streamInfo = info
            currentQuality = quality
            player = newPlayer
            isLoading = false
            startSponsorSkipping(on: newPlayer)

            // Start auto-hide timer for overlays
            startOverlayHideTimer()

            print("Player created and playing - rate: \(newPlayer.rate)")

            // Upgrade to best quality in background if not already at max
            if quality != config.maxQuality {
                Task {
                    await upgradeToHighQuality(config: config)
                }
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

        // Don't upgrade if already at max quality
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

    private func setupEndPlaybackObserver(for playerItem: AVPlayerItem) {
        // Clean up any existing observer
        cleanupEndPlaybackObserver()

        // Observe when playback reaches the end
        endPlaybackObserver = NotificationCenter.default.addObserver(
            forName: .AVPlayerItemDidPlayToEndTime,
            object: playerItem,
            queue: .main
        ) { [self] _ in
            Task { @MainActor in
                await markVideoAsWatched()
            }
        }
    }

    private func cleanupEndPlaybackObserver() {
        if let observer = endPlaybackObserver {
            NotificationCenter.default.removeObserver(observer)
            endPlaybackObserver = nil
        }
    }

    private func markVideoAsWatched() async {
        // Skip if already marked as watched
        guard !video.isWatched else { return }

        do {
            _ = try await apiClient.markWatched(itemId: video.id)
            print("Video marked as watched: \(video.title)")

            // Show toast notification
            withAnimation(.easeInOut(duration: 0.3)) {
                showWatchedToast = true
            }

            // Hide toast after 3 seconds
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            withAnimation(.easeInOut(duration: 0.3)) {
                showWatchedToast = false
            }
        } catch {
            print("Failed to mark video as watched: \(error)")
        }
    }
}

// MARK: - tvOS AVPlayerViewController Wrapper

struct TVPlayerControllerView: UIViewControllerRepresentable {
    let player: AVPlayer
    var actions: [UIAction] = []

    func makeUIViewController(context: Context) -> AVPlayerViewController {
        let controller = AVPlayerViewController()
        controller.player = player
        controller.showsPlaybackControls = true
        controller.contextualActions = actions
        return controller
    }

    func updateUIViewController(_ uiViewController: AVPlayerViewController, context: Context) {
        uiViewController.player = player
        uiViewController.contextualActions = actions
    }
}

// MARK: - Add to Collection View

struct TVAddToCollectionView: View {
    @EnvironmentObject var apiClient: APIClient

    let video: FeedItem
    @Binding var collections: [Collection]
    @Binding var isPresented: Bool

    @State private var isLoading = false
    @State private var error: String?
    @State private var successMessage: String?
    @State private var newCollectionName = ""
    @State private var showCreateNew = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.opacity(0.9).ignoresSafeArea()

                VStack(spacing: 30) {
                    // Header
                    Text("Add to Collection")
                        .font(.title)
                        .foregroundStyle(.white)

                    // Video info
                    HStack(spacing: 20) {
                        AsyncImage(url: URL(string: video.thumbnailUrl ?? "")) { image in
                            image.resizable().aspectRatio(contentMode: .fill)
                        } placeholder: {
                            Rectangle().fill(Color.gray.opacity(0.3))
                        }
                        .frame(width: 200, height: 112)
                        .clipShape(RoundedRectangle(cornerRadius: 8))

                        VStack(alignment: .leading, spacing: 8) {
                            Text(video.title)
                                .font(.headline)
                                .foregroundStyle(.white)
                                .lineLimit(2)

                            if let channelName = video.channelName {
                                Text(channelName)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        Spacer()
                    }
                    .padding(.horizontal, 100)

                    // Status messages
                    if let error = error {
                        Text(error)
                            .foregroundStyle(.red)
                            .font(.headline)
                    }

                    if let success = successMessage {
                        Text(success)
                            .foregroundStyle(.green)
                            .font(.headline)
                    }

                    if isLoading {
                        ProgressView()
                    }

                    // Collections list
                    if !showCreateNew {
                        ScrollView {
                            LazyVStack(spacing: 16) {
                                // Create new collection button
                                Button {
                                    showCreateNew = true
                                } label: {
                                    HStack {
                                        Image(systemName: "plus.circle.fill")
                                            .foregroundStyle(.blue)
                                        Text("Create New Collection")
                                        Spacer()
                                    }
                                    .padding()
                                    .background(Color.secondary.opacity(0.2))
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                                }
                                .buttonStyle(.plain)

                                // Existing collections
                                ForEach(collections) { collection in
                                    Button {
                                        addToCollection(collection)
                                    } label: {
                                        HStack {
                                            Image(systemName: "folder.fill")
                                                .foregroundStyle(.blue)
                                            Text(collection.name)
                                            Spacer()
                                            Text("\(collection.itemCount) items")
                                                .font(.caption)
                                                .foregroundStyle(.secondary)
                                        }
                                        .padding()
                                        .background(Color.secondary.opacity(0.2))
                                        .clipShape(RoundedRectangle(cornerRadius: 12))
                                    }
                                    .buttonStyle(.plain)
                                    .disabled(isLoading)
                                }
                            }
                            .padding(.horizontal, 100)
                        }
                        .frame(maxHeight: 400)
                    } else {
                        // Create new collection form
                        VStack(spacing: 20) {
                            TextField("Collection name", text: $newCollectionName)
                                .textFieldStyle(.plain)
                                .padding()
                                .background(Color.secondary.opacity(0.2))
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                                .padding(.horizontal, 100)

                            HStack(spacing: 30) {
                                Button("Cancel") {
                                    showCreateNew = false
                                    newCollectionName = ""
                                }
                                .buttonStyle(.bordered)

                                Button("Create & Add") {
                                    createCollectionAndAdd()
                                }
                                .buttonStyle(.borderedProminent)
                                .disabled(newCollectionName.trimmingCharacters(in: .whitespaces).isEmpty || isLoading)
                            }
                        }
                    }

                    Spacer()

                    // Close button
                    Button("Close") {
                        isPresented = false
                    }
                    .buttonStyle(.bordered)
                    .padding(.bottom, 40)
                }
                .padding(.top, 60)
            }
        }
    }

    private func addToCollection(_ collection: Collection) {
        isLoading = true
        error = nil
        successMessage = nil

        Task {
            do {
                var item = AddCollectionItemRequest(
                    itemType: "video",
                    url: video.videoUrl
                )
                item.thumbnailUrl = video.thumbnailUrl
                item.title = video.title
                item.videoId = video.videoId

                _ = try await apiClient.addItemToCollection(collectionId: collection.id, item: item)
                successMessage = "Added to \(collection.name)"

                // Refresh collections
                collections = try await apiClient.getCollections()

                // Auto-close after success
                try? await Task.sleep(nanoseconds: 1_500_000_000)
                isPresented = false
            } catch {
                self.error = "Failed: \(error.localizedDescription)"
            }
            isLoading = false
        }
    }

    private func createCollectionAndAdd() {
        let name = newCollectionName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }

        isLoading = true
        error = nil
        successMessage = nil

        Task {
            do {
                let newCollection = try await apiClient.createCollection(
                    name: name,
                    description: nil
                )

                collections = try await apiClient.getCollections()
                showCreateNew = false
                newCollectionName = ""

                addToCollection(newCollection)
            } catch {
                self.error = "Failed to create: \(error.localizedDescription)"
                isLoading = false
            }
        }
    }
}

#Preview {
    TVVideoPlayerView(
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
