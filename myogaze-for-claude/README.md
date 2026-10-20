# MyoGaze → Claude handoff package

## For you (Melvin)

1. Download **`myogaze-for-claude.zip`** from your **Downloads** folder  
   (or zip this folder again if you moved it).
2. Open Claude → **attach the zip** (paperclip).
3. Open **`PROMPT_FOR_CLAUDE.md`** → copy everything under "Paste this entire message" into the chat → Send.

## Zip contents

| Path | Purpose |
|------|---------|
| `PROMPT_FOR_CLAUDE.md` | Message to paste into Claude |
| `design/MyoGaze-mobile-UI-preview.html` | Visual / UX target |
| `web/src/useNeuroShift.ts` | Engine hook + WebSocket |
| `web/src/api.ts`, `auth.ts`, `serverConfig.ts`, … | Backend wire protocol |
| `web/src/components/views/LiveView.tsx` | Real JPEG + detection overlays |
| `web/src/App.tsx` + views | Reference behavior |
| `web/package.json`, `vite.config.ts` | Build toolchain |

When Claude returns a zip, merge into `NeuroShift/web/` or ask Cursor to integrate.
