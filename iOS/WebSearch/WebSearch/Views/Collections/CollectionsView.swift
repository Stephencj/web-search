import SwiftUI

struct CollectionsView: View {
    @EnvironmentObject var apiClient: APIClient
    @Binding var selectedTab: Int

    @State private var collections: [Collection] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var showAddCollection = false
    @State private var newCollectionName = ""
    @State private var collectionToDelete: Collection?
    @State private var showDeleteConfirmation = false

    var body: some View {
        NavigationStack {
            List {
                // MARK: - Permanent Sections (always visible)
                Section {
                    NavigationLink {
                        SavedVideosView(selectedTab: $selectedTab)
                    } label: {
                        Label {
                            Text("Saved Videos")
                        } icon: {
                            Image(systemName: "bookmark.fill")
                                .foregroundStyle(.blue)
                        }
                    }

                    NavigationLink {
                        HistoryView()
                    } label: {
                        Label {
                            Text("Watch History")
                        } icon: {
                            Image(systemName: "clock.fill")
                                .foregroundStyle(.orange)
                        }
                    }
                }

                // MARK: - User Collections
                Section("My Collections") {
                    if isLoading && collections.isEmpty {
                        HStack {
                            Spacer()
                            ProgressView()
                            Spacer()
                        }
                        .listRowBackground(Color.clear)
                    } else if collections.isEmpty {
                        Text("No collections yet")
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .listRowBackground(Color.clear)
                    } else {
                        ForEach(collections) { collection in
                            NavigationLink(destination: CollectionDetailView(collection: collection)) {
                                CollectionRow(collection: collection)
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: false) {
                                Button(role: .destructive) {
                                    collectionToDelete = collection
                                    showDeleteConfirmation = true
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                }
            }
            .listStyle(.insetGrouped)
            .navigationTitle("Collections")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showAddCollection = true
                    } label: {
                        Image(systemName: "plus")
                    }
                }
            }
            .refreshable {
                await loadCollections()
            }
            .alert("New Collection", isPresented: $showAddCollection) {
                TextField("Name", text: $newCollectionName)
                Button("Cancel", role: .cancel) {
                    newCollectionName = ""
                }
                Button("Create") {
                    createCollection()
                }
            }
            .alert("Delete Collection", isPresented: $showDeleteConfirmation) {
                Button("Cancel", role: .cancel) {
                    collectionToDelete = nil
                }
                Button("Delete", role: .destructive) {
                    if let collection = collectionToDelete {
                        deleteCollection(collection)
                    }
                }
            } message: {
                if let collection = collectionToDelete {
                    Text("Are you sure you want to delete \"\(collection.name)\"?")
                }
            }
            .task {
                await loadCollections()
            }
        }
    }

    private func loadCollections() async {
        isLoading = true
        error = nil

        do {
            collections = try await apiClient.getCollections()
        } catch {
            self.error = error.localizedDescription
        }

        isLoading = false
    }

    private func createCollection() {
        let name = newCollectionName.trimmingCharacters(in: .whitespaces)
        guard !name.isEmpty else { return }

        Task {
            do {
                let collection = try await apiClient.createCollection(name: name)
                collections.insert(collection, at: 0)
            } catch {
                self.error = error.localizedDescription
            }
            newCollectionName = ""
        }
    }

    private func deleteCollection(_ collection: Collection) {
        Task {
            do {
                try await apiClient.deleteCollection(id: collection.id)
                collections.removeAll { $0.id == collection.id }
            } catch {
                self.error = error.localizedDescription
            }
            collectionToDelete = nil
        }
    }
}

struct CollectionRow: View {
    let collection: Collection

    var body: some View {
        HStack(spacing: 12) {
            // Cover image or placeholder
            Group {
                if let coverUrl = collection.coverUrl, let url = URL(string: coverUrl) {
                    AsyncImage(url: url) { phase in
                        switch phase {
                        case .success(let image):
                            image
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                        default:
                            collectionPlaceholder
                        }
                    }
                } else {
                    collectionPlaceholder
                }
            }
            .frame(width: 60, height: 60)
            .clipShape(RoundedRectangle(cornerRadius: 8))

            VStack(alignment: .leading, spacing: 4) {
                Text(collection.name)
                    .font(.headline)

                if let description = collection.description, !description.isEmpty {
                    Text(description)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                }

                Text("\(collection.itemCount) items")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
        .padding(.vertical, 4)
    }

    private var collectionPlaceholder: some View {
        Rectangle()
            .fill(Color.blue.opacity(0.1))
            .overlay {
                Image(systemName: "play.rectangle.on.rectangle")
                    .foregroundStyle(.blue)
            }
    }
}

#Preview {
    CollectionsView(selectedTab: .constant(3))
        .environmentObject(APIClient())
}
