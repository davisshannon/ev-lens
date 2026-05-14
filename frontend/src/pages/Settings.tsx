import { useState } from "react";
import { api } from "../api/client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

interface Integration {
  id: string;
  integration_type: string;
  name: string;
  enabled: boolean;
  last_success_at: string | null;
  last_error: string | null;
}

function useIntegrations() {
  return useQuery<Integration[]>({
    queryKey: ["integrations"],
    queryFn: () => api.get("/integrations").then((r) => r.data),
    staleTime: 30_000,
  });
}

export function SettingsPage() {
  const qc = useQueryClient();
  const { data: integrations } = useIntegrations();
  const [teslaConnecting, setTeslaConnecting] = useState(false);
  const [teslaError, setTeslaError] = useState<string | null>(null);

  const [wcHost, setWcHost] = useState("");
  const [pwHost, setPwHost] = useState("");
  const [pwPassword, setPwPassword] = useState("");
  const [hwError, setHwError] = useState<string | null>(null);
  const [hwSuccess, setHwSuccess] = useState<string | null>(null);

  const addWallConnector = useMutation({
    mutationFn: (body: { host: string }) =>
      api.post("/integrations/wall-connector", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["integrations"] });
      setHwSuccess("Wall Connector connected.");
      setWcHost("");
    },
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : "Failed to connect Wall Connector";
      setHwError(msg);
    },
  });

  const addPowerwall = useMutation({
    mutationFn: (body: { host: string; password: string }) =>
      api.post("/integrations/powerwall", body).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["integrations"] });
      setHwSuccess("Powerwall connected.");
      setPwHost("");
      setPwPassword("");
    },
    onError: (e: unknown) => {
      const msg = e instanceof Error ? e.message : "Failed to connect Powerwall";
      setHwError(msg);
    },
  });

  async function handleConnectTesla() {
    setTeslaConnecting(true);
    setTeslaError(null);
    try {
      const { data } = await api.get<{ auth_url: string }>("/auth/tesla/url");
      window.open(data.auth_url, "_blank", "width=600,height=700");
    } catch {
      setTeslaError("Failed to generate Tesla auth URL. Check TESLA_CLIENT_ID in .env.");
    } finally {
      setTeslaConnecting(false);
    }
  }

  const teslaIntegration = integrations?.find((i) => i.integration_type === "tesla_fleet");
  const wcIntegration = integrations?.find((i) => i.integration_type === "wall_connector");
  const pwIntegration = integrations?.find((i) => i.integration_type === "powerwall");

  return (
    <div className="max-w-lg space-y-5">
      <h1 className="text-xl font-semibold text-gray-100">Settings</h1>

      {/* Tesla */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-medium text-gray-200">Tesla Fleet API</h2>
            <p className="text-sm text-gray-500 mt-1">
              Connect your Tesla account via the official Fleet API.
            </p>
          </div>
          {teslaIntegration && (
            <StatusDot ok={!teslaIntegration.last_error} />
          )}
        </div>

        {teslaError && <ErrorBox message={teslaError} />}

        {teslaIntegration ? (
          <p className="text-sm text-green-400">
            Connected · Last poll{" "}
            {teslaIntegration.last_success_at
              ? new Date(teslaIntegration.last_success_at).toLocaleTimeString()
              : "never"}
          </p>
        ) : (
          <button
            onClick={handleConnectTesla}
            disabled={teslaConnecting}
            className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500/90 disabled:opacity-50"
          >
            {teslaConnecting ? "Opening Tesla…" : "Connect Tesla Account"}
          </button>
        )}
      </section>

      {/* Wall Connector */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-medium text-gray-200">Wall Connector</h2>
            <p className="text-sm text-gray-500 mt-1">
              Tesla Wall Connector Gen 3 local telemetry. Must be on the same network.
            </p>
          </div>
          {wcIntegration && <StatusDot ok={!wcIntegration.last_error} />}
        </div>

        {hwError && <ErrorBox message={hwError} />}
        {hwSuccess && <p className="text-sm text-green-400">{hwSuccess}</p>}

        {wcIntegration ? (
          <p className="text-sm text-green-400">Connected</p>
        ) : (
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="192.168.1.x"
              value={wcHost}
              onChange={(e) => setWcHost(e.target.value)}
              className="flex-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
            />
            <button
              onClick={() => { setHwError(null); setHwSuccess(null); addWallConnector.mutate({ host: wcHost }); }}
              disabled={!wcHost || addWallConnector.isPending}
              className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-50"
            >
              {addWallConnector.isPending ? "Testing…" : "Connect"}
            </button>
          </div>
        )}
      </section>

      {/* Powerwall */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-medium text-gray-200">Powerwall / Energy Gateway</h2>
            <p className="text-sm text-gray-500 mt-1">
              Local Gateway API. Password is the last 5 characters of the Gateway serial number.
            </p>
          </div>
          {pwIntegration && <StatusDot ok={!pwIntegration.last_error} />}
        </div>

        {pwIntegration ? (
          <p className="text-sm text-green-400">Connected</p>
        ) : (
          <div className="space-y-2">
            <input
              type="text"
              placeholder="Gateway IP (e.g. 192.168.1.x)"
              value={pwHost}
              onChange={(e) => setPwHost(e.target.value)}
              className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
            />
            <div className="flex gap-2">
              <input
                type="password"
                placeholder="Gateway password (last 5 of serial)"
                value={pwPassword}
                onChange={(e) => setPwPassword(e.target.value)}
                className="flex-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
              />
              <button
                onClick={() => { setHwError(null); setHwSuccess(null); addPowerwall.mutate({ host: pwHost, password: pwPassword }); }}
                disabled={!pwHost || !pwPassword || addPowerwall.isPending}
                className="rounded-lg bg-gray-700 px-4 py-2 text-sm font-medium text-gray-200 hover:bg-gray-600 disabled:opacity-50"
              >
                {addPowerwall.isPending ? "Testing…" : "Connect"}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Tariffs placeholder */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5">
        <h2 className="text-base font-medium text-gray-200">Tariffs</h2>
        <p className="text-sm text-gray-500 mt-1">
          Configure electricity pricing for charge cost estimates and planning.
          Use the API at <code className="text-xs bg-gray-800 px-1 rounded">/api/v1/tariffs</code> or
          the full tariff UI coming in M3.
        </p>
      </section>
    </div>
  );
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span className={`h-2.5 w-2.5 rounded-full mt-1 ${ok ? "bg-green-400" : "bg-red-400"}`} />
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <p className="text-sm text-red-400 bg-red-950 rounded-lg px-3 py-2">{message}</p>
  );
}
