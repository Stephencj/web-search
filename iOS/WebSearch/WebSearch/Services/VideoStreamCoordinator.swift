import AVFoundation

// MARK: - Stream Loading Result Types

/// Result of a stream loading operation
enum StreamLoadingResult {
    case success(player: AVPlayer, streamInfo: StreamInfo, quality: String)
    case fallbackRequired(reason: String)
    case error(String)
}

/// Result of a quality upgrade operation
enum QualityUpgradeResult {
    case upgraded(newQuality: String, streamInfo: StreamInfo)
    case notNeeded
    case failed(reason: String)
}

// MARK: - Stream Loading Configuration

/// Platform-specific settings for stream loading
struct StreamLoadingConfig {
    let initialQuality: String
    let maxQuality: String
    let stabilizationDelay: UInt64
    let qualityFallbacks: [String]

    static let iPhoneDefault = StreamLoadingConfig(
        initialQuality: "480p",
        maxQuality: "720p",
        stabilizationDelay: 1_000_000_000,
        qualityFallbacks: []
    )

    static let iPadDefault = StreamLoadingConfig(
        initialQuality: "720p",
        maxQuality: "best",
        stabilizationDelay: 1_000_000_000,
        qualityFallbacks: []
    )

    static let tvOSDefault = StreamLoadingConfig(
        initialQuality: "720p",
        maxQuality: "best",
        stabilizationDelay: 2_000_000_000,
        qualityFallbacks: ["720p", "best"]
    )
}

// MARK: - Video Stream Coordinator

/// Shared coordinator for loading video streams across iOS and tvOS platforms
@MainActor
class VideoStreamCoordinator {
    static let shared = VideoStreamCoordinator()

    private init() {}

    /// Load a video stream with the given configuration
    /// - Parameters:
    ///   - video: The video to play
    ///   - apiClient: API client for fetching stream info
    ///   - config: Platform-specific configuration
    ///   - resumeFromSeconds: Optional position to resume from
    /// - Returns: Result indicating success, fallback needed, or error
    func loadStream(
        video: FeedItem,
        apiClient: APIClient,
        config: StreamLoadingConfig,
        resumeFromSeconds: Int? = nil
    ) async -> StreamLoadingResult {
        // If config has quality fallbacks, try them in order (tvOS pattern)
        if !config.qualityFallbacks.isEmpty {
            return await loadStreamWithFallbacks(
                video: video,
                apiClient: apiClient,
                qualities: config.qualityFallbacks,
                resumeFromSeconds: resumeFromSeconds
            )
        }

        // Otherwise use single quality approach (iOS pattern)
        return await loadStreamSingleQuality(
            video: video,
            apiClient: apiClient,
            quality: config.initialQuality,
            resumeFromSeconds: resumeFromSeconds
        )
    }

    /// Load stream with single quality (iOS approach)
    private func loadStreamSingleQuality(
        video: FeedItem,
        apiClient: APIClient,
        quality: String,
        resumeFromSeconds: Int?
    ) async -> StreamLoadingResult {
        do {
            let info = try await apiClient.getStreamInfo(
                platform: video.platform,
                videoId: video.videoId,
                quality: quality
            )

            if let errorMsg = info.error {
                print("Stream error: \(errorMsg)")
                return .fallbackRequired(reason: errorMsg)
            }

            guard let streamUrl = info.streamUrl, let url = URL(string: streamUrl) else {
                return .fallbackRequired(reason: "No stream URL available")
            }

            let playerItem = AVPlayerItem(url: url)
            let player = AVPlayer(playerItem: playerItem)

            // Optimize for faster playback start
            player.automaticallyWaitsToMinimizeStalling = false

            // Resume from saved position
            if let progress = resumeFromSeconds, progress > 0 {
                let time = CMTime(seconds: Double(progress), preferredTimescale: 1)
                await player.seek(to: time)
            }

            // Start playback immediately
            player.play()

            return .success(
                player: player,
                streamInfo: info,
                quality: info.quality ?? quality
            )
        } catch {
            print("Failed to get stream: \(error)")
            return .fallbackRequired(reason: error.localizedDescription)
        }
    }

    /// Load stream with quality fallbacks (tvOS approach)
    private func loadStreamWithFallbacks(
        video: FeedItem,
        apiClient: APIClient,
        qualities: [String],
        resumeFromSeconds: Int?
    ) async -> StreamLoadingResult {
        print("Loading stream for: \(video.platform) / \(video.videoId)")

        for quality in qualities {
            do {
                print("Trying quality: \(quality)")
                let info = try await apiClient.getStreamInfo(
                    platform: video.platform,
                    videoId: video.videoId,
                    quality: quality
                )

                if let errorMsg = info.error {
                    print("Stream API returned error for \(quality): \(errorMsg)")
                    continue
                }

                guard let streamUrl = info.streamUrl, !streamUrl.isEmpty else {
                    print("No stream URL returned for \(quality)")
                    continue
                }

                guard let url = URL(string: streamUrl) else {
                    print("Invalid stream URL: \(streamUrl)")
                    continue
                }

                print("Got stream URL: \(streamUrl.prefix(100))...")

                let playerItem = AVPlayerItem(url: url)
                let player = AVPlayer(playerItem: playerItem)

                // Resume from saved position
                if let progress = resumeFromSeconds, progress > 0 {
                    let time = CMTime(seconds: Double(progress), preferredTimescale: 1)
                    await player.seek(to: time)
                }

                // Start playback immediately
                player.play()

                print("Player created and play() called - rate: \(player.rate)")

                return .success(
                    player: player,
                    streamInfo: info,
                    quality: info.quality ?? quality
                )
            } catch {
                print("Failed to get stream for \(quality): \(error)")
                continue
            }
        }

        // All qualities failed
        return .error("Unable to load stream for this video")
    }

    /// Upgrade to high quality stream
    /// - Parameters:
    ///   - currentPlayer: The current AVPlayer instance
    ///   - currentStreamInfo: Current stream info
    ///   - video: The video being played
    ///   - apiClient: API client
    ///   - config: Platform configuration
    /// - Returns: Result indicating upgrade status
    func upgradeToHighQuality(
        currentPlayer: AVPlayer,
        currentStreamInfo: StreamInfo,
        video: FeedItem,
        apiClient: APIClient,
        config: StreamLoadingConfig
    ) async -> QualityUpgradeResult {
        // Wait for initial playback to stabilize
        try? await Task.sleep(nanoseconds: config.stabilizationDelay)

        // Don't upgrade if already at max quality
        if let current = currentStreamInfo.quality, current == config.maxQuality {
            return .notNeeded
        }

        do {
            let bestInfo = try await apiClient.getStreamInfo(
                platform: video.platform,
                videoId: video.videoId,
                quality: config.maxQuality
            )

            guard let newQuality = bestInfo.quality,
                  let currentQual = currentStreamInfo.quality,
                  newQuality != currentQual,
                  let streamUrl = bestInfo.streamUrl,
                  let url = URL(string: streamUrl) else {
                return .notNeeded
            }

            print("Preparing quality upgrade from \(currentQual) to \(newQuality)")

            let highQualityItem = AVPlayerItem(url: url)
            let currentTime = currentPlayer.currentTime()
            let wasPlaying = currentPlayer.rate > 0

            // Wait for new item to be ready
            let ready = await waitForItemReady(item: highQualityItem)

            guard ready else {
                print("Failed to prepare high quality stream")
                return .failed(reason: "High quality stream not ready")
            }

            // Seamlessly swap the player item
            currentPlayer.replaceCurrentItem(with: highQualityItem)

            // Seek to where we were
            await currentPlayer.seek(to: currentTime, toleranceBefore: .zero, toleranceAfter: .zero)

            // Resume playback if it was playing
            if wasPlaying {
                currentPlayer.play()
            }

            print("Upgraded quality to \(newQuality)")

            return .upgraded(newQuality: newQuality, streamInfo: bestInfo)

        } catch {
            print("Failed to upgrade quality: \(error)")
            return .failed(reason: error.localizedDescription)
        }
    }

    /// Wait for an AVPlayerItem to be ready for playback
    /// - Parameters:
    ///   - item: The player item to wait for
    ///   - timeout: Maximum wait time in seconds (default 10)
    /// - Returns: True if ready, false if failed or timed out
    func waitForItemReady(item: AVPlayerItem, timeout: TimeInterval = 10) async -> Bool {
        let checkInterval: TimeInterval = 0.2
        var elapsed: TimeInterval = 0

        while elapsed < timeout {
            let status = item.status

            if status == .readyToPlay {
                return true
            } else if status == .failed {
                return false
            }

            try? await Task.sleep(nanoseconds: UInt64(checkInterval * 1_000_000_000))
            elapsed += checkInterval
        }

        return item.status == .readyToPlay
    }
}
