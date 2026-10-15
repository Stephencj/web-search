package com.websearch.tv.ui.screens.channels

import androidx.compose.foundation.background
import androidx.compose.foundation.focusable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
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
import androidx.compose.ui.graphics.Color
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
import com.websearch.tv.api.Channel
import com.websearch.tv.ui.components.PlatformBadge
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class ChannelsState {
    data object Loading : ChannelsState()
    data class Success(val channels: List<Channel>) : ChannelsState()
    data class Error(val message: String) : ChannelsState()
}

@HiltViewModel
class ChannelsViewModel @Inject constructor(
    private val apiClient: ApiClient
) : ViewModel() {

    private val _state = MutableStateFlow<ChannelsState>(ChannelsState.Loading)
    val state: StateFlow<ChannelsState> = _state.asStateFlow()

    private val _syncingChannelId = MutableStateFlow<Int?>(null)
    val syncingChannelId: StateFlow<Int?> = _syncingChannelId.asStateFlow()

    init {
        loadChannels()
    }

    fun loadChannels() {
        viewModelScope.launch {
            _state.value = ChannelsState.Loading
            try {
                val channels = apiClient.getChannels()
                _state.value = ChannelsState.Success(channels)
            } catch (e: Exception) {
                _state.value = ChannelsState.Error(e.message ?: "Failed to load channels")
            }
        }
    }

    fun syncChannel(channelId: Int) {
        viewModelScope.launch {
            _syncingChannelId.value = channelId
            try {
                apiClient.syncChannel(channelId)
                loadChannels()
            } catch (e: Exception) {
                // Handle error
            }
            _syncingChannelId.value = null
        }
    }

    fun deleteChannel(channelId: Int) {
        viewModelScope.launch {
            try {
                apiClient.deleteChannel(channelId)
                loadChannels()
            } catch (e: Exception) {
                // Handle error
            }
        }
    }
}

@Composable
fun ChannelsScreen(
    viewModel: ChannelsViewModel = hiltViewModel()
) {
    val state by viewModel.state.collectAsState()
    val syncingChannelId by viewModel.syncingChannelId.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        when (val currentState = state) {
            is ChannelsState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            is ChannelsState.Error -> {
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
            is ChannelsState.Success -> {
                if (currentState.channels.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Person,
                                contentDescription = null,
                                modifier = Modifier.size(48.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "No channels",
                                style = MaterialTheme.typography.bodyLarge,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = "Subscribe from Discover",
                                style = MaterialTheme.typography.bodyMedium,
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
                        items(currentState.channels) { channel ->
                            ChannelCard(
                                channel = channel,
                                isSyncing = syncingChannelId == channel.id,
                                onSync = { viewModel.syncChannel(channel.id) },
                                onDelete = { viewModel.deleteChannel(channel.id) }
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ChannelCard(
    channel: Channel,
    isSyncing: Boolean,
    onSync: () -> Unit,
    onDelete: () -> Unit
) {
    var isFocused by remember { mutableStateOf(false) }
    var showMenu by remember { mutableStateOf(false) }

    Card(
        modifier = Modifier
            .width(300.dp)
            .scale(if (isFocused) 1.05f else 1f)
            .onFocusChanged { isFocused = it.isFocused }
            .focusable()
            .onKeyEvent { event ->
                if (event.type == KeyEventType.KeyUp) {
                    when (event.key) {
                        Key.Menu -> {
                            showMenu = true
                            true
                        }
                        else -> false
                    }
                } else false
            },
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            containerColor = if (isFocused)
                MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)
            else MaterialTheme.colorScheme.surface
        )
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Avatar
            Box(
                modifier = Modifier.size(120.dp)
            ) {
                if (channel.avatarUrl != null) {
                    AsyncImage(
                        model = channel.avatarUrl,
                        contentDescription = channel.name,
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(CircleShape),
                        contentScale = ContentScale.Crop
                    )
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.surfaceVariant),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = channel.name.take(1).uppercase(),
                            style = MaterialTheme.typography.headlineLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                if (isSyncing) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(CircleShape)
                            .background(Color.Black.copy(alpha = 0.5f)),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(32.dp),
                            color = Color.White
                        )
                    }
                }
            }

            // Name
            Text(
                text = channel.name,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )

            // Stats
            Row(
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                channel.videoCount?.let { count ->
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.PlayCircle,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp),
                            tint = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "$count",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                channel.unwatchedCount?.let { count ->
                    if (count > 0) {
                        Text(
                            text = "$count new",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                }
            }

            // Platform badge
            PlatformBadge(platform = channel.platform)
        }
    }

    // Context menu
    DropdownMenu(
        expanded = showMenu,
        onDismissRequest = { showMenu = false }
    ) {
        DropdownMenuItem(
            text = { Text("Sync Channel") },
            onClick = {
                onSync()
                showMenu = false
            },
            leadingIcon = {
                Icon(Icons.Default.Sync, contentDescription = null)
            }
        )
        DropdownMenuItem(
            text = { Text("Unsubscribe") },
            onClick = {
                onDelete()
                showMenu = false
            },
            leadingIcon = {
                Icon(Icons.Default.PersonRemove, contentDescription = null)
            }
        )
    }
}
