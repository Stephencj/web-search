package com.websearch.tv.ui.screens.player

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.websearch.tv.api.ApiClient
import com.websearch.tv.api.StreamInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class PlayerState {
    data object Loading : PlayerState()
    data class Ready(val streamInfo: StreamInfo, val resumePosition: Long = 0) : PlayerState()
    data class Error(val message: String) : PlayerState()
}

@HiltViewModel
class VideoPlayerViewModel @Inject constructor(
    private val apiClient: ApiClient
) : ViewModel() {

    private val _playerState = MutableStateFlow<PlayerState>(PlayerState.Loading)
    val playerState: StateFlow<PlayerState> = _playerState.asStateFlow()

    private var currentPlatform: String = ""
    private var currentVideoId: String = ""
    private var currentItemId: Int = 0
    private var lastSavedProgress: Long = 0

    fun loadStream(platform: String, videoId: String, itemId: Int) {
        currentPlatform = platform
        currentVideoId = videoId
        currentItemId = itemId

        viewModelScope.launch {
            _playerState.value = PlayerState.Loading
            try {
                val streamInfo = apiClient.getStreamInfo(platform, videoId)
                if (streamInfo.error != null) {
                    _playerState.value = PlayerState.Error(streamInfo.error)
                } else if (streamInfo.streamUrl == null) {
                    _playerState.value = PlayerState.Error("No stream URL available")
                } else {
                    // Get resume position from feed item if available
                    val resumePosition = try {
                        if (itemId > 0) {
                            val feed = apiClient.getFeed(perPage = 100)
                            feed.items.find { it.id == itemId }?.watchProgressSeconds?.toLong()?.times(1000) ?: 0L
                        } else 0L
                    } catch (e: Exception) {
                        0L
                    }
                    _playerState.value = PlayerState.Ready(streamInfo, resumePosition)
                }
            } catch (e: Exception) {
                _playerState.value = PlayerState.Error(e.message ?: "Failed to load stream")
            }
        }
    }

    fun saveProgress(positionMs: Long) {
        val positionSeconds = (positionMs / 1000).toInt()
        // Only save if position changed significantly (5 seconds)
        if (kotlin.math.abs(positionSeconds - lastSavedProgress) < 5) return
        lastSavedProgress = positionSeconds.toLong()

        viewModelScope.launch {
            try {
                if (currentItemId > 0) {
                    apiClient.updateProgress(currentItemId, positionSeconds)
                }
            } catch (e: Exception) {
                // Ignore progress save errors
            }
        }
    }

    fun markWatched() {
        viewModelScope.launch {
            try {
                if (currentItemId > 0) {
                    apiClient.markWatched(currentItemId)
                }
            } catch (e: Exception) {
                // Ignore mark watched errors
            }
        }
    }
}
