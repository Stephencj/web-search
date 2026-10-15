package com.websearch.tv.ui.navigation

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
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.key.*
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.tv.foundation.lazy.list.TvLazyRow
import androidx.tv.foundation.lazy.list.itemsIndexed
import com.websearch.tv.api.FeedItem
import com.websearch.tv.ui.screens.channels.ChannelsScreen
import com.websearch.tv.ui.screens.collections.CollectionsScreen
import com.websearch.tv.ui.screens.discover.DiscoverScreen
import com.websearch.tv.ui.screens.feed.FeedScreen
import com.websearch.tv.ui.screens.login.LoginScreen
import com.websearch.tv.ui.screens.player.VideoPlayerScreen
import com.websearch.tv.ui.screens.saved.SavedVideosScreen
import com.websearch.tv.ui.screens.settings.SettingsScreen

sealed class Screen(val route: String) {
    data object Login : Screen("login")
    data object Main : Screen("main")
    data object Player : Screen("player/{platform}/{videoId}/{itemId}") {
        fun createRoute(platform: String, videoId: String, itemId: Int = 0) =
            "player/$platform/$videoId/$itemId"
    }
}

enum class MainTab(val title: String, val icon: ImageVector) {
    Feed("Feed", Icons.Default.Home),
    Channels("Channels", Icons.Default.Person),
    Discover("Discover", Icons.Default.Search),
    Collections("Collections", Icons.Default.Folder),
    Saved("Saved", Icons.Default.Bookmark),
    Settings("Settings", Icons.Default.Settings)
}

@Composable
fun AppNavigation(
    isLoggedIn: Boolean,
    onLogout: () -> Unit
) {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = if (isLoggedIn) Screen.Main.route else Screen.Login.route
    ) {
        composable(Screen.Login.route) {
            LoginScreen(
                onLoginSuccess = {
                    navController.navigate(Screen.Main.route) {
                        popUpTo(Screen.Login.route) { inclusive = true }
                    }
                }
            )
        }

        composable(Screen.Main.route) {
            MainScreen(
                navController = navController,
                onLogout = onLogout
            )
        }

        composable(Screen.Player.route) { backStackEntry ->
            val platform = backStackEntry.arguments?.getString("platform") ?: ""
            val videoId = backStackEntry.arguments?.getString("videoId") ?: ""
            val itemId = backStackEntry.arguments?.getString("itemId")?.toIntOrNull() ?: 0

            VideoPlayerScreen(
                platform = platform,
                videoId = videoId,
                itemId = itemId,
                onBack = { navController.popBackStack() }
            )
        }
    }
}

@Composable
fun MainScreen(
    navController: NavHostController,
    onLogout: () -> Unit
) {
    var selectedTab by remember { mutableStateOf(MainTab.Feed) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        // Tab bar
        TabBar(
            selectedTab = selectedTab,
            onTabSelected = { selectedTab = it }
        )

        // Content
        Box(modifier = Modifier.fillMaxSize()) {
            when (selectedTab) {
                MainTab.Feed -> FeedScreen(
                    onVideoSelect = { video ->
                        navController.navigate(
                            Screen.Player.createRoute(video.platform, video.videoId, video.id)
                        )
                    }
                )
                MainTab.Channels -> ChannelsScreen()
                MainTab.Discover -> DiscoverScreen(
                    onVideoSelect = { video ->
                        navController.navigate(
                            Screen.Player.createRoute(video.platform, video.videoId, 0)
                        )
                    }
                )
                MainTab.Collections -> CollectionsScreen(
                    onVideoSelect = { video ->
                        navController.navigate(
                            Screen.Player.createRoute(video.platform, video.videoId, video.id)
                        )
                    }
                )
                MainTab.Saved -> SavedVideosScreen(
                    onVideoSelect = { video ->
                        navController.navigate(
                            Screen.Player.createRoute(video.platform, video.videoId, video.id)
                        )
                    }
                )
                MainTab.Settings -> SettingsScreen(onLogout = onLogout)
            }
        }
    }
}

@Composable
private fun TabBar(
    selectedTab: MainTab,
    onTabSelected: (MainTab) -> Unit
) {
    TvLazyRow(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 48.dp, vertical = 24.dp),
        horizontalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        itemsIndexed(MainTab.entries.toList()) { _, tab ->
            TabItem(
                tab = tab,
                isSelected = tab == selectedTab,
                onClick = { onTabSelected(tab) }
            )
        }
    }
}

@Composable
private fun TabItem(
    tab: MainTab,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    var isFocused by remember { mutableStateOf(false) }

    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(
                when {
                    isSelected -> MaterialTheme.colorScheme.primary
                    isFocused -> MaterialTheme.colorScheme.primary.copy(alpha = 0.3f)
                    else -> MaterialTheme.colorScheme.surface
                }
            )
            .onFocusChanged { isFocused = it.isFocused }
            .focusable()
            .onKeyEvent { event ->
                if (event.type == KeyEventType.KeyUp &&
                    (event.key == Key.Enter || event.key == Key.DirectionCenter)
                ) {
                    onClick()
                    true
                } else false
            }
            .padding(horizontal = 20.dp, vertical = 12.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = tab.icon,
            contentDescription = tab.title,
            tint = when {
                isSelected -> MaterialTheme.colorScheme.onPrimary
                isFocused -> MaterialTheme.colorScheme.primary
                else -> MaterialTheme.colorScheme.onSurface
            }
        )
        Text(
            text = tab.title,
            style = MaterialTheme.typography.labelLarge,
            color = when {
                isSelected -> MaterialTheme.colorScheme.onPrimary
                isFocused -> MaterialTheme.colorScheme.primary
                else -> MaterialTheme.colorScheme.onSurface
            }
        )
    }
}
