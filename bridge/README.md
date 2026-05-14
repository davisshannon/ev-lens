# EV Lens OAuth Bridge

Stateless Cloudflare Worker. Sole job: receive Tesla's OAuth callback, forward the code to the user's local EV Lens instance. Stores nothing.

## Deploy to Cloudflare

```bash
cd bridge
npm install
npx wrangler deploy
```

Then add a custom domain (`auth.ev-lens.com`) in the Cloudflare Workers dashboard.

## Required secrets (set in Cloudflare dashboard → Workers → ev-lens-bridge → Settings → Variables)

| Secret | Value |
|--------|-------|
| `BRIDGE_SECRET` | Same value as `SECRET_KEY` in your EV Lens `.env` |
| `TESLA_CLIENT_ID` | Your Tesla app client ID from developer.tesla.com |

Optional variable (already set to `*` in wrangler.toml — allows any signed instance):

| Variable | Value |
|----------|-------|
| `ALLOWED_ORIGINS` | `*` (default) or comma-separated list e.g. `http://localhost:8000,https://evlens.myhome.net` |

## Tesla Developer Portal setup

At [developer.tesla.com](https://developer.tesla.com), when registering your app:

| Field | Value |
|-------|-------|
| **Allowed Origins** | `https://auth.ev-lens.com` |
| **Redirect URIs** | `https://auth.ev-lens.com/callback` |
| **Scopes** | `openid offline_access vehicle_device_data vehicle_location` |

> If using a custom bridge domain, replace `auth.ev-lens.com` with your domain everywhere.

## How it works

```
User clicks "Connect Tesla" in EV Lens
  │
  ▼
GET https://auth.ev-lens.com/authorize
    ?instance=http://localhost:8000
    &state=<random>
  │
  ├─ Bridge signs state (encodes instance URL + HMAC)
  ├─ Redirects to Tesla OAuth
  │
  ▼
User authorises on Tesla's site
  │
  ▼
Tesla calls GET https://auth.ev-lens.com/callback
    ?code=<auth_code>
    &state=<signed_state>
  │
  ├─ Bridge verifies HMAC, extracts instance URL
  ├─ Redirects to http://localhost:8000/api/v1/auth/tesla/callback
  │     ?code=<auth_code>&state=<original_state>
  │
  ▼
Local EV Lens instance exchanges code for tokens directly with Tesla
(bridge is no longer involved)
```

## Local development

```bash
npm run dev
# Worker runs at http://localhost:8787
```

Test the authorize redirect:
```
http://localhost:8787/authorize?instance=http://localhost:8000&state=test123
```
