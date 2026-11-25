# Backend plan

Backend work for the app in [frontend-plan.md](frontend-plan.md). The database is clean (no real data yet), so new tables and changes to existing ones need no data migration.

## Done

- **Web origin for local development.** `app_url` and `cors_origins` now default to `http://localhost:8081`, the Expo web dev server. Phone apps do not send browser origins, so CORS only matters for the web app.

## To do: code

- **Household-wide coin history** (needed for frontend step 4). The large-screen parent dashboard shows every kid's coins in one table, filtered by kid and by type (task, prize, adjustment). The backend lists transactions one kid at a time, so it needs `GET /households/{hid}/transactions?kid_id=&kind=` for parents, with `kid_id` and `kid_display_name` on each entry.
- **Delete your own account** (needed before the app stores). Apple and Google require apps that create accounts to let users delete them from the app. Add `DELETE /me` for parents, with rules for households where the parent is the only admin, and decide how a kid account is deleted (today an admin can delete a kid with `DELETE /households/{hid}/kids/{kid_id}`).
- **Push notifications** (frontend step 6).
  - A `push_devices` table: user, Expo push token, platform, created and last seen times. A token belongs to one user; registering it again moves it to the new user.
  - `PUT /me/push-devices` `{token, platform}` to register after login, and `DELETE /me/push-devices/{token}` on logout. Logout should also remove the device's token.
  - A `push` value in `NotificationChannel`, so users can turn push off per notification type.
  - A `PushSender` protocol in `core/push/`, selected by a `push_backend` setting, like `EmailSender`: a `console` backend for local development and an `expo` backend that sends through Expo's push service. `services.notifications.notify` sends a push after the commit for each enabled device.
  - Remove tokens that Expo reports as no longer registered (`DeviceNotRegistered`).
- **Real email backend** (needed for any deployed environment). Only the `console` email backend exists, so login codes and invitations cannot reach real users yet. Add a provider behind the `EmailSender` protocol.
- **Photo storage for deployment.** Only the `local` photo backend exists. A deployed backend needs a persistent volume for `photo_dir` or an object storage backend behind `PhotoStore`.
- **Optional before launch:** squash the Alembic migrations into one, since there is no data to migrate.

## To do: manual setup

These need accounts, keys or a domain, so they cannot be done in code.

- **Settings for each deployed environment.** Set `app_url` to the web app's address and `cors_origins` to its origin, for example `app_url=https://app.example.com` and `cors_origins=["https://app.example.com"]`.
- **Email provider.** Create an account with the chosen provider, verify the sending domain (SPF and DKIM DNS records) and put its API key in the backend's environment.
- **Developer accounts.**
  - An Apple Developer Program membership, for iOS builds, TestFlight and the App Store.
  - A Google Play Console account, for Android.
  - An Expo account for EAS Build and push notifications.
- **Links that open the app** (invitation links on phones). Serve these two files from the web app's domain, over HTTPS, as `application/json`, without redirects:
  - `/.well-known/apple-app-site-association`, with the Apple Team ID and the iOS bundle identifier, for the path `/invitations/*`.
  - `/.well-known/assetlinks.json`, with the Android package name and the SHA-256 fingerprint of the app signing key (shown in EAS or the Play Console).
  - Add the domain to `ios.associatedDomains` and `android.intentFilters` in the Expo app config.
- **Push credentials.**
  - iOS: let EAS create or upload an APNs key.
  - Android: create a Firebase project and upload its FCM V1 service account key to EAS.
  - Optional: turn on Expo's push security setting and put the Expo access token in the backend's environment for the `expo` push backend.
- **Web hosting security.** The web app keeps the session token in `localStorage`. Serve it with a strict Content Security Policy (scripts only from its own origin, `connect-src` limited to the API) to reduce the risk of XSS reading the token.
- **Privacy.** Publish a privacy policy and fill in the stores' privacy and children's data forms (COPPA in the US, GDPR in the EU), before the first store submission.
