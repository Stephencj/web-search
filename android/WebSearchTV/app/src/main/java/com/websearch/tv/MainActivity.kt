package com.websearch.tv

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.lifecycle.lifecycleScope
import com.websearch.tv.auth.AuthManager
import com.websearch.tv.ui.navigation.AppNavigation
import com.websearch.tv.ui.theme.WebSearchTVTheme
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject
    lateinit var authManager: AuthManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            val isLoggedIn by authManager.isLoggedIn.collectAsState(initial = false)

            WebSearchTVTheme {
                AppNavigation(
                    isLoggedIn = isLoggedIn,
                    onLogout = {
                        lifecycleScope.launch {
                            authManager.clearToken()
                        }
                    }
                )
            }
        }
    }
}
