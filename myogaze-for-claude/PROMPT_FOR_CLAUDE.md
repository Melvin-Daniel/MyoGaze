# Paste this entire message into Claude (after uploading `myogaze-for-claude.zip`)

---

I attached **`myogaze-for-claude.zip`**. It has our real MyoGaze `web/` integration layer, reference views, and **`design/MyoGaze-mobile-UI-preview.html`** (the visual target).

## Your job

Build a **production React 19 + TypeScript + Vite 8** frontend that:

1. **Looks like** the HTML preview (Figtree, teal/slate tokens, dark mode, motion, 480px phone shell).
2. **Behaves like** our current app by using the attached integration files **unchanged in behavior** (you may move/rename CSS, not REST/WS contracts).

**Do not** ship another standalone HTML mock with a fake `S` state object.

## Files you MUST keep behavior-identical

Copy these into your output `web/src/` without changing REST paths, WebSocket message handling, or public APIs:

- `useNeuroShift.ts` → export `useNeuroShift()` and `type NeuroShiftEngine = ReturnType<typeof useNeuroShift>`
- `api.ts`, `auth.ts` (token: `myogaze.token`), `serverConfig.ts`, `lanHint.ts`
- `gazeStatus.ts` → `deriveGazeStatus()`
- `types.ts`, `activityLog.ts`, `phoneCamera.ts`
- `settings/prefs.ts` → `usePrefs`, storage key `myogaze.settings.v1`
- `package.json` dependency versions (React 19, Vite 8, Capacitor 8, vite-plugin-pwa)
- `vite.config.ts` → proxy `/api` and `/ws` to `http://127.0.0.1:8000`, PWA manifest **MyoGaze**, denylist `/label` for SW

## Live view (critical)

Match **`components/views/LiveView.tsx` → `DetectionStage`**:

- `engine.previewJpeg` as double-buffered `<img>` (no SVG fake room)
- Overlays from `engine.liveTargets` with normalized `box` [0–1]
- `engine.gazePoint`, `engine.dwellProgress`
- Copy/status from `deriveGazeStatus({ running, decision, liveTargets, dwellProgress, dwellRequired, dwellActuates })`

## App shell

Same flow as attached `App.tsx`:

1. `ConnectScreen` (Capacitor: laptop IP, `probeServer`, `myogaze.serverBase`)
2. `OnboardingScreen` → `AuthScreen` (register/login)
3. Main: tabs **Home · Live · Activity · Settings** + toasts

All main views take **`engine: NeuroShiftEngine`**.

## Home / Activity / Settings

- **Home:** session hero, lamp + fan manual switches (`engine.toggleDevice`), unsure banner → Activity, today stats, recent (`activityLog`)
- **Activity:** chips All / Toggles / Unsure / Device
- **Settings:** hub + panels; server fields via `engine.updateSettings`, local a11y/notifications via `usePrefs`
- **Hidden “Lab”** section OK for eval hooks (`startCue`, `exportCued`, etc.) on engine

## Product copy (accurate)

- User **looks at desk lamp or PC fan ~2 seconds** to toggle (laptop webcam + CV on laptop).
- **Phone is the control UI** (preview + status), not the primary camera unless remote camera mode.
- **Unsure / abstain** = nothing switched — UI is calm and safe (amber), not red error panic.
- Devices: **lamp**, **fan** (plug optional / lower priority).

## Deliverable

1. **Full `web/` tree** as a zip: `src/`, `public/`, configs, `npm run dev` / `npm run build` works.
2. **`INTEGRATION.md`**: what you replaced vs kept, how to merge into our repo.
3. Deliver in **3 passes** if needed: (1) design system + shell + Home, (2) Live, (3) Activity + Settings + Auth flows + Lab + final zip.

## Out of scope

- Python backend changes
- Rewriting WebSocket `tick` / `hello` message shapes

---

End of prompt.
