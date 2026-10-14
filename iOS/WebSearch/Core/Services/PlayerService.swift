import SwiftUI
import AVKit
#if os(iOS)
import MediaPlayer
#endif

@MainActor
class PlayerService: ObservableObject {
    static let shared = PlayerService()

    @Published var currentVideo: FeedItem?
    @Published var isPlaying = false
    @Published var isFullScreen = false
    @Published var currentTime: Double = 0
    @Published var duration: Double = 0
    @Published var isLoading = false
    @Published var showPlayer = false  // Triggers full-screen player presentation

    // Player is now public so VideoPlayerView can register it
    @Published var player: AVPlayer?
    private var timeObserver: Any?
    private var statusObserver: NSKeyValueObservation?

    private init() {
        #if os(iOS)
        setupRemoteCommands()
        #endif
        setupAudioSession()
    }

    private func setupAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try session.setActive(true)
        } catch {
            print("Failed to setup audio session: \(error)")
        }
    }

    func play(video: FeedItem) {
        // If switching to a different video, stop current playback first
        // This also dismisses PiP since replaceCurrentItem(nil) exits PiP
        if let current = currentVideo, current.id != video.id {
            stopCurrentPlayback()
        }

        currentVideo = video
        showPlayer = true  // Trigger player presentation
    }

    /// Stops current playback completely, dismissing PiP if active
    private func stopCurrentPlayback() {
        player?.pause()
        player?.replaceCurrentItem(with: nil)  // This exits PiP
        player = nil
        cleanupObservers()
        isPlaying = false
        currentTime = 0
        duration = 0
    }

    /// Called when user minimizes the player (keeps playing in background)
    func minimize() {
        showPlayer = false
        // Don't stop the player - keep it playing for mini player control
    }

    func closePlayer() {
        showPlayer = false
        currentVideo = nil
        stop()
    }

    /// Register a player created by VideoPlayerView
    /// This allows MiniPlayerView to control the same player instance
    func registerPlayer(_ newPlayer: AVPlayer) {
        // Clean up existing observers if we had a different player
        cleanupObservers()

        player = newPlayer
        setupTimeObserver()
        setupStatusObserver()
        #if os(iOS)
        updateNowPlayingInfo()
        #endif
    }

    private func setupStatusObserver() {
        guard let playerItem = player?.currentItem else { return }

        statusObserver = playerItem.observe(\.status) { [weak self] item, _ in
            Task { @MainActor in
                switch item.status {
                case .readyToPlay:
                    self?.isLoading = false
                    let duration = item.duration.seconds
                    if !duration.isNaN {
                        self?.duration = duration
                    }
                case .failed:
                    self?.isLoading = false
                default:
                    break
                }
            }
        }
    }

    private func cleanupObservers() {
        if let observer = timeObserver, let player = player {
            player.removeTimeObserver(observer)
        }
        timeObserver = nil
        statusObserver?.invalidate()
        statusObserver = nil
    }

    func playDirectURL(_ urlString: String) {
        guard let url = URL(string: urlString) else { return }

        isLoading = true

        // Create player
        let playerItem = AVPlayerItem(url: url)
        let newPlayer = AVPlayer(playerItem: playerItem)
        registerPlayer(newPlayer)
        player?.play()
        isPlaying = true

        isLoading = false
    }

    func togglePlayPause() {
        if isPlaying {
            player?.pause()
        } else {
            player?.play()
        }
        isPlaying.toggle()
        #if os(iOS)
        updatePlaybackState()
        #endif
    }

    func seek(by seconds: Double) {
        guard let player = player else { return }
        let newTime = player.currentTime().seconds + seconds
        player.seek(to: CMTime(seconds: max(0, newTime), preferredTimescale: 1))
    }

    func seekTo(_ time: Double) {
        player?.seek(to: CMTime(seconds: time, preferredTimescale: 1))
    }

    func stop() {
        cleanupObservers()
        player?.pause()
        player = nil
        currentVideo = nil
        isPlaying = false
        currentTime = 0
        duration = 0

        #if os(iOS)
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
        #endif
    }

    func setFullScreen(_ fullScreen: Bool) {
        isFullScreen = fullScreen
        if fullScreen {
            showPlayer = true
        }
    }

    #if os(iOS)
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

        center.changePlaybackPositionCommand.addTarget { [weak self] event in
            if let event = event as? MPChangePlaybackPositionCommandEvent {
                self?.seekTo(event.positionTime)
            }
            return .success
        }
    }
    #endif

    private func setupTimeObserver() {
        timeObserver = player?.addPeriodicTimeObserver(
            forInterval: CMTime(seconds: 1, preferredTimescale: 1),
            queue: .main
        ) { [weak self] time in
            Task { @MainActor in
                self?.currentTime = time.seconds
                if let duration = self?.player?.currentItem?.duration.seconds, !duration.isNaN {
                    self?.duration = duration
                }
            }
        }
    }

    #if os(iOS)
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
                    var updatedInfo = MPNowPlayingInfoCenter.default().nowPlayingInfo ?? [:]
                    updatedInfo[MPMediaItemPropertyArtwork] = artwork
                    MPNowPlayingInfoCenter.default().nowPlayingInfo = updatedInfo
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
    #endif
}
