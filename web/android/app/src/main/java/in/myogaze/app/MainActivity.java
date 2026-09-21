package in.myogaze.app;

import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

/**
 * iPhone hotspots are metered. Android then sends app HTTP over mobile data,
 * so Sign in never reaches the laptop. Bind to Wi-Fi before the WebView loads.
 */
public class MainActivity extends BridgeActivity {
  private ConnectivityManager connectivity;
  private final ConnectivityManager.NetworkCallback wifiCallback =
      new ConnectivityManager.NetworkCallback() {
        @Override
        public void onAvailable(Network network) {
          connectivity.bindProcessToNetwork(network);
        }

        @Override
        public void onLost(Network network) {
          connectivity.bindProcessToNetwork(null);
        }
      };

  @Override
  public void onCreate(Bundle savedInstanceState) {
    connectivity = (ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
    bindCurrentWifi();
    if (connectivity != null) {
      NetworkRequest request =
          new NetworkRequest.Builder()
              .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
              .build();
      connectivity.registerNetworkCallback(request, wifiCallback);
    }
    super.onCreate(savedInstanceState);
  }

  private void bindCurrentWifi() {
    if (connectivity == null) {
      return;
    }
    Network[] networks = connectivity.getAllNetworks();
    if (networks == null) {
      return;
    }
    for (Network network : networks) {
      NetworkCapabilities caps = connectivity.getNetworkCapabilities(network);
      if (caps != null && caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
        connectivity.bindProcessToNetwork(network);
        return;
      }
    }
  }

  @Override
  public void onDestroy() {
    if (connectivity != null) {
      try {
        connectivity.unregisterNetworkCallback(wifiCallback);
      } catch (RuntimeException ignored) {
        /* already unregistered */
      }
      connectivity.bindProcessToNetwork(null);
    }
    super.onDestroy();
  }
}
