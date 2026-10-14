import SwiftUI
import WebKit

struct WebVideoPlayerView: View {
    let video: FeedItem
    @Binding var isPresented: Bool

    @State private var isLoading = true

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            if let embedUrl = getEmbedUrl() {
                WebView(url: embedUrl, isLoading: $isLoading)
                    .ignoresSafeArea()
            } else {
                // No embed available, show link to open externally
                VStack(spacing: 20) {
                    Image(systemName: "play.rectangle")
                        .font(.system(size: 60))
                        .foregroundStyle(.gray)

                    Text("In-app playback not available")
                        .font(.headline)
                        .foregroundStyle(.white)

                    Text("This video can only be played in the \(video.platform.capitalized) app or browser.")
                        .font(.subheadline)
                        .foregroundStyle(.gray)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)

                    Button {
                        if let url = URL(string: video.videoUrl) {
                            UIApplication.shared.open(url)
                        }
                    } label: {
                        Label("Open in \(video.platform.capitalized)", systemImage: "arrow.up.right.square")
                    }
                    .buttonStyle(.borderedProminent)
                    .padding(.top)
                }
            }

            // Loading indicator
            if isLoading {
                ProgressView()
                    .scaleEffect(1.5)
                    .tint(.white)
            }

            // Close button
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

                    // Platform badge
                    PlatformBadge(platform: video.platform)
                        .padding()
                }
                Spacer()
            }
        }
    }

    private func getEmbedUrl() -> URL? {
        let platform = video.platform.lowercased()
        let videoId = video.videoId

        switch platform {
        case "youtube":
            return URL(string: "https://www.youtube.com/embed/\(videoId)?autoplay=1&rel=0&playsinline=1")

        case "rumble":
            // Rumble video IDs for embed might need different format
            // Try both the video ID and extracting from URL
            if let embedId = extractRumbleEmbedId() {
                return URL(string: "https://rumble.com/embed/\(embedId)/")
            }
            return nil

        case "odysee":
            // Odysee embed format: https://odysee.com/$/embed/claim-name/claim-id
            if let embedUrl = extractOdyseeEmbedUrl() {
                return URL(string: embedUrl)
            }
            return nil

        default:
            return nil
        }
    }

    private func extractRumbleEmbedId() -> String? {
        // Try to extract embed ID from Rumble URL
        // URL format: https://rumble.com/v4xxxxx-title.html
        // Embed format: https://rumble.com/embed/v4xxxxx/

        let url = video.videoUrl

        // Try to extract the video ID pattern (v followed by alphanumeric)
        if let range = url.range(of: "/(v[a-zA-Z0-9]+)", options: .regularExpression) {
            let match = String(url[range])
            return String(match.dropFirst()) // Remove leading slash
        }

        // If videoId is already in correct format
        if video.videoId.hasPrefix("v") {
            return video.videoId
        }

        return video.videoId
    }

    private func extractOdyseeEmbedUrl() -> String? {
        // Odysee URL format: https://odysee.com/@channel/video-name:claim-id
        // Embed format: https://odysee.com/$/embed/video-name/claim-id

        let url = video.videoUrl

        // Try to parse the Odysee URL
        guard let urlComponents = URLComponents(string: url),
              let host = urlComponents.host,
              host.contains("odysee") else {
            return nil
        }

        let path = urlComponents.path

        // Extract claim name and claim ID
        // Path format: /@channel/video-name:claim-id or /video-name:claim-id
        let parts = path.split(separator: "/").filter { !$0.isEmpty }

        for part in parts {
            if part.contains(":") && !part.hasPrefix("@") {
                let claimParts = part.split(separator: ":")
                if claimParts.count == 2 {
                    let claimName = String(claimParts[0])
                    let claimId = String(claimParts[1])
                    return "https://odysee.com/$/embed/\(claimName)/\(claimId)?autoplay=1"
                }
            }
        }

        return nil
    }
}

// MARK: - WKWebView Wrapper

struct WebView: UIViewRepresentable {
    let url: URL
    @Binding var isLoading: Bool

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []
        config.allowsPictureInPictureMediaPlayback = true

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.isScrollEnabled = false
        webView.isOpaque = false
        webView.backgroundColor = .black

        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        let request = URLRequest(url: url)
        webView.load(request)
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        var parent: WebView

        init(_ parent: WebView) {
            self.parent = parent
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            parent.isLoading = true
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            parent.isLoading = false
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            parent.isLoading = false
        }
    }
}

#Preview {
    WebVideoPlayerView(
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
}
