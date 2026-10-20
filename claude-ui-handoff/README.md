# MyoGaze frontend handoff for Claude (React rebuild)

Upload **`myogaze-claude-handoff.zip`** (same contents as this folder) to Claude.

## Required — copy unchanged (wire protocol)

| File | Role |
|------|------|
| `web/src/useNeuroShift.ts` | `NeuroShiftEngine` hook; WebSocket + REST |
| `web/src/api.ts` | REST client |
| `web/src/auth.ts` | Token key `myogaze.token` |
| `web/src/serverConfig.ts` | Server base `myogaze.serverBase`, Capacitor |
| `web/src/lanHint.ts` | Imported by serverConfig |
| `web/src/gazeStatus.ts` | `deriveGazeStatus()` |
| `web/src/types.ts` | Shared TS types |
| `web/src/activityLog.ts` | Activity feed helpers |
| `web/src/phoneCamera.ts` | Remote camera → WS `camera_frame` |
| `web/src/settings/prefs.ts` | Local prefs `myogaze.settings.v1` |
| `web/package.json` | React 19, Vite 8, Capacitor 8 |
| `web/vite.config.ts` | PWA + proxy `/api`, `/ws` → :8000 |

## Reference only — replace UI, keep behavior

| File | Role |
|------|------|
| `web/src/App.tsx` | Shell: Connect → Onboarding → Auth → 4 tabs |
| `web/src/components/views/LiveView.tsx` | **DetectionStage** double-buffer JPEG + boxes |
| `web/src/components/views/HomeView.tsx` | Home layout reference |
| `web/src/components/views/ActivityView.tsx` | Activity chips |
| `web/src/components/views/SettingsView.tsx` | Settings hub + panel ids |
| `web/src/components/ConnectScreen.tsx` | Native laptop pairing |
| `web/src/components/AuthScreen.tsx` | Login/register |
| `web/src/components/OnboardingScreen.tsx` | First-run |
| `web/src/components/Nav.tsx` | Tab bar |
| `web/src/settings/tracking.ts` | `lampDevice`, `fanDevice` helpers |

## Visual target

Use the **MyoGaze – mobile UI preview.html** already in the Claude chat (Figtree, teal tokens, dark mode).

## Export type

```ts
export type NeuroShiftEngine = ReturnType<typeof useNeuroShift>;
```

Views must accept `engine: NeuroShiftEngine` — no simulated `S` state object.
