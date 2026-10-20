import type { CapacitorConfig } from '@capacitor/cli'

const config: CapacitorConfig = {
  appId: 'in.myogaze.app',
  appName: 'MyoGaze',
  webDir: 'dist',
  android: {
    // The Control App is reached over plain HTTP on the local network
    allowMixedContent: true,
  },
  ios: {
    // capacitor:// / https scheme so WKWebView stays a secure context (getUserMedia)
    contentInset: 'automatic',
    scheme: 'MyoGaze',
  },
  server: {
    // Bundled UI + Connect screen (LAN IP, Tailscale IP, or https://… tunnel URL).
    // Do not set `url` here — a hardcoded LAN address breaks APK installs on other networks.
    androidScheme: 'http',
    iosScheme: 'https',
    cleartext: true,
    allowNavigation: ['*'],
  },
  plugins: {
    CapacitorHttp: {
      enabled: true,
    },
  },
}

export default config
