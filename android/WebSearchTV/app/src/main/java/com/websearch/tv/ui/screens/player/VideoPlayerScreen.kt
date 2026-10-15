package com.websearch.tv.ui.screens.player

import android.app.Activity
import android.view.KeyEvent
import android.view.WindowManager
import androidx.activity.compose.BackHandler
import androidx.compose.animation.*
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
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.key.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.websearch.tv.util.formatDuration
import kotlinx.coroutines.delay

@Composable
fun VideoPlayerScreen(
    platform: String,
    videoId: String,
    itemId: Int,
    onBack: () -> Unit,
    viewModel: VideoPlayerViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val playerState by viewModel.playerState.collectAsState()

    var showOverlay by remember { mutableStateOf(true) }
    var overlayTrigger by remember { mutableStateOf(0) } // Used to restart auto-hide timer
    var isPlaying by remember { mutableStateOf(false) }
    var currentPosition by remember { mutableStateOf(0L) }
    var duration by remember { mutableStateOf(0L) }

    val exoPlayer = remember {
        ExoPlayer.Builder(context).build()
    }

    // Keep screen on while video player is active
    DisposableEffect(Unit) {
        val activity = context as? Activity
        activity?.window?.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        onDispose {
            activity?.window?.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    // Load stream on first composition
    LaunchedEffect(platform, videoId, itemId) {
        viewModel.loadStream(platform, videoId, itemId)
    }

    // Set up player when stream is ready
    LaunchedEffect(playerState) {
        if (playerState is PlayerState.Ready) {
            val state = playerState as PlayerState.Ready
            state.streamInfo.streamUrl?.let { url ->
                val mediaItem = MediaItem.fromUri(url)
                exoPlayer.setMediaItem(mediaItem)
                exoPlayer.prepare()
                exoPlayer.play()

                // Resume from saved position
                if (state.resumePosition > 0) {
                    exoPlayer.seekTo(state.resumePosition)
                }
            }
        }
    }

    // Auto-hide overlay after 5 seconds when playing
    LaunchedEffect(showOverlay, overlayTrigger, isPlaying) {
        if (showOverlay && isPlaying) {
            delay(5000)
            showOverlay = false
        }
    }

    // Update position periodically
    LaunchedEffect(exoPlayer) {
        while (true) {
            currentPosition = exoPlayer.currentPosition
            duration = exoPlayer.duration.coerceAtLeast(0)
            isPlaying = exoPlayer.isPlaying

            // Save progress periodically
            if (isPlaying && currentPosition > 0) {
                viewModel.saveProgress(currentPosition)
            }

            // Check for video completion
            if (exoPlayer.playbackState == Player.STATE_ENDED) {
                viewModel.markWatched()
            }

            delay(1000)
        }
    }

    // Cleanup
    DisposableEffect(Unit) {
        onDispose {
            viewModel.saveProgress(exoPlayer.currentPosition)
            exoPlayer.release()
        }
    }

    BackHandler {
        if (showOverlay) {
            // First back press hides the overlay
            showOverlay = false
        } else {
            // Second back press exits the player
            viewModel.saveProgress(exoPlayer.currentPosition)
            onBack()
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
            .onKeyEvent { event ->
                if (event.type == KeyEventType.KeyDown) {
                    when (event.nativeKeyEvent.keyCode) {
                        KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER -> {
                            if (showOverlay) {
                                if (exoPlayer.isPlaying) exoPlayer.pause()
                                else exoPlayer.play()
                                overlayTrigger++ // Reset auto-hide timer
                            } else {
                                showOverlay = true
                                overlayTrigger++
                            }
                            true
                        }
                        KeyEvent.KEYCODE_DPAD_LEFT -> {
                            if (showOverlay) {
                                exoPlayer.seekTo((exoPlayer.currentPosition - 10000).coerceAtLeast(0))
                                overlayTrigger++ // Reset auto-hide timer
                            } else {
                                showOverlay = true
                                overlayTrigger++
                            }
                            true
                        }
                        KeyEvent.KEYCODE_DPAD_RIGHT -> {
                            if (showOverlay) {
                                exoPlayer.seekTo((exoPlayer.currentPosition + 30000).coerceAtMost(exoPlayer.duration))
                                overlayTrigger++ // Reset auto-hide timer
                            } else {
                                showOverlay = true
                                overlayTrigger++
                            }
                            true
                        }
                        KeyEvent.KEYCODE_DPAD_UP, KeyEvent.KEYCODE_DPAD_DOWN -> {
                            showOverlay = true
                            overlayTrigger++
                            true
                        }
                        KeyEvent.KEYCODE_BACK -> {
                            if (showOverlay) {
                                // First back press hides the overlay
                                showOverlay = false
                            } else {
                                // Second back press exits the player
                                viewModel.saveProgress(exoPlayer.currentPosition)
                                onBack()
                            }
                            true
                        }
                        else -> {
                            showOverlay = true
                            overlayTrigger++
                            false
                        }
                    }
                } else false
            }
            .focusable()
    ) {
        when (val state = playerState) {
            is PlayerState.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = Color.White)
                }
            }
            is PlayerState.Error -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Error,
                            contentDescription = "Error",
                            modifier = Modifier.size(48.dp),
                            tint = Color.Red
                        )
                        Text(
                            text = state.message,
                            style = MaterialTheme.typography.bodyLarge,
                            color = Color.White
                        )
                        Text(
                            text = "Press Back to return",
                            style = MaterialTheme.typography.bodyMedium,
                            color = Color.Gray
                        )
                    }
                }
            }
            is PlayerState.Ready -> {
                // Video player
                AndroidView(
                    factory = { ctx ->
                        PlayerView(ctx).apply {
                            player = exoPlayer
                            useController = false
                        }
                    },
                    modifier = Modifier.fillMaxSize()
                )

                // Overlay
                AnimatedVisibility(
                    visible = showOverlay,
                    enter = fadeIn(),
                    exit = fadeOut()
                ) {
                    PlayerOverlay(
                        title = state.streamInfo.title ?: "Video",
                        currentPosition = currentPosition,
                        duration = duration,
                        isPlaying = isPlaying,
                        onPlayPause = {
                            if (exoPlayer.isPlaying) exoPlayer.pause()
                            else exoPlayer.play()
                        },
                        onSeekBack = {
                            exoPlayer.seekTo((exoPlayer.currentPosition - 10000).coerceAtLeast(0))
                        },
                        onSeekForward = {
                            exoPlayer.seekTo((exoPlayer.currentPosition + 30000).coerceAtMost(exoPlayer.duration))
                        },
                        onBack = {
                            viewModel.saveProgress(exoPlayer.currentPosition)
                            onBack()
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun PlayerOverlay(
    title: String,
    currentPosition: Long,
    duration: Long,
    isPlaying: Boolean,
    onPlayPause: () -> Unit,
    onSeekBack: () -> Unit,
    onSeekForward: () -> Unit,
    onBack: () -> Unit
) {
    Box(
        modifier = Modifier.fillMaxSize()
    ) {
        // Top gradient with title
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(150.dp)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(Color.Black.copy(alpha = 0.8f), Color.Transparent)
                    )
                )
                .align(Alignment.TopCenter)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(24.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                OverlayButton(
                    icon = Icons.Default.ArrowBack,
                    onClick = onBack
                )
                Spacer(modifier = Modifier.width(24.dp))
                Text(
                    text = title,
                    style = MaterialTheme.typography.headlineSmall,
                    color = Color.White,
                    maxLines = 1
                )
            }
        }

        // Bottom gradient with controls
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(200.dp)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(Color.Transparent, Color.Black.copy(alpha = 0.8f))
                    )
                )
                .align(Alignment.BottomCenter)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.BottomCenter)
                    .padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Progress bar
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text(
                        text = formatDuration((currentPosition / 1000).toInt()),
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White
                    )
                    LinearProgressIndicator(
                        progress = if (duration > 0) currentPosition.toFloat() / duration else 0f,
                        modifier = Modifier
                            .weight(1f)
                            .height(6.dp)
                            .clip(RoundedCornerShape(3.dp)),
                        color = Color.Red,
                        trackColor = Color.White.copy(alpha = 0.3f)
                    )
                    Text(
                        text = formatDuration((duration / 1000).toInt()),
                        style = MaterialTheme.typography.bodyMedium,
                        color = Color.White
                    )
                }

                // Playback controls
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    OverlayButton(
                        icon = Icons.Default.Replay10,
                        onClick = onSeekBack
                    )
                    Spacer(modifier = Modifier.width(32.dp))
                    OverlayButton(
                        icon = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                        onClick = onPlayPause,
                        size = 64.dp
                    )
                    Spacer(modifier = Modifier.width(32.dp))
                    OverlayButton(
                        icon = Icons.Default.Forward30,
                        onClick = onSeekForward
                    )
                }
            }
        }
    }
}

@Composable
private fun OverlayButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
    size: androidx.compose.ui.unit.Dp = 48.dp
) {
    var isFocused by remember { mutableStateOf(false) }
    val focusRequester = remember { FocusRequester() }

    Box(
        modifier = Modifier
            .size(size)
            .clip(CircleShape)
            .background(
                if (isFocused) Color.White.copy(alpha = 0.3f)
                else Color.Transparent
            )
            .focusRequester(focusRequester)
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
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(size * 0.6f),
            tint = Color.White
        )
    }
}
