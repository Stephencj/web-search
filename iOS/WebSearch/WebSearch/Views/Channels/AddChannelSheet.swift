import SwiftUI

struct AddChannelSheet: View {
    @EnvironmentObject var apiClient: APIClient
    @Environment(\.dismiss) var dismiss

    @State private var channelUrl = ""
    @State private var searchQuery = ""
    @State private var searchResults: [ChannelSearchResult] = []
    @State private var isLoading = false
    @State private var isSearching = false
    @State private var error: String?
    @State private var selectedTab = 0

    let onAdded: (Channel) -> Void

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                // Tab selector
                Picker("Add Method", selection: $selectedTab) {
                    Text("URL").tag(0)
                    Text("Search").tag(1)
                }
                .pickerStyle(.segmented)
                .padding()

                if selectedTab == 0 {
                    urlEntry
                } else {
                    searchEntry
                }
            }
            .navigationTitle("Add Channel")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }

    // MARK: - URL Entry

    private var urlEntry: some View {
        VStack(spacing: 16) {
            Text("Enter a channel URL from YouTube, Rumble, Odysee, or other supported platforms.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            TextField("Channel URL", text: $channelUrl)
                .textFieldStyle(.roundedBorder)
                .autocapitalization(.none)
                .autocorrectionDisabled()
                .keyboardType(.URL)
                .padding(.horizontal)

            if let error = error {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(.horizontal)
            }

            Button {
                addChannelByUrl()
            } label: {
                if isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                } else {
                    Text("Subscribe")
                        .frame(maxWidth: .infinity)
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(channelUrl.trimmingCharacters(in: .whitespaces).isEmpty || isLoading)
            .padding(.horizontal)

            Spacer()

            // Supported platforms hint
            VStack(spacing: 8) {
                Text("Supported Platforms")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                HStack(spacing: 16) {
                    PlatformBadge(platform: "youtube")
                    PlatformBadge(platform: "rumble")
                    PlatformBadge(platform: "odysee")
                    PlatformBadge(platform: "podcast")
                }
            }
            .padding(.bottom, 20)
        }
        .padding(.top)
    }

    // MARK: - Search Entry

    private var searchEntry: some View {
        VStack(spacing: 0) {
            // Search field
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundStyle(.secondary)
                TextField("Search channels...", text: $searchQuery)
                    .autocapitalization(.none)
                    .onSubmit {
                        searchChannels()
                    }
                if !searchQuery.isEmpty {
                    Button {
                        searchQuery = ""
                        searchResults = []
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .clipShape(RoundedRectangle(cornerRadius: 10))
            .padding()

            if let error = error {
                Text(error)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(.horizontal)
            }

            // Results
            if isSearching {
                ProgressView("Searching...")
                    .padding(.top, 40)
                Spacer()
            } else if searchResults.isEmpty && !searchQuery.isEmpty {
                ContentUnavailableView(
                    "No Results",
                    systemImage: "magnifyingglass",
                    description: Text("No channels found for \"\(searchQuery)\"")
                )
            } else {
                List {
                    ForEach(searchResults) { result in
                        ChannelSearchResultRow(result: result) {
                            subscribeToChannel(result)
                        }
                    }
                }
                .listStyle(.plain)
            }
        }
    }

    // MARK: - Actions

    private func addChannelByUrl() {
        let url = channelUrl.trimmingCharacters(in: .whitespaces)
        guard !url.isEmpty else { return }

        isLoading = true
        error = nil

        Task {
            do {
                let channel = try await apiClient.addChannel(url: url)
                onAdded(channel)
                dismiss()
            } catch let apiError as APIError {
                error = apiError.errorDescription
            } catch {
                self.error = error.localizedDescription
            }
            isLoading = false
        }
    }

    private func searchChannels() {
        let query = searchQuery.trimmingCharacters(in: .whitespaces)
        guard !query.isEmpty else { return }

        isSearching = true
        error = nil

        Task {
            do {
                searchResults = try await apiClient.searchChannels(query: query)
            } catch {
                self.error = error.localizedDescription
            }
            isSearching = false
        }
    }

    private func subscribeToChannel(_ result: ChannelSearchResult) {
        isLoading = true
        error = nil

        Task {
            do {
                let channel = try await apiClient.addChannel(url: result.channelUrl)
                onAdded(channel)
                dismiss()
            } catch let apiError as APIError {
                error = apiError.errorDescription
            } catch {
                self.error = error.localizedDescription
            }
            isLoading = false
        }
    }
}

struct ChannelSearchResultRow: View {
    let result: ChannelSearchResult
    let onSubscribe: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Avatar
            AsyncImage(url: URL(string: result.avatarUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().aspectRatio(contentMode: .fill)
                default:
                    Circle()
                        .fill(Color.gray.opacity(0.3))
                        .overlay {
                            Text(String(result.name.prefix(1)).uppercased())
                                .font(.headline)
                                .foregroundStyle(.secondary)
                        }
                }
            }
            .frame(width: 44, height: 44)
            .clipShape(Circle())

            // Info
            VStack(alignment: .leading, spacing: 4) {
                Text(result.name)
                    .font(.headline)
                    .lineLimit(1)

                HStack(spacing: 8) {
                    PlatformBadge(platform: result.platform)

                    if let subscribers = result.subscriberCount {
                        Text(formatCount(subscribers) + " subscribers")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Spacer()

            Button("Subscribe", action: onSubscribe)
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
        }
        .padding(.vertical, 4)
    }

    private func formatCount(_ count: Int) -> String {
        if count >= 1_000_000 {
            return String(format: "%.1fM", Double(count) / 1_000_000)
        } else if count >= 1_000 {
            return String(format: "%.1fK", Double(count) / 1_000)
        }
        return "\(count)"
    }
}

#Preview {
    AddChannelSheet { _ in }
        .environmentObject(APIClient())
}
