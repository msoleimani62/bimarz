package ir.bimarz.app.vpn

sealed class ConnectionState {
    data object Disconnected : ConnectionState()
    data object Connecting : ConnectionState()
    data class Connected(val profileId: String, val profileLabel: String) : ConnectionState()
    data object Disconnecting : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}

/**
 * پل ساده بین سرویس (که به چرخه‌ی عمر خودش محدود است) و رابط کاربری
 * Compose: هر دو یک StateFlow مشترک process-wide را می‌بینند. برای این
 * پروژه از AIDL/Messenger پیچیده‌تر لازم نیست چون هیچ IPC بین-فرآیندی‌ای
 * در کار نیست — سرویس و UI هر دو در همان فرآیند اپ اجرا می‌شوند.
 *
 * A simple bridge between the service (which is bound by its own
 * lifecycle) and the Compose UI: both observe one shared process-wide
 * StateFlow. No AIDL/Messenger complexity is needed here since there is
 * no cross-process IPC involved — the service and the UI both run in the
 * app's own process.
 */
object VpnStateHolder {
    private val _state = kotlinx.coroutines.flow.MutableStateFlow<ConnectionState>(
        ConnectionState.Disconnected,
    )
    val state: kotlinx.coroutines.flow.StateFlow<ConnectionState> = _state

    fun update(newState: ConnectionState) {
        _state.value = newState
    }
}
