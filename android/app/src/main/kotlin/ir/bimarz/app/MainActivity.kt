package ir.bimarz.app

import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import ir.bimarz.app.ui.ConnectScreen
import ir.bimarz.app.ui.MainViewModel
import ir.bimarz.app.ui.ProfileListScreen
import ir.bimarz.app.ui.theme.BimarzTheme
import ir.bimarz.app.vpn.BimarzVpnService

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    // درخواست مجوز VPN همیشه باید از یک اکتیویتی بیاید (سیستم یک دیالوگ
    // سیستمی «BiMarz اجازه‌ی برقراری اتصال VPN را می‌خواهد» نشان می‌دهد)؛
    // یک سرویس به‌تنهایی نمی‌تواند این را تریگر کند.
    // The VPN permission request must always come from an Activity (the
    // system shows a "BiMarz wants to set up a VPN connection" system
    // dialog); a service alone cannot trigger this.
    private val vpnPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult(),
    ) { result ->
        if (result.resultCode == RESULT_OK) {
            pendingConnectProfileId?.let { startVpnService(it) }
        }
        pendingConnectProfileId = null
    }

    private var pendingConnectProfileId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            BimarzTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    BimarzApp(
                        viewModel = viewModel,
                        onRequestConnect = ::requestConnect,
                        onDisconnect = ::stopVpnService,
                    )
                }
            }
        }
    }

    private fun requestConnect(profileId: String) {
        val prepareIntent = VpnService.prepare(this)
        if (prepareIntent != null) {
            pendingConnectProfileId = profileId
            vpnPermissionLauncher.launch(prepareIntent)
        } else {
            startVpnService(profileId)
        }
    }

    private fun startVpnService(profileId: String) {
        val intent = Intent(this, BimarzVpnService::class.java).apply {
            action = BimarzVpnService.ACTION_CONNECT
            putExtra(BimarzVpnService.EXTRA_PROFILE_ID, profileId)
        }
        startService(intent)
    }

    private fun stopVpnService() {
        val intent = Intent(this, BimarzVpnService::class.java).apply {
            action = BimarzVpnService.ACTION_DISCONNECT
        }
        startService(intent)
    }
}

@androidx.compose.runtime.Composable
private fun BimarzApp(
    viewModel: MainViewModel,
    onRequestConnect: (String) -> Unit,
    onDisconnect: () -> Unit,
) {
    val profiles by viewModel.profiles.collectAsState()
    val connectionState by viewModel.connectionState.collectAsState()
    val linkError by viewModel.linkError.collectAsState()

    var selectedProfileId by remember { mutableStateOf<String?>(null) }
    var tabIndex by remember { mutableStateOf(0) }

    androidx.compose.foundation.layout.Column(modifier = Modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = tabIndex) {
            Tab(
                selected = tabIndex == 0,
                onClick = { tabIndex = 0 },
                text = { androidx.compose.material3.Text(androidx.compose.ui.res.stringResource(R.string.profiles_title)) },
            )
            Tab(
                selected = tabIndex == 1,
                onClick = { tabIndex = 1 },
                text = { androidx.compose.material3.Text(androidx.compose.ui.res.stringResource(R.string.connect)) },
            )
        }

        when (tabIndex) {
            0 -> ProfileListScreen(
                profiles = profiles,
                selectedProfileId = selectedProfileId,
                linkError = linkError,
                onSelectProfile = { selectedProfileId = it },
                onAddLink = { viewModel.addProfileFromLink(it) },
                onRemoveProfile = {
                    viewModel.removeProfile(it)
                    if (selectedProfileId == it) selectedProfileId = null
                },
            )
            else -> ConnectScreen(
                connectionState = connectionState,
                selectedProfile = profiles.firstOrNull { it.profileId == selectedProfileId },
                onConnectClick = { selectedProfileId?.let(onRequestConnect) },
                onDisconnectClick = onDisconnect,
            )
        }
    }
}
