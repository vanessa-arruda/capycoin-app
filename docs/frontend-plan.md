# Frontend plan

This is the plan for the Capycoin app: one app for parents and kids that runs on the web first, and later on Android and iOS from the same code. The backend work it depends on is in [backend-plan.md](backend-plan.md).

## Decisions

- **One app for both roles.** Parent and kid screens live in one app. After login, the user's account type decides which screens they see.
- **Web first.** Every step is built, run and tested on the web, locally, before anything is deployed. Phone sizes are checked with the browser's responsive design mode (390 × 844 for phones, 1280 wide and up for the parent desktop layout).
- **Phones stay in the plan.** Android and iOS builds come in step 5. Until then, every component is written so it also works on phones: React Native components only, no HTML elements, no browser APIs outside the few platform files listed below.
- **Native feel on phones.** The phone apps use native navigation, gestures and components (React Native), not a web page inside an app.
- **Design source.** The screens, colours and logo files are in the design canvas: https://claude.ai/artifact/5nCWaDe7qSQBPZnUK24XF7. The logo and coin SVGs are in `resources/`.

## Stack

| Area | Choice |
|---|---|
| App framework | Expo (React Native) with TypeScript, using the Expo SDK that is current when the project is set up |
| Routing | Expo Router (file-based routes, same URLs on the web and deep links on phones) |
| Web output | React Native Web, through Expo |
| Styling | NativeWind (Tailwind class names for React Native), with the design's colours in the Tailwind theme |
| Fonts | Nunito (400, 600, 700, 800) through `expo-font` |
| Images and SVG logos | `expo-image`, which shows SVG on web, Android and iOS |
| API types and client | Types generated from the backend's OpenAPI spec with `openapi-typescript`, requests through `openapi-fetch` |
| Server data | TanStack Query (caching, refresh on focus, pagination for `Page[...]` lists) |
| Animations and gestures | Reanimated and Gesture Handler |
| Session token storage | `expo-secure-store` on phones, `localStorage` on the web |
| Camera and photo picking | `expo-image-picker` (works on the web too) |
| Push notifications | `expo-notifications`, step 6 only |
| Unit and component tests | Jest with React Native Testing Library |
| End-to-end tests | Playwright on the web; Maestro on phones from step 5 |
| Package manager | npm, with Node from `.tool-versions` |

## Project layout

```
app-frontend/
  app/                      Expo Router routes
    _layout.tsx             providers: fonts, TanStack Query, session
    index.tsx               sends the user to login, the kid screens or the parent screens
    login.tsx
    invitations/accept.tsx  matches {app_url}/invitations/accept#token=...
    (kid)/                  kid screens, bottom tabs: Home, Store, Wallet
    (parent)/               parent screens, bottom tabs on phones, sidebar on wide screens
  src/
    api/                    generated types (schema.d.ts) and the API client
    components/             shared components (Button, Card, CoinAmount, Avatar, ...)
    features/               screen logic grouped by area (auth, tasks, prizes, wallet, ...)
    theme/                  colours and spacing shared with tailwind.config.js
    session/                token storage and the current user and household
  assets/                   fonts, plus logo and coin exported from resources/
```

## Rules for components

- Use React Native components (`View`, `Text`, `Pressable`, `TextInput`, `ScrollView`, `FlatList`) and NativeWind classes. Do not use HTML elements or `window` and `document` in shared code.
- When a platform needs different code, use a platform file (`Thing.web.tsx` next to `Thing.tsx`) or `Platform.OS`. Keep these small and list them here as they are added. Known ones:
  - **Parent desktop sidebar** and the **wide coin history table**: web only, for wide screens. Phones use tabs and a list.
  - **Token storage**: `localStorage` on the web, `expo-secure-store` on phones.
  - **Proof photos shown to parents**: the photo endpoint needs the `Authorization` header. Phones can pass headers to `expo-image`. On the web an image tag cannot send headers, so the web version fetches the photo and shows it from a blob URL.
- Every pressable element has an accessibility role and label, and is at least 44 px tall. Text meets 4.5:1 contrast, as in the design.
- Layout is mobile first. Wide layouts use NativeWind breakpoints (`md:`, `lg:`) and are checked in responsive design mode.

## Theme from the design

| Token | Value | Use |
|---|---|---|
| `teal` | `#0E7C6B` | Primary buttons, active tabs, links |
| `teal-dark` | `#0A5C50` | Pressed and hover states, text on light teal |
| `teal-light` | `#D3EEE7` | Success and selected backgrounds |
| `ink` | `#14202B` | Main text |
| `ink-2` | `#3D4752` | Body text |
| `muted` | `#56606B` | Secondary text |
| `border` | `#C9D3DB` | Inputs and outlined buttons |
| `bg-kid` | `#EEF6F3` | Kid screens background |
| `bg-parent` | `#F4F6F8` | Parent screens background |
| `gold` | `#F5B700` | Coin, progress bars |
| `gold-light` | `#FFF4CC` | Reward and price backgrounds |
| `gold-text` | `#5C4100` / `#7A5600` | Coin amounts on light gold |
| `warn` | `#8A3B00` on `#FFEBD6` | Negative balances, "not yet" notices |
| `dot` | `#E8590C` | Unread badge |

Corner radii are 14 px for inputs and small buttons, 16 to 18 px for main buttons, 20 to 22 px for cards and 28 px for the kid balance card.

## Local development

- Backend: `make be-db-up`, `make be-migrate` and `make be-dev` (API on `http://localhost:8000`).
- Frontend Makefile targets, run from the repo root, prefixed `fe-`:
  - `fe-install`: `npm install` in `app-frontend/`.
  - `fe-dev`: `npx expo start --web` (web app on `http://localhost:8081`, the backend's default `app_url` and CORS origin).
  - `fe-api-types`: writes the backend's OpenAPI spec to a file and generates `src/api/schema.d.ts` from it. Run it after any backend endpoint change.
  - `fe-test`: Jest.
  - `fe-e2e`: Playwright against the local web app and backend.
  - `fe-lint`: ESLint and the TypeScript check.
- The API address comes from `EXPO_PUBLIC_API_URL` (default `http://localhost:8000`).
- Emails, including login codes, are printed by the backend's console email backend. Read the code from the backend's terminal.

## Steps

Each step ends with the screens working on the web against the local backend, with component tests and at least one Playwright test for the main path.

### 1. Base setup

- Create the Expo project in `app-frontend/` with TypeScript, Expo Router, NativeWind, the theme, Nunito and the logo files.
- Add the `fe-` Makefile targets and generate the API client.
- Session: login with an email code and with username and password, keep the token, log out, and send the user back to login on any `401`.
- Load `GET /me` and `GET /me/households` after login and route to the kid or parent screens by the user's `role`. A parent with several households uses the first one for now (the household switcher is out of scope).
- Screens: sign in (design: Main). Accepting an invitation (design: AcceptInvite) can come here or in step 3.

### 2. Kid screens

- Home, Task (with an optional photo and note), Store (with the confirm sheet), Wallet and Notifications (designs: KidHome, KidTask, KidStore, KidWallet, KidNotifications).
- Proof photos are picked with `expo-image-picker`; on the web this opens the file picker. Keep uploads under the backend's 5 MB limit.

### 3. Parent screens

- Review list and review detail, Kids and kid detail, New task, Manage tasks and prizes, Notifications, Household settings for admins, and Accept invitation if not done in step 1 (designs: ParentHome, ParentReview, ParentKid, ParentNewTask, ParentManage, ParentNotifications, AdminSettings, AcceptInvite).
- The first-run flow (creating a household, adding kids) waits for the account and household creation proposal to be approved and designed.

### 4. Parent desktop layout

- Sidebar navigation and the two-column review and kids layout for wide screens (design: Desktop).
- The household-wide coin history table needs a new backend endpoint; see [backend-plan.md](backend-plan.md).

### 5. Android and iOS

- Run the app on simulators and phones with Expo Go or a development build, and fix anything that differs from the web.
- Camera for proof photos, secure token storage, app icon and splash screen from `capycoin-logo.svg`.
- Links that open the app: invitation links and the universal and app link files (manual setup in [backend-plan.md](backend-plan.md)).
- Builds with EAS Build. Maestro tests for the main kid and parent paths.

### 6. Push notifications

- Ask for permission after login on phones, register the device's Expo push token with the backend, and open the right screen when a notification is tapped.
- On the web, notifications refresh when the app comes back into focus and on a timer.

## Open questions

- **App store category:** list the app in the App Store Kids category and Google Play's family programme, or as an app for parents with kid accounts inside? The Kids category limits analytics, ads and outside links, so this decides which crash reporting and analytics tools can be used. Decide before step 5.
- **First-run flow:** waiting for approval of the account and household creation proposal.
- **Old frontend branch:** `origin/capycoin-frontend` has a Next.js frontend written against an older API. It is not used by this plan; its author should know before it is replaced.
