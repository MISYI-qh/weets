package id.misyi.weets;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Menghidupkan layanan latar belakang Weets otomatis setelah HP menyala (atau aplikasi diperbarui). */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        try {
            ServiceWeets.start(context, "weets");
        } catch (Throwable t) {
            // diam saja: pengguna tetap bisa membuka aplikasi seperti biasa
        }
    }
}
