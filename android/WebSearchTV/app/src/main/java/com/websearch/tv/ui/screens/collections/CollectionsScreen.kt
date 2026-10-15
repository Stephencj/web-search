package com.websearch.tv.ui.screens.collections

import androidx.compose.foundation.background
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.input.key.*
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.tv.foundation.lazy.grid.TvGridCells
import androidx.tv.foundation.lazy.grid.TvLazyVerticalGrid
import androidx.tv.foundation.lazy.grid.items
import coil.compose.AsyncImage
import com.websearch.tv.api.ApiClient
import com.websearch.tv.api.Collection
import com.websearch.tv.api.CollectionItem
import com.websearch.tv.api.FeedItem
import com.websearch.tv.ui.components.VideoCard
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class CollectionsState {
    data object Loading : CollectionsState()
    data class CollectionsList(val collections: List<Collection>) : CollectionsState()
    data class CollectionDetail(
        val collection: Collection,
        val items: List<CollectionItem>
    ) : CollectionsState()
    data class Error(val message: String) : CollectionsState()
}

@HiltViewModel
class CollectionsViewModel @Inject constructor(
    private val apiClient: ApiClient
) : ViewModel() {

    private val _state = MutableStateFlow<CollectionsState>(CollectionsState.Loading)
    val state: StateFlow<CollectionsState> = _state.asStateFlow()

    init {
        loadCollections()
    }

    fun loadCollections() {
        viewModelScope.launch {
            _state.value = CollectionsState.Loading
            try {
                val collections = apiClient.getCollections()
                _state.value = CollectionsState.CollectionsList(collections)
            } catch (e: Exception) {
                _state.value = CollectionsState.Error(e.message ?: "Failed to load collections")
            }
        }
    }

    fun selectCollection(collection: Collection) {
        viewModelScope.launch {
            _state.value = CollectionsState.Loading
            try {
                val details = apiClient.getCollection(collection.id)
                _state.value = CollectionsState.CollectionDetail(collection, details.items)
            } catch (e: Exception) {
                _state.value = CollectionsState.Error(e.message ?: "Failed to load collection")
            }
        }
    }

    fun goBack() {
        loadCollections()
    }

    fun removeItem(collectionId: Int, itemId: Int) {
        viewModelScope.launch {
            try {
                apiClient.removeItemFromCollection(collectionId, itemId)
                // Reload collection
                val currentState = _state.value
                if (currentState is CollectionsState.CollectionDetail) {
                    selectCollection(currentState.collection)
                }
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}

@Composable
fun CollectionsScreen(
    viewModel: CollectionsViewModel = hiltViewModel(),
    onVideoSelect: (FeedItem) -> Unit
) {
    val state by viewModel.state.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        when (val currentState = state) {
            is CollectionsState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            is CollectionsState.Error -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = currentState.message,
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
            is CollectionsState.CollectionsList -> {
                if (currentState.collections.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Folder,
                                contentDescription = null,
                                modifier = Modifier.size(48.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "No collections",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                } else {
                    TvLazyVerticalGrid(
                        columns = TvGridCells.Adaptive(300.dp),
                        contentPadding = PaddingValues(60.dp),
                        verticalArrangement = Arrangement.spacedBy(40.dp),
                        horizontalArrangement = Arrangement.spacedBy(40.dp)
                    ) {
                        items(currentState.collections) { collection ->
                            CollectionCard(
                                collection = collection,
                                onClick = { viewModel.selectCollection(collection) }
                            )
                        }
                    }
                }
            }
            is CollectionsState.CollectionDetail -> {
                // Header with back button
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 60.dp, vertical = 20.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    var backFocused by remember { mutableStateOf(false) }
                    Box(
                        modifier = Modifier
                            .size(48.dp)
                            .clip(RoundedCornerShape(24.dp))
                            .background(
                                if (backFocused) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.surface
                            )
                            .onFocusChanged { backFocused = it.isFocused }
                            .focusable()
                            .onKeyEvent { event ->
                                if (event.type == KeyEventType.KeyUp &&
                                    (event.key == Key.Enter || event.key == Key.DirectionCenter)
                                ) {
                                    viewModel.goBack()
                                    true
                                } else false
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Back",
                            tint = if (backFocused) MaterialTheme.colorScheme.onPrimary
                            else MaterialTheme.colorScheme.onSurface
                        )
                    }
                    Text(
                        text = currentState.collection.name,
                        style = MaterialTheme.typography.headlineSmall,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    Text(
                        text = "(${currentState.items.size} items)",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                if (currentState.items.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "No items in this collection",
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                } else {
                    TvLazyVerticalGrid(
                        columns = TvGridCells.Adaptive(400.dp),
                        contentPadding = PaddingValues(60.dp),
                        verticalArrangement = Arrangement.spacedBy(40.dp),
                        horizontalArrangement = Arrangement.spacedBy(40.dp)
                    ) {
                        items(currentState.items.mapNotNull { it.toFeedItem() }) { video ->
                            VideoCard(
                                video = video,
                                onClick = { onVideoSelect(video) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CollectionCard(
    collection: Collection,
    onClick: () -> Unit
) {
    var isFocused by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .width(300.dp)
            .scale(if (isFocused) 1.05f else 1f)
            .onFocusChanged { isFocused = it.isFocused }
            .focusable()
            .onKeyEvent { event ->
                if (event.type == KeyEventType.KeyUp &&
                    (event.key == Key.Enter || event.key == Key.DirectionCenter)
                ) {
                    onClick()
                    true
                } else false
            },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isFocused)
                MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
            else MaterialTheme.colorScheme.surface
        )
    ) {
        Column {
            // Cover image
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(16f / 9f)
                    .clip(RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp))
            ) {
                if (collection.coverUrl != null) {
                    AsyncImage(
                        model = collection.coverUrl,
                        contentDescription = collection.name,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop
                    )
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(MaterialTheme.colorScheme.surfaceVariant),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Folder,
                            contentDescription = null,
                            modifier = Modifier.size(48.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            // Info
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = collection.name,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = "${collection.itemCount} items",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
