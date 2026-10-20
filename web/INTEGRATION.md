# MyoGaze web/ — integration notes

Drop this `web/` over `NeuroShift/web/`, then `npm install && npm run build`. No backend changes.

## Kept byte-for-byte (engine, wire protocol, logic)
`useNeuroShift.ts`, `api.ts`, `auth.ts`, `serverConfig.ts`, `lanHint.ts`, `gazeStatus.ts`, `types.ts`,
`activityLog.ts`, `phoneCamera.ts`, `settings/prefs.ts`, `settings/tracking.ts`, `settings/version.ts`,
`App.tsx`, and the views (`HomeView`, `LiveView` incl. the `DetectionStage` JPEG double-buffer,
`ActivityView`, `SettingsView`), plus Connect/Auth/Onboarding screens, Nav, Toast, icons and `capacitor.config.ts`.
Views still take `engine: NeuroShiftEngine`; every action (`toggleDevice`, `startSession`, `pauseSession`,
`calibrateGaze`, `updateSettings`) is the existing call. No fake state anywhere.

## Replaced / added
| File | Change |
|---|---|
| `src/styles/myogaze.css` | New design system (tokens, dark mode, a11y attributes, all component styles). Replaces `index.css`, `claude-app.css`, `vnext.css`, `redesign.css` (those were not in the zip; delete them if present in your repo). |
| `src/main.tsx` | Imports the one stylesheet, calls `applyTheme()`. |
| `src/theme.ts` (new) | Light / dark / system, stored in `myogaze.theme`. Kept out of `prefs.ts` so that file stays unchanged. |
| `components/settings/panels.tsx` | Only `AppearancePanel` changed: now a real theme selector. |
| `index.html` | Figtree font, theme-color. |
| `vite.config.ts` | Only `theme_color` / `background_color` changed. Proxy and PWA config as before. |
| `public/` | Added `apple-touch-icon.png` (180px from app-icon) and `mark.svg` (both were referenced but missing); favicon recoloured teal. |
| Deleted | `ExploreView`, `InsightsView`, `MonitorView`, `SmartView`, `SystemView` (unused). |

## Design tokens
Colors: `--bg --surf --ink --mute --line --teal --teal-s --amber --amber-s`. Unsure/abstain uses amber, never red.
Root attributes applied by `App.tsx`: `data-text` (normal|large|xl), `data-contrast` (high|off), `data-motion` (reduce|ok).
Theme: `data-theme` on `<html>` (absent = follow system).

## Commands
`npm run dev` (proxy `/api` + `/ws` to 127.0.0.1:8000) · `npm run build` (`tsc -b && vite build`) · `npm run preview`.
Capacitor: unchanged; server base comes from `serverConfig.ts`.

## Not verified
`npm run build` passes. I have not run it against your live backend or looked at it on a device: check Live (overlay alignment,
dwell ring), Settings sub-panels, and the onboarding canvas against the preview.
