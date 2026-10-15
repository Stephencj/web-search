package com.websearch.tv.ui.screens.saved

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.tv.foundation.lazy.grid.TvGridCells
import androidx.tv.foundation.lazy.grid.TvLazyVerticalGrid
import androidx.tv.foundation.lazy.grid.items
import com.websearch.tv.api.ApiClient
import com.websearch.tv.api.FeedItem
import com.websearch.tv.api.SavedVideo
import com.websearch.tv.ui.components.VideoCard
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class SavedVideosState {
    data object Loading : SavedVideosState()
    data class Success(val videos: List<SavedVideo>) : SavedVideosState()
    data class Error(val message: String) : SavedVideosState()
}

@HiltViewModel
class SavedVideosViewModel @Inject constructor(
    private val apiClient: ApiClient
) : ViewModel() {

    private val _state = MutableStateFlow<SavedVideosState>(SavedVideosState.Loading)
    val state: StateFlow<SavedVideosState> = _state.asStateFlow()

    init {
        loadSavedVideos()
    }

    fun loadSavedVideos() {
        viewModelScope.launch {
            _state.value = SavedVideosState.Loading
            try {
                val videos = apiClient.getSavedVideos()
                _state.value = SavedVideosState.Success(videos)
            } catch (e: Exception) {
                _state.value = SavedVideosState.Error(e.message ?: "Failed to load saved videos")
            }
        }
    }

    fun deleteVideo(id: Int) {
        viewModelScope.launch {
            try {
                apiClient.deleteSavedVideo(id)
                loadSavedVideos()
            } catch (e: Exception) {
                // Handle error
            }
        }
    }

    fun toggleWatched(video: SavedVideo) {
        viewModelScope.launch {
            try {
                apiClient.markSavedVideoWatched(video.id, !video.isWatched)
                loadSavedVideos()
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}

@Composable
fun SavedVideosScreen(
    viewModel: SavedVideosViewModel = hiltViewModel(),
    onVideoSelect: (FeedItem) -> Unit
) {
    val state by viewModel.state.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        when (val currentState = state) {
            is SavedVideosState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            is SavedVideosState.Error -> {
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
            is SavedVideosState.Success -> {
                if (currentState.videos.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Bookmark,
                                contentDescription = null,
                                modifier = Modifier.size(48.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "No saved videos",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "Save videos from Discover to watch later",
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                } else {
                    TvLazyVerticalGrid(
                        columns = TvGridCells.Adaptive(400.dp),
                        contentPadding = PaddingValues(60.dp),
                        verticalArrangement = Arrangement.spacedBy(40.dp),
                        horizontalArrangement = Arrangement.spacedBy(40.dp)
                    ) {
                        items(currentState.videos) { video ->
                            VideoCard(
                                video = video.toFeedItem(),
                                onClick = { onVideoSelect(video.toFeedItem()) }
                            )
                        }
                    }
                }
            }
        }
    }
}
