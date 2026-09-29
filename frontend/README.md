# frontend: the team console

React + TypeScript + Tailwind (built with Vite), served by the backend at `/console/` behind
the team password. Docker builds it for you; no Node needed on the laptop.

| Folder / file | What |
|---|---|
| `src/pages/Overview.tsx` | counts, languages, call status, most common occupations, latest calls |
| `src/pages/Calls.tsx` | every call, searchable, refreshes every 5 s |
| `src/pages/CallDetail.tsx` | one call: the live log, profile, the caller's words (+ English) and recording, what was understood, consents |
| `src/LiveLog.tsx`, `src/liveLog.ts` | the live log: events → categorised entries (system said, caller, answers, understanding, background, problems, call) with filters, search and follow-live |
| `src/pages/People.tsx` | one row per caller with their latest answers |
| `src/pages/Occupations.tsx` | the 59 occupations and the words callers use |
| `src/api.ts` | calls the backend's `/console/api/*` (types + auto-refresh hook) |
| `src/labels.ts` | readable names for stored values and timeline events |
| `src/ui.tsx`, `src/CallTable.tsx` | shared pieces |

Development (Node 22): `npm install`, `npm run dev`, open `http://localhost:5173/console/` while
the backend runs on port 8000. `npm run build` must pass (strict TypeScript).
