package com.websearch.tv.ui.screens.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.websearch.tv.api.ApiClient
import com.websearch.tv.api.User
import com.websearch.tv.auth.AuthManager
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed class LoginState {
    data object Loading : LoginState()
    data class UserSelection(val users: List<User>) : LoginState()
    data class PinEntry(val user: User) : LoginState()
    data class Error(val message: String) : LoginState()
    data object Success : LoginState()
}

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val apiClient: ApiClient,
    private val authManager: AuthManager
) : ViewModel() {

    private val _state = MutableStateFlow<LoginState>(LoginState.Loading)
    val state: StateFlow<LoginState> = _state.asStateFlow()

    private val _pin = MutableStateFlow("")
    val pin: StateFlow<String> = _pin.asStateFlow()

    init {
        loadUsers()
    }

    private fun loadUsers() {
        viewModelScope.launch {
            _state.value = LoginState.Loading
            try {
                val users = apiClient.getUsers()
                if (users.isEmpty()) {
                    _state.value = LoginState.Error("No users found")
                } else {
                    _state.value = LoginState.UserSelection(users)
                }
            } catch (e: Exception) {
                _state.value = LoginState.Error(e.message ?: "Failed to load users")
            }
        }
    }

    fun selectUser(user: User) {
        if (user.hasPin == true) {
            _pin.value = ""
            _state.value = LoginState.PinEntry(user)
        } else {
            login(user.username, null)
        }
    }

    fun updatePin(newPin: String) {
        if (newPin.length <= 6 && newPin.all { it.isDigit() }) {
            _pin.value = newPin
        }
    }

    fun submitPin() {
        val currentState = _state.value
        if (currentState is LoginState.PinEntry) {
            login(currentState.user.username, _pin.value)
        }
    }

    fun goBack() {
        loadUsers()
    }

    private fun login(username: String, pin: String?) {
        viewModelScope.launch {
            _state.value = LoginState.Loading
            try {
                apiClient.login(username, pin)
                _state.value = LoginState.Success
            } catch (e: Exception) {
                _state.value = LoginState.Error(e.message ?: "Login failed")
            }
        }
    }

    fun retry() {
        loadUsers()
    }
}
