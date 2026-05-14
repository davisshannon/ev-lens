/**
 * EV Lens OAuth Bridge — Cloudflare Worker
 *
 * This is the ONLY public-facing component of EV Lens. It has one job:
 * receive Tesla's OAuth callback, then redirect the code+state back to
 * the user's local EV Lens instance. Nothing is stored. No database.
 * No logging of tokens or codes.
 *
 * Flow:
 *   1. Local app calls GET /authorize?instance=http://localhost:8000&...
 *      Bridge redirects to Tesla with a signed state param that encodes
 *      the instance URL.
 *   2. Tesla calls GET /callback?code=...&state=...
 *      Bridge decodes the instance URL from state, redirects to:
 *        http://<instance>/api/v1/auth/tesla/callback?code=...&state=...
 *
 * Environment variables (set in Cloudflare dashboard / wrangler.toml):
 *   BRIDGE_SECRET   — shared secret used to sign state (must match backend SECRET_KEY)
 *   TESLA_CLIENT_ID — Tesla app client ID
 *   ALLOWED_ORIGINS — comma-separated list of allowed instance origins
 *                     e.g. "http://localhost:8000,https://evlens.myhome.net"
 *                     Use "*" to allow any origin (self-hosted, trust the signature)
 */

export interface Env {
  BRIDGE_SECRET: string;
  TESLA_CLIENT_ID: string;
  ALLOWED_ORIGINS: string;
}

const TESLA_AUTH_BASE = "https://auth.tesla.com/oauth2/v3";
const SCOPES = "openid offline_access vehicle_device_data vehicle_location";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/") return homePage();
    if (url.pathname === "/health") return new Response("ok", { status: 200 });
    if (url.pathname === "/authorize") return handleAuthorize(url, env);
    if (url.pathname === "/callback") return handleCallback(url, env);

    return new Response("Not found", { status: 404 });
  },
};

/**
 * GET /authorize?instance=<local_url>&state=<caller_state>
 *
 * Wraps the caller's state with the instance URL (signed), then redirects
 * to Tesla's OAuth authorize endpoint.
 */
async function handleAuthorize(url: URL, env: Env): Promise<Response> {
  const instance = url.searchParams.get("instance");
  const callerState = url.searchParams.get("state") ?? "";

  if (!instance) {
    return errorPage("Missing required parameter: instance");
  }

  // Validate the instance origin is in the allowlist
  if (!isAllowedOrigin(instance, env.ALLOWED_ORIGINS)) {
    return errorPage(
      `Origin not allowed: ${new URL(instance).origin}. ` +
      `Add it to ALLOWED_ORIGINS in the bridge configuration.`
    );
  }

  // Pack instance + caller state into a signed bridge state
  const bridgeState = await packState(callerState, instance, env.BRIDGE_SECRET);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: env.TESLA_CLIENT_ID,
    redirect_uri: `${url.origin}/callback`,
    scope: SCOPES,
    state: bridgeState,
  });

  return Response.redirect(`${TESLA_AUTH_BASE}/authorize?${params}`, 302);
}

/**
 * GET /callback?code=...&state=...&error=...
 *
 * Tesla redirects here after the user authorises (or denies).
 * Unpack state, verify signature, redirect code back to local instance.
 */
async function handleCallback(url: URL, env: Env): Promise<Response> {
  const error = url.searchParams.get("error");
  const errorDesc = url.searchParams.get("error_description") ?? "";
  const code = url.searchParams.get("code");
  const bridgeState = url.searchParams.get("state") ?? "";

  // Unpack signed state — get back caller state + instance URL
  const unpacked = await unpackState(bridgeState, env.BRIDGE_SECRET);
  if (!unpacked) {
    return errorPage("Invalid or expired state parameter. Please try connecting again.");
  }

  const { callerState, instance } = unpacked;

  if (error) {
    // Redirect error back to instance so local app can surface it
    const params = new URLSearchParams({ error, error_description: errorDesc, state: callerState });
    return Response.redirect(`${instance}/api/v1/auth/tesla/callback?${params}`, 302);
  }

  if (!code) {
    return errorPage("No code received from Tesla.");
  }

  // Redirect code + original caller state back to local instance
  const params = new URLSearchParams({ code, state: callerState });
  return Response.redirect(`${instance}/api/v1/auth/tesla/callback?${params}`, 302);
}

// ── State packing/unpacking ───────────────────────────────────────────────────
//
// State format (base64url of JSON):
//   { cs: <callerState>, inst: <instanceUrl>, ts: <unixSeconds>, sig: <hmac-hex> }
//
// The HMAC covers cs+inst+ts to prevent tampering with the instance URL.
// TTL: 10 minutes.

const STATE_TTL_S = 600;

interface BridgeState {
  cs: string;   // caller state
  inst: string; // instance URL
  ts: number;   // issued timestamp
  sig: string;  // HMAC-SHA256 hex
}

async function packState(callerState: string, instance: string, secret: string): Promise<string> {
  const ts = Math.floor(Date.now() / 1000);
  const sig = await hmacHex(secret, `${callerState}:${instance}:${ts}`);
  const payload: BridgeState = { cs: callerState, inst: instance, ts, sig };
  return btoa(JSON.stringify(payload)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

async function unpackState(raw: string, secret: string): Promise<{ callerState: string; instance: string } | null> {
  try {
    const json = atob(raw.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as BridgeState;

    // TTL check
    if (Math.floor(Date.now() / 1000) - payload.ts > STATE_TTL_S) return null;

    // Signature check
    const expected = await hmacHex(secret, `${payload.cs}:${payload.inst}:${payload.ts}`);
    if (!timingSafeEqual(expected, payload.sig)) return null;

    return { callerState: payload.cs, instance: payload.inst };
  } catch {
    return null;
  }
}

async function hmacHex(secret: string, message: string): Promise<string> {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Array.from(new Uint8Array(sig)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function isAllowedOrigin(instance: string, allowedOrigins: string): boolean {
  if (allowedOrigins.trim() === "*") return true;
  try {
    const origin = new URL(instance).origin;
    return allowedOrigins.split(",").map((s) => s.trim()).includes(origin);
  } catch {
    return false;
  }
}

function homePage(): Response {
  return new Response(
    `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EV Lens Auth Bridge</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0c1117; color: #e2e8f0;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { max-width: 480px; padding: 2rem; text-align: center; }
    h1 { color: #0ea5e9; font-size: 1.5rem; margin-bottom: 0.5rem; }
    p { color: #94a3b8; line-height: 1.6; }
    .badge { display: inline-block; background: #0ea5e920; color: #0ea5e9;
             border: 1px solid #0ea5e940; border-radius: 9999px; padding: 0.25rem 0.75rem;
             font-size: 0.75rem; margin-top: 1rem; }
  </style>
</head>
<body>
  <div class="card">
    <h1>EV Lens</h1>
    <p>This is the EV Lens OAuth bridge. It receives Tesla's authorisation callback
       and forwards your token back to your local EV Lens instance.</p>
    <p>Nothing is stored here. No credentials pass through this service —
       only an authorisation code that your local instance exchanges directly with Tesla.</p>
    <div class="badge">Stateless · Privacy-preserving · Open source</div>
  </div>
</body>
</html>`,
    { headers: { "Content-Type": "text/html;charset=UTF-8" } }
  );
}

function errorPage(message: string): Response {
  return new Response(
    `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>EV Lens Auth Bridge — Error</title>
  <style>
    body { font-family: system-ui, sans-serif; background: #0c1117; color: #e2e8f0;
           display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { max-width: 480px; padding: 2rem; text-align: center; }
    h1 { color: #f87171; font-size: 1.25rem; }
    p { color: #94a3b8; }
    code { background: #1e293b; padding: 0.75rem 1rem; border-radius: 0.5rem;
           display: block; margin: 1rem 0; font-size: 0.875rem; color: #e2e8f0; word-break: break-word; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Connection error</h1>
    <code>${escapeHtml(message)}</code>
    <p>Close this window and try connecting again from your EV Lens instance.</p>
  </div>
</body>
</html>`,
    { status: 400, headers: { "Content-Type": "text/html;charset=UTF-8" } }
  );
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
