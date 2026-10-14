import SwiftUI

struct FeedFilterSheet: View {
    @Binding var selectedMode: FeedMode
    @Binding var watchFilter: WatchFilter
    @Binding var selectedPlatform: String?
    let onApply: () -> Void

    @Environment(\.dismiss) var dismiss

    let platforms = ["youtube", "rumble", "odysee", "podcast", "redbar"]

    var body: some View {
        NavigationStack {
            List {
                // Feed Mode
                Section("Feed Mode") {
                    ForEach(FeedMode.allCases, id: \.self) { mode in
                        Button {
                            selectedMode = mode
                        } label: {
                            HStack {
                                Image(systemName: mode.icon)
                                    .frame(width: 24)
                                Text(mode.displayName)
                                Spacer()
                                if selectedMode == mode {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.blue)
                                }
                            }
                        }
                        .foregroundStyle(.primary)
                    }
                }

                // Watch Status
                Section("Watch Status") {
                    ForEach(WatchFilter.allCases, id: \.self) { filter in
                        Button {
                            watchFilter = filter
                        } label: {
                            HStack {
                                Text(filter.displayName)
                                Spacer()
                                if watchFilter == filter {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.blue)
                                }
                            }
                        }
                        .foregroundStyle(.primary)
                    }
                }

                // Platform Filter
                Section("Platform") {
                    Button {
                        selectedPlatform = nil
                    } label: {
                        HStack {
                            Text("All Platforms")
                            Spacer()
                            if selectedPlatform == nil {
                                Image(systemName: "checkmark")
                                    .foregroundStyle(.blue)
                            }
                        }
                    }
                    .foregroundStyle(.primary)

                    ForEach(platforms, id: \.self) { platform in
                        Button {
                            selectedPlatform = platform
                        } label: {
                            HStack {
                                PlatformBadge(platform: platform)
                                Spacer()
                                if selectedPlatform == platform {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.blue)
                                }
                            }
                        }
                        .foregroundStyle(.primary)
                    }
                }
            }
            .navigationTitle("Filters")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Reset") {
                        selectedMode = .newest
                        watchFilter = .unwatched
                        selectedPlatform = nil
                    }
                }

                ToolbarItem(placement: .topBarTrailing) {
                    Button("Apply") {
                        onApply()
                    }
                    .fontWeight(.semibold)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}

#Preview {
    FeedFilterSheet(
        selectedMode: .constant(.newest),
        watchFilter: .constant(.unwatched),
        selectedPlatform: .constant(nil),
        onApply: {}
    )
}
