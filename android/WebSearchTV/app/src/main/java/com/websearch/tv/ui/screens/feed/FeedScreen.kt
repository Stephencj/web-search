package com.websearch.tv.ui.screens.feed

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
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.input.key.*
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.tv.foundation.lazy.grid.TvGridCells
import androidx.tv.foundation.lazy.grid.TvLazyVerticalGrid
import androidx.tv.foundation.lazy.grid.items
import androidx.tv.foundation.lazy.list.TvLazyRow
import androidx.tv.foundation.lazy.list.items
import com.websearch.tv.api.FeedItem
import com.websearch.tv.api.FeedMode
import com.websearch.tv.api.Platform
import com.websearch.tv.api.WatchFilter
import com.websearch.tv.ui.components.PlatformBadge
import com.websearch.tv.ui.components.VideoCard

@Composable
fun FeedScreen(
    viewModel: FeedViewModel = hiltViewModel(),
    onVideoSelect: (FeedItem) -> Unit
) {
    val feedState by viewModel.feedState.collectAsState()
    val stats by viewModel.stats.collectAsState()
    val platforms by viewModel.platforms.collectAsState()
    val watchFilter by viewModel.watchFilter.collectAsState()
    val platformFilter by viewModel.platformFilter.collectAsState()
    val modeFilter by viewModel.modeFilter.collectAsState()
    val isSyncing by viewModel.isSyncing.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Stats bar
        stats?.let { feedStats ->
            StatsBar(stats = feedStats)
        }

        // Filter bar
        FilterBar(
            watchFilter = watchFilter,
            platformFilter = platformFilter,
            modeFilter = modeFilter,
            platforms = platforms,
            isSyncing = isSyncing,
            onWatchFilterChange = viewModel::setWatchFilter,
            onPlatformFilterChange = viewModel::setPlatformFilter,
            onModeFilterChange = viewModel::setModeFilter,
            onSync = viewModel::syncFeed,
            onRefresh = viewModel::loadFeed
        )

        // Content
        when (val state = feedState) {
            is FeedState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            is FeedState.Error -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Warning,
                            contentDescription = "Error",
                            modifier = Modifier.size(48.dp),
                            tint = MaterialTheme.colorScheme.error
                        )
                        Text(
                            text = state.message,
                            style = MaterialTheme.typography.bodyLarge,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                    }
                }
            }
            is FeedState.Success -> {
                if (state.items.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.PlayCircle,
                                contentDescription = "No videos",
                                modifier = Modifier.size(48.dp),
                                tint = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Text(
                                text = if (watchFilter == WatchFilter.UNWATCHED)
                                    "No unwatched videos"
                                else
                                    "No videos",
                                style = MaterialTheme.typography.bodyLarge,
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
                        items(state.items) { video ->
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
private fun StatsBar(stats: com.websearch.tv.api.FeedStats) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 60.dp, vertical = 10.dp),
        horizontalArrangement = Arrangement.spacedBy(30.dp)
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.PlayCircle,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(20.dp)
            )
            Text(
                text = "${stats.totalVideos} videos",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = Icons.Default.VisibilityOff,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.tertiary,
                modifier = Modifier.size(20.dp)
            )
            Text(
                text = "${stats.unwatchedCount} unwatched",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        stats.byPlatform?.forEach { (platform, count) ->
            Row(
                horizontalArrangement = Arrangement.spacedBy(4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                PlatformBadge(platform = platform)
                Text(
                    text = "$count",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun FilterBar(
    watchFilter: WatchFilter,
    platformFilter: String?,
    modeFilter: FeedMode,
    platforms: List<Platform>,
    isSyncing: Boolean,
    onWatchFilterChange: (WatchFilter) -> Unit,
    onPlatformFilterChange: (String?) -> Unit,
    onModeFilterChange: (FeedMode) -> Unit,
    onSync: () -> Unit,
    onRefresh: () -> Unit
) {
    TvLazyRow(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 60.dp, vertical = 20.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Watch filter
        item {
            FilterDropdown(
                label = "Show",
                value = watchFilter.displayName,
                options = WatchFilter.entries.map { it.displayName },
                onOptionSelected = { index ->
                    onWatchFilterChange(WatchFilter.entries[index])
                }
            )
        }

        // Platform filter
        item {
            FilterDropdown(
                label = "Platform",
                value = platformFilter?.replaceFirstChar { it.uppercase() } ?: "All",
                options = listOf("All") + platforms.map { it.name },
                onOptionSelected = { index ->
                    onPlatformFilterChange(
                        if (index == 0) null else platforms[index - 1].platformId
                    )
                }
            )
        }

        // Mode filter
        item {
            FilterDropdown(
                label = "Sort",
                value = modeFilter.displayName,
                options = FeedMode.entries.map { it.displayName },
                onOptionSelected = { index ->
                    onModeFilterChange(FeedMode.entries[index])
                }
            )
        }

        // Sync button
        item {
            ActionButton(
                text = "Sync",
                icon = Icons.Default.Sync,
                isLoading = isSyncing,
                onClick = onSync
            )
        }

        // Refresh button
        item {
            ActionButton(
                text = "Refresh",
                icon = Icons.Default.Refresh,
                onClick = onRefresh
            )
        }
    }
}

@Composable
private fun FilterDropdown(
    label: String,
    value: String,
    options: List<String>,
    onOptionSelected: (Int) -> Unit
) {
    var isFocused by remember { mutableStateOf(false) }
    var isExpanded by remember { mutableStateOf(false) }

    Box {
        Row(
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .background(
                    if (isFocused) MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)
                    else MaterialTheme.colorScheme.surface
                )
                .onFocusChanged { isFocused = it.isFocused }
                .focusable()
                .onKeyEvent { event ->
                    if (event.type == KeyEventType.KeyUp &&
                        (event.key == Key.Enter || event.key == Key.DirectionCenter)
                    ) {
                        isExpanded = !isExpanded
                        true
                    } else false
                }
                .padding(horizontal = 16.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "$label:",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                text = value,
                style = MaterialTheme.typography.bodyMedium,
                color = if (isFocused) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.onSurface
            )
            Icon(
                imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                contentDescription = null,
                modifier = Modifier.size(20.dp),
                tint = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        DropdownMenu(
            expanded = isExpanded,
            onDismissRequest = { isExpanded = false }
        ) {
            options.forEachIndexed { index, option ->
                DropdownMenuItem(
                    text = { Text(option) },
                    onClick = {
                        onOptionSelected(index)
                        isExpanded = false
                    }
                )
            }
        }
    }
}

@Composable
private fun ActionButton(
    text: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    isLoading: Boolean = false,
    onClick: () -> Unit
) {
    var isFocused by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(
                if (isFocused) MaterialTheme.colorScheme.primary
                else MaterialTheme.colorScheme.surface
            )
            .onFocusChanged { isFocused = it.isFocused }
            .focusable()
            .onKeyEvent { event ->
                if (event.type == KeyEventType.KeyUp &&
                    (event.key == Key.Enter || event.key == Key.DirectionCenter)
                ) {
                    if (!isLoading) onClick()
                    true
                } else false
            }
            .padding(horizontal = 16.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                modifier = Modifier.size(20.dp),
                strokeWidth = 2.dp,
                color = if (isFocused) MaterialTheme.colorScheme.onPrimary
                else MaterialTheme.colorScheme.primary
            )
        } else {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(20.dp),
                tint = if (isFocused) MaterialTheme.colorScheme.onPrimary
                else MaterialTheme.colorScheme.onSurface
            )
        }
        Text(
            text = text,
            style = MaterialTheme.typography.labelLarge,
            color = if (isFocused) MaterialTheme.colorScheme.onPrimary
            else MaterialTheme.colorScheme.onSurface
        )
    }
}
