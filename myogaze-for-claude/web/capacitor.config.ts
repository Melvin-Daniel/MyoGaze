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
    // Load the laptop Control App in the WebView so Sign in is same-origin.
    url: 'http://192.168.1.10:8000',
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
