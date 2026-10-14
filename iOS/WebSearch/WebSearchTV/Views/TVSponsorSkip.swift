import Foundation
import CryptoKit

/// The Apple TV player only ever plays the server's direct stream — tvOS has
/// no web view, so YouTube's own player and its ads never appear here. What
/// ads are left are the sponsor read-outs inside the videos; this skips them.
/// Same behaviour as the brain-washer iPhone app.
enum AdBlocking {
    static let settingKey = "block_ads"

    static var isEnabled: Bool {
        UserDefaults.standard.object(forKey: settingKey) as? Bool ?? true
    }
}

struct SponsorSegment: Equatable {
    let start: TimeInterval
    let end: TimeInterval
    let category: String

    var label: String {
        switch category {
        case "sponsor": return "Sponsor"
        case "selfpromo": return "Self-promotion"
        default: return category.capitalized
        }
    }
}

/// Segments come from SponsorBlock's crowd-sourced database, asked by the
/// first four hex digits of the video id's SHA-256 so the service never
/// learns exactly which video is playing.
enum SponsorSegments {
    static let categories = ["sponsor", "selfpromo"]
    static let minimumLength: TimeInterval = 1

    static func fetch(videoId: String, session: URLSession = .shared) async -> [SponsorSegment] {
        let digest = SHA256.hash(data: Data(videoId.utf8))
        let prefix = digest.map { String(format: "%02x", $0) }.joined().prefix(4)

        var comps = URLComponents(string: "https://sponsor.ajay.app/api/skipSegments/\(prefix)")!
        let categoryList = "[" + categories.map { "\"\($0)\"" }.joined(separator: ",") + "]"
        comps.queryItems = [
            URLQueryItem(name: "categories", value: categoryList),
            URLQueryItem(name: "actionTypes", value: "[\"skip\"]"),
        ]
        guard let url = comps.url else { return [] }

        var request = URLRequest(url: url)
        request.timeoutInterval = 8
        // 404 means no video under that prefix has segments — the common case.
        guard let (data, response) = try? await session.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200 else { return [] }
        return parse(data, videoId: videoId)
    }

    static func parse(_ data: Data, videoId: String) -> [SponsorSegment] {
        struct Entry: Decodable {
            let videoID: String
            let segments: [Segment]
        }
        struct Segment: Decodable {
            let segment: [Double]
            let category: String
        }
        guard let entries = try? JSONDecoder().decode([Entry].self, from: data),
              let mine = entries.first(where: { $0.videoID == videoId }) else { return [] }

        return mine.segments
            .compactMap { s -> SponsorSegment? in
                guard s.segment.count == 2, categories.contains(s.category) else { return nil }
                let seg = SponsorSegment(start: s.segment[0], end: s.segment[1], category: s.category)
                return seg.end - seg.start >= minimumLength ? seg : nil
            }
            .sorted { $0.start < $1.start }
    }
}

/// Each segment is skipped once; scrubbing back into one afterwards is taken
/// as wanting to see it.
struct SponsorSkipper {
    private(set) var segments: [SponsorSegment] = []
    private var skipped: Set<Int> = []

    init(segments: [SponsorSegment] = []) {
        self.segments = segments
    }

    mutating func segmentToSkip(at time: TimeInterval) -> SponsorSegment? {
        guard let index = segments.indices.first(where: {
            !skipped.contains($0) && segments[$0].start <= time && time < segments[$0].end - 0.5
        }) else { return nil }
        skipped.insert(index)
        return segments[index]
    }
}
