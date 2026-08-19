package ir.bimarz.app.ui

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.IconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import ir.bimarz.app.R
import ir.bimarz.app.data.ServerProfile

@Composable
fun ProfileListScreen(
    profiles: List<ServerProfile>,
    selectedProfileId: String?,
    linkError: String?,
    onSelectProfile: (String) -> Unit,
    onAddLink: (String) -> Unit,
    onRemoveProfile: (String) -> Unit,
) {
    var linkInput by remember { mutableStateOf("") }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(text = stringResource(R.string.profiles_title), style = MaterialTheme.typography.titleLarge)

        Row(modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp)) {
            OutlinedTextField(
                value = linkInput,
                onValueChange = { linkInput = it },
                label = { Text(stringResource(R.string.vless_link_hint)) },
                modifier = Modifier.weight(1f),
                isError = linkError != null,
            )
        }
        if (linkError != null) {
            Text(text = linkError, color = MaterialTheme.colorScheme.error)
        }
        Button(
            onClick = {
                onAddLink(linkInput)
                linkInput = ""
            },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(text = stringResource(R.string.add_profile))
        }

        if (profiles.isEmpty()) {
            Text(
                text = stringResource(R.string.no_profiles),
                modifier = Modifier.padding(top = 24.dp),
            )
        } else {
            LazyColumn(modifier = Modifier.padding(top = 16.dp)) {
                items(profiles, key = { it.profileId }) { profile ->
                    ProfileRow(
                        profile = profile,
                        selected = profile.profileId == selectedProfileId,
                        onSelect = { onSelectProfile(profile.profileId) },
                        onRemove = { onRemoveProfile(profile.profileId) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ProfileRow(
    profile: ServerProfile,
    selected: Boolean,
    onSelect: () -> Unit,
    onRemove: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(modifier = Modifier.fillMaxWidth().padding(8.dp)) {
            RadioButton(selected = selected, onClick = onSelect)
            Column(modifier = Modifier.weight(1f).padding(start = 8.dp)) {
                Text(text = profile.label, style = MaterialTheme.typography.bodyLarge)
                Text(
                    text = "${profile.address}:${profile.port}",
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            IconButton(onClick = onRemove) {
                Icon(imageVector = Icons.Filled.Delete, contentDescription = null)
            }
        }
    }
}
