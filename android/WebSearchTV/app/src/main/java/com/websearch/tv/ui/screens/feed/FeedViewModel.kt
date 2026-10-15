package com.websearch.tv.ui.screens.feed

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.websearch.tv.api.*
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class FeedState {
    data object Loading : FeedState()
    data class Success(val items: List<FeedItem>) : FeedState()
    data class Error(val message: String) : FeedState()
}

@HiltViewModel
class FeedViewModel @Inject constructor(
    private val apiClient: ApiClient
) : ViewModel() {

    private val _feedState = MutableStateFlow<FeedState>(FeedState.Loading)
    val feedState: StateFlow<FeedState> = _feedState.asStateFlow()

    private val _stats = MutableStateFlow<FeedStats?>(null)
    val stats: StateFlow<FeedStats?> = _stats.asStateFlow()

    private val _platforms = MutableStateFlow<List<Platform>>(emptyList())
    val platforms: StateFlow<List<Platform>> = _platforms.asStateFlow()

    private val _watchFilter = MutableStateFlow(WatchFilter.UNWATCHED)
    val watchFilter: StateFlow<WatchFilter> = _watchFilter.asStateFlow()

    private val _platformFilter = MutableStateFlow<String?>(null)
    val platformFilter: StateFlow<String?> = _platformFilter.asStateFlow()

    private val _modeFilter = MutableStateFlow(FeedMode.NEWEST)
    val modeFilter: StateFlow<FeedMode> = _modeFilter.asStateFlow()

    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()

    init {
        loadFeed()
        loadStats()
        loadPlatforms()
    }

    fun loadFeed() {
        viewModelScope.launch {
            _feedState.value = FeedState.Loading
            try {
                val response = apiClient.getFeed(
                    platform = _platformFilter.value,
                    watched = _watchFilter.value,
                    mode = _modeFilter.value,
                    perPage = 50
                )
                _feedState.value = FeedState.Success(response.items)
            } catch (e: Exception) {
                _feedState.value = FeedState.Error(e.message ?: "Failed to load feed")
            }
        }
    }

    private fun loadStats() {
        viewModelScope.launch {
            try {
                _stats.value = apiClient.getFeedStats()
            } catch (e: Exception) {
                // Ignore stats errors
            }
        }
    }

    private fun loadPlatforms() {
        viewModelScope.launch {
            try {
                _platforms.value = apiClient.getPlatforms()
            } catch (e: Exception) {
                // Ignore platform errors
            }
        }
    }

    fun setWatchFilter(filter: WatchFilter) {
        _watchFilter.value = filter
        loadFeed()
    }

    fun setPlatformFilter(platform: String?) {
        _platformFilter.value = platform
        loadFeed()
    }

    fun setModeFilter(mode: FeedMode) {
        _modeFilter.value = mode
        loadFeed()
    }

    fun syncFeed() {
        viewModelScope.launch {
            _isSyncing.value = true
            try {
                apiClient.syncFeed()
                loadFeed()
                loadStats()
            } catch (e: Exception) {
                // Handle error
            }
            _isSyncing.value = false
        }
    }

    fun markWatched(itemId: Int) {
        viewModelScope.launch {
            try {
                apiClient.markWatched(itemId)
                loadFeed()
                loadStats()
            } catch (e: Exception) {
                // Handle error
            }
        }
    }

    fun markUnwatched(itemId: Int) {
        viewModelScope.launch {
            try {
                apiClient.markUnwatched(itemId)
                loadFeed()
                loadStats()
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}
