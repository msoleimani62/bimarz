package ir.bimarz.app.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import ir.bimarz.app.data.ProfileRepository
import ir.bimarz.app.data.ServerProfile
import ir.bimarz.app.data.VlessLinkParser
import ir.bimarz.app.vpn.ConnectionState
import ir.bimarz.app.vpn.VpnStateHolder
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val profileRepository = ProfileRepository(application)

    private val _profiles = MutableStateFlow<List<ServerProfile>>(emptyList())
    val profiles: StateFlow<List<ServerProfile>> = _profiles.asStateFlow()

    val connectionState: StateFlow<ConnectionState> = VpnStateHolder.state

    private val _linkError = MutableStateFlow<String?>(null)
    val linkError: StateFlow<String?> = _linkError.asStateFlow()

    init {
        reloadProfiles()
    }

    private fun reloadProfiles() {
        viewModelScope.launch {
            _profiles.value = profileRepository.loadAll()
        }
    }

    fun addProfileFromLink(rawLink: String) {
        viewModelScope.launch {
            try {
                val profile = VlessLinkParser.parse(rawLink)
                profileRepository.add(profile)
                _linkError.value = null
                reloadProfiles()
            } catch (e: VlessLinkParser.VlessLinkParseException) {
                _linkError.value = e.message
            }
        }
    }

    fun removeProfile(profileId: String) {
        viewModelScope.launch {
            profileRepository.remove(profileId)
            reloadProfiles()
        }
    }

    fun clearLinkError() {
        _linkError.value = null
    }
}
