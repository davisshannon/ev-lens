import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";

type Step = "account" | "bridge" | "done";

interface SetupStatus {
  needs_setup: boolean;
  bridge_secret: string | null;
}

export function SetupPage({ status }: { status: SetupStatus }) {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("account");

  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleCreateAccount() {
    setError(null);
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.post<{ access_token: string }>("/auth/setup", {
        username: username.trim(),
        password,
      });
      localStorage.setItem("ev_lens_token", data.access_token);
      // If there's a bridge secret to show, go to that step
      if (status.bridge_secret) {
        setStep("bridge");
      } else {
        setStep("done");
      }
    } catch (e: unknown) {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Setup failed. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleCopy() {
    if (status.bridge_secret) {
      navigator.clipboard.writeText(status.bridge_secret);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  function handleFinish() {
    navigate("/today");
    window.location.reload();
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-bold text-gray-100">EV Lens</h1>
          <p className="text-sm text-gray-500">First-run setup</p>
        </div>

        {/* Step indicators */}
        <div className="flex items-center justify-center gap-2">
          {(["account", "bridge", "done"] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-colors ${
                  step === s
                    ? "bg-brand-500 text-white"
                    : ["done", "bridge"].includes(step) && i === 0
                    ? "bg-green-600 text-white"
                    : step === "done" && i === 1
                    ? "bg-green-600 text-white"
                    : "bg-gray-800 text-gray-500"
                }`}
              >
                {(step === "bridge" && i === 0) || (step === "done" && i < 2) ? "✓" : i + 1}
              </div>
              {i < 2 && <div className="w-8 h-px bg-gray-800" />}
            </div>
          ))}
        </div>

        {/* Step: Create account */}
        {step === "account" && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-200">Create your account</h2>
              <p className="text-sm text-gray-500 mt-1">
                This is the admin account for your EV Lens instance.
              </p>
            </div>

            {error && (
              <p className="text-sm text-red-400 bg-red-950 rounded-lg px-3 py-2">{error}</p>
            )}

            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 block mb-1">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2 focus:outline-none focus:border-brand-500"
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2 focus:outline-none focus:border-brand-500"
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 block mb-1">Confirm password</label>
                <input
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateAccount()}
                  className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2 focus:outline-none focus:border-brand-500"
                  autoComplete="new-password"
                />
              </div>
            </div>

            <button
              onClick={handleCreateAccount}
              disabled={loading || !username || !password || !confirm}
              className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-500/90 disabled:opacity-50 transition-colors"
            >
              {loading ? "Creating…" : "Create Account"}
            </button>
          </div>
        )}

        {/* Step: Bridge secret */}
        {step === "bridge" && status.bridge_secret && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-gray-200">Sync Cloudflare secret</h2>
              <p className="text-sm text-gray-500 mt-1">
                Your Tesla OAuth bridge at{" "}
                <span className="text-gray-300">auth.ev-lens.com</span> must share this secret
                key with your EV Lens instance. Copy it to{" "}
                <span className="text-gray-300">
                  Workers &amp; Pages → ev-lens → Settings → Variables and Secrets →{" "}
                  <code className="text-xs bg-gray-800 px-1 rounded">BRIDGE_SECRET</code>
                </span>
                .
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-gray-500 block">BRIDGE_SECRET</label>
              <div className="flex gap-2">
                <code className="flex-1 rounded-lg bg-gray-800 border border-gray-700 text-green-400 text-xs px-3 py-2 font-mono break-all">
                  {status.bridge_secret}
                </code>
                <button
                  onClick={handleCopy}
                  className="flex-shrink-0 rounded-lg bg-gray-700 px-3 py-2 text-xs text-gray-300 hover:bg-gray-600 transition-colors"
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>

            <div className="rounded-lg bg-yellow-950 border border-yellow-900 px-3 py-2">
              <p className="text-xs text-yellow-400">
                If BRIDGE_SECRET in Cloudflare doesn't match this value, Tesla OAuth will fail.
                You can find this value again in your backend <code>.env</code> file as{" "}
                <code>SECRET_KEY</code>.
              </p>
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleFinish}
                className="flex-1 rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-500/90 transition-colors"
              >
                Done, take me in
              </button>
              <button
                onClick={handleFinish}
                className="rounded-lg bg-gray-800 px-4 py-2.5 text-sm font-medium text-gray-400 hover:bg-gray-700 transition-colors"
              >
                Skip
              </button>
            </div>
          </div>
        )}

        {/* Step: Done (no bridge secret case) */}
        {step === "done" && (
          <div className="rounded-xl bg-gray-900 border border-gray-800 p-6 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-green-900 flex items-center justify-center mx-auto">
              <span className="text-green-400 text-2xl">✓</span>
            </div>
            <div>
              <h2 className="text-base font-semibold text-gray-200">You're all set!</h2>
              <p className="text-sm text-gray-500 mt-1">
                Connect your Tesla in Settings to start monitoring.
              </p>
            </div>
            <button
              onClick={handleFinish}
              className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-500/90 transition-colors"
            >
              Open EV Lens
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
