import UIKit
import AVFoundation

class AppDelegate: NSObject, UIApplicationDelegate {

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        configureAudioSession()
        return true
    }

    // MARK: - Audio Session Configuration
    private func configureAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()

            // Configure for background audio playback
            try session.setCategory(
                .playback,
                mode: .default,
                options: [.allowAirPlay, .allowBluetoothA2DP]
            )

            // Activate the session
            try session.setActive(true)

            print("Audio session configured successfully")
        } catch {
            print("Failed to configure audio session: \(error)")
        }
    }

    // MARK: - Background Tasks
    func application(
        _ application: UIApplication,
        handleEventsForBackgroundURLSession identifier: String,
        completionHandler: @escaping () -> Void
    ) {
        // Handle background URL session events
        completionHandler()
    }

    // MARK: - App Lifecycle
    func applicationDidEnterBackground(_ application: UIApplication) {
        // App entered background - audio will continue if configured correctly
    }

    func applicationWillEnterForeground(_ application: UIApplication) {
        // App is coming back to foreground
        Task { @MainActor in
            // Refresh auth session if needed
            await AuthService.shared.restoreSession()
        }
    }

    func applicationWillTerminate(_ application: UIApplication) {
        // Save any pending state before termination
    }
}
