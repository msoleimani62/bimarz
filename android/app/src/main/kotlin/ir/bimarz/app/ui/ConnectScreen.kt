package ir.bimarz.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ir.bimarz.app.R
import ir.bimarz.app.data.ServerProfile
import ir.bimarz.app.vpn.ConnectionState

@Composable
fun ConnectScreen(
    connectionState: ConnectionState,
    selectedProfile: ServerProfile?,
    onConnectClick: () -> Unit,
    onDisconnectClick: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = statusLabel(connectionState),
            style = MaterialTheme.typography.headlineSmall,
        )

        if (selectedProfile != null) {
            Text(
                text = selectedProfile.label,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(top = 8.dp, bottom = 24.dp),
            )
        }

        val isBusy = connectionState is ConnectionState.Connecting ||
            connectionState is ConnectionState.Disconnecting

        Button(
            enabled = !isBusy && selectedProfile != null,
            onClick = {
                if (connectionState is ConnectionState.Connected) {
                    onDisconnectClick()
                } else {
                    onConnectClick()
                }
            },
        ) {
            val labelRes = if (connectionState is ConnectionState.Connected) {
                R.string.disconnect
            } else {
                R.string.connect
            }
            Text(text = stringResourceCompat(labelRes))
        }

        if (connectionState is ConnectionState.Error) {
            Text(
                text = connectionState.message,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 16.dp),
            )
        }
    }
}

@Composable
private fun statusLabel(state: ConnectionState): String = when (state) {
    is ConnectionState.Disconnected -> stringResourceCompat(R.string.status_disconnected)
    is ConnectionState.Connecting -> stringResourceCompat(R.string.status_connecting)
    is ConnectionState.Connected -> stringResourceCompat(R.string.status_connected)
    is ConnectionState.Disconnecting -> stringResourceCompat(R.string.status_disconnecting)
    is ConnectionState.Error -> stringResourceCompat(R.string.status_disconnected)
}

@Composable
private fun stringResourceCompat(resId: Int): String =
    androidx.compose.ui.res.stringResource(id = resId)
