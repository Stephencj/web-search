import SwiftUI

struct TVWebVideoPlayerView: View {
    let video: FeedItem
    @Binding var isPresented: Bool

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            // tvOS doesn't support WebKit, show fallback message
            VStack(spacing: 30) {
                Image(systemName: "play.rectangle")
                    .font(.system(size: 80))
                    .foregroundStyle(.gray)

                Text("Web Playback Unavailable")
                    .font(.title2)
                    .foregroundStyle(.white)

                Text("This video from \(video.platform.capitalized) cannot be played on Apple TV. Web playback is not supported on this platform.")
                    .font(.headline)
                    .foregroundStyle(.gray)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 100)

                Button("Close") {
                    isPresented = false
                }
                .buttonStyle(.borderedProminent)
                .padding(.top, 20)
            }

            // Top bar with info
            VStack {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(video.title)
                            .font(.headline)
                            .foregroundStyle(.white)
                            .lineLimit(1)

                        if let channelName = video.channelName {
                            Text(channelName)
                                .font(.subheadline)
                                .foregroundStyle(.gray)
                        }
                    }

                    Spacer()

                    // Platform badge
                    TVPlatformBadge(platform: video.platform)
                }
                .padding(40)
                .background(
                    LinearGradient(
                        colors: [.black.opacity(0.8), .clear],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )

                Spacer()
            }
        }
        .onExitCommand {
            isPresented = false
        }
    }
}
