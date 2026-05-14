import { useState } from "react";
import { api } from "../api/client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAssignTariff, useCreateTariff, useDeleteTariff, useTariffs } from "../hooks/useCharges";
import { useVehicles } from "../hooks/useVehicles";
import { useAppSettings, useSetSetting } from "../hooks/useAppSettings";
import type { AppSettingOut } from "../api/appSettings";
import type { Tariff } from "../types/charge";

// ── Integrations ──────────────────────────────────────────────────────────────

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

// ── Inline setting field ──────────────────────────────────────────────────────

function SettingField({
  setting,
  hint,
  inputType = "text",
}: {
  setting: AppSettingOut;
  hint?: string;
  inputType?: "text" | "password";
}) {
  const setSetting = useSetSetting();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);

  function startEdit() {
    setDraft("");
    setError(null);
    setEditing(true);
  }

  async function handleSave() {
    if (!draft.trim()) {
      setError("Value cannot be empty");
      return;
    }
    setError(null);
    try {
      await setSetting.mutateAsync({ key: setting.key, value: draft.trim() });
      setEditing(false);
    } catch {
      setError("Failed to save — check the server logs");
    }
  }

  function handleCancel() {
    setEditing(false);
    setError(null);
  }

  const displayValue = setting.is_set
    ? setting.is_secret
      ? "••••••"
      : setting.value
    : "";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={`h-2 w-2 flex-shrink-0 rounded-full ${
              setting.is_set ? "bg-green-400" : "bg-gray-600"
            }`}
          />
          <span className="text-sm text-gray-300">{setting.label}</span>
        </div>
        {!editing && (
          <div className="flex items-center gap-3 flex-shrink-0">
            {setting.is_set && !setting.is_secret && (
              <span className="text-xs text-gray-500 font-mono truncate max-w-[160px]">
                {displayValue}
              </span>
            )}
            {setting.is_set && setting.is_secret && (
              <span className="text-xs text-gray-600 font-mono">set</span>
            )}
            <button
              onClick={startEdit}
              className="text-xs text-gray-400 hover:text-gray-200 transition-colors px-2 py-1 rounded hover:bg-gray-700"
            >
              {setting.is_set ? "Edit" : "Set"}
            </button>
          </div>
        )}
      </div>

      {editing && (
        <div className="ml-4 space-y-1.5">
          <input
            type={inputType}
            placeholder={setting.is_set ? "(leave blank to keep current)" : `Enter ${setting.label}`}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoFocus
            className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-1.5 focus:outline-none focus:border-brand-500"
          />
          {hint && <p className="text-xs text-gray-500">{hint}</p>}
          {error && <p className="text-xs text-red-400">{error}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={setSetting.isPending}
              className="rounded-lg bg-brand-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-500/90 disabled:opacity-50"
            >
              {setSetting.isPending ? "Saving…" : "Save"}
            </button>
            <button
              onClick={handleCancel}
              className="rounded-lg bg-gray-800 px-3 py-1.5 text-xs font-medium text-gray-400 hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function SettingsPage() {
  const qc = useQueryClient();
  const { data: integrations } = useIntegrations();
  const { data: appSettings } = useAppSettings();
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
      setTeslaError("Failed to generate Tesla auth URL. Check Tesla Client ID.");
    } finally {
      setTeslaConnecting(false);
    }
  }

  const teslaIntegration = integrations?.find((i) => i.integration_type === "tesla_fleet");
  const wcIntegration = integrations?.find((i) => i.integration_type === "wall_connector");
  const pwIntegration = integrations?.find((i) => i.integration_type === "powerwall");

  // Helper to find a setting by key
  function s(key: string): AppSettingOut | undefined {
    return appSettings?.find((x) => x.key === key);
  }

  const teslaIdSet = s("tesla_client_id")?.is_set ?? false;
  const teslaSecretSet = s("tesla_client_secret")?.is_set ?? false;
  const teslaCredsSet = teslaIdSet && teslaSecretSet;

  return (
    <div className="max-w-lg space-y-5">
      <h1 className="text-xl font-semibold text-gray-100">Settings</h1>

      {/* ── Instance ──────────────────────────────────────────────────────── */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
        <div>
          <h2 className="text-base font-medium text-gray-200">Instance</h2>
          <p className="text-sm text-gray-500 mt-1">
            Core URLs for this EV Lens instance.
          </p>
        </div>

        <div className="space-y-3">
          {s("app_public_url") && (
            <SettingField
              setting={s("app_public_url")!}
              hint="Public URL of this EV Lens instance. Used for Tesla OAuth redirect. e.g. http://localhost:8000 or https://evlens.yourdomain.com"
            />
          )}
          {s("oauth_bridge_url") && (
            <SettingField
              setting={s("oauth_bridge_url")!}
              hint="Leave as https://auth.ev-lens.com unless self-hosting the bridge"
            />
          )}
        </div>
      </section>

      {/* ── Tesla Fleet API ───────────────────────────────────────────────── */}
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

        <div className="space-y-3">
          {s("tesla_client_id") && (
            <SettingField setting={s("tesla_client_id")!} />
          )}
          {s("tesla_client_secret") && (
            <SettingField setting={s("tesla_client_secret")!} inputType="password" />
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
          teslaCredsSet && (
            <button
              onClick={handleConnectTesla}
              disabled={teslaConnecting}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500/90 disabled:opacity-50"
            >
              {teslaConnecting ? "Opening Tesla…" : "Connect Tesla Account"}
            </button>
          )
        )}

        {!teslaCredsSet && !teslaIntegration && (
          <p className="text-xs text-gray-500">Set Client ID and Secret above to enable OAuth.</p>
        )}
      </section>

      {/* ── AI Assistant ──────────────────────────────────────────────────── */}
      <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
        <div>
          <h2 className="text-base font-medium text-gray-200">AI Assistant</h2>
          <p className="text-sm text-gray-500 mt-1">
            Configure API keys for AI providers. The first key that is set will be used.
          </p>
        </div>

        {/* Anthropic */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Anthropic</p>
          {s("anthropic_api_key") && (
            <SettingField setting={s("anthropic_api_key")!} inputType="password" />
          )}
        </div>

        {/* OpenAI */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">OpenAI</p>
          {s("openai_api_key") && (
            <SettingField setting={s("openai_api_key")!} inputType="password" />
          )}
        </div>

        {/* xAI */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">xAI</p>
          {s("xai_api_key") && (
            <SettingField setting={s("xai_api_key")!} inputType="password" />
          )}
        </div>

        {/* AWS Bedrock */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">AWS Bedrock</p>
          {s("aws_access_key_id") && (
            <SettingField setting={s("aws_access_key_id")!} />
          )}
          {s("aws_secret_access_key") && (
            <SettingField setting={s("aws_secret_access_key")!} inputType="password" />
          )}
          {s("aws_region") && (
            <SettingField setting={s("aws_region")!} />
          )}
        </div>

        {/* Model override */}
        <div className="pt-1 border-t border-gray-800">
          {s("ai_model_override") && (
            <SettingField
              setting={s("ai_model_override")!}
              hint="Override the default model for the active provider (e.g. claude-3-5-haiku-20241022)"
            />
          )}
        </div>
      </section>

      {/* ── Hardware ──────────────────────────────────────────────────────── */}
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

      {/* Tariffs */}
      <TariffSection />
    </div>
  );
}

// ── Tariff section (unchanged) ────────────────────────────────────────────────

const PRESET_CONFIGS: Record<string, { label: string; config: Record<string, unknown> }> = {
  flat: {
    label: "Flat rate",
    config: { type: "flat", rate: 0.12 },
  },
  tou: {
    label: "Time-of-Use",
    config: {
      type: "tou",
      windows: [
        { name: "off-peak", start: "21:00", end: "07:00", rate: 0.08 },
        { name: "peak", start: "07:00", end: "21:00", rate: 0.24 },
      ],
    },
  },
  ev_night: {
    label: "EV Night (overnight discount)",
    config: {
      type: "ev_night",
      night_start: "23:00",
      night_end: "07:00",
      night_rate: 0.07,
      day_rate: 0.22,
    },
  },
};

function TariffSection() {
  const { data: tariffs } = useTariffs();
  const { data: vehicles } = useVehicles();
  const createTariff = useCreateTariff();
  const deleteTariff = useDeleteTariff();
  const assignTariff = useAssignTariff();

  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [timezone, setTimezone] = useState(
    Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  );
  const [preset, setPreset] = useState<keyof typeof PRESET_CONFIGS>("flat");
  const [rawConfig, setRawConfig] = useState(
    JSON.stringify(PRESET_CONFIGS.flat.config, null, 2)
  );
  const [configError, setConfigError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  function handlePresetChange(p: keyof typeof PRESET_CONFIGS) {
    setPreset(p);
    setRawConfig(JSON.stringify(PRESET_CONFIGS[p].config, null, 2));
    setConfigError(null);
  }

  async function handleAdd() {
    setFormError(null);
    setConfigError(null);
    let config: Record<string, unknown>;
    try {
      config = JSON.parse(rawConfig);
    } catch {
      setConfigError("Invalid JSON");
      return;
    }
    if (!name.trim()) {
      setFormError("Name is required");
      return;
    }
    try {
      await createTariff.mutateAsync({ name: name.trim(), currency, timezone, config });
      setAdding(false);
      setName("");
      setRawConfig(JSON.stringify(PRESET_CONFIGS.flat.config, null, 2));
    } catch {
      setFormError("Failed to create tariff");
    }
  }

  return (
    <section className="rounded-xl bg-gray-900 border border-gray-800 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-medium text-gray-200">Tariffs</h2>
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="text-xs px-3 py-1.5 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
          >
            + Add tariff
          </button>
        )}
      </div>

      {tariffs && tariffs.length > 0 && (
        <div className="space-y-2">
          {tariffs.map((t) => (
            <TariffRow
              key={t.id}
              tariff={t}
              vehicles={vehicles ?? []}
              onDelete={() => deleteTariff.mutate(t.id)}
              onAssign={(vehicleId) => assignTariff.mutate({ tariffId: t.id, vehicleId })}
            />
          ))}
        </div>
      )}

      {!tariffs?.length && !adding && (
        <p className="text-sm text-gray-500">
          No tariffs configured. Add one to enable cost estimates and smart charging.
        </p>
      )}

      {adding && (
        <div className="border border-gray-700 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-gray-300">New Tariff</p>

          {formError && <ErrorBox message={formError} />}

          <input
            type="text"
            placeholder="Name (e.g. Home TOU)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
          />

          <div className="flex gap-2">
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="flex-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
            >
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
              <option value="GBP">GBP</option>
              <option value="CAD">CAD</option>
              <option value="AUD">AUD</option>
            </select>
            <input
              type="text"
              placeholder="Timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="flex-1 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-sm px-3 py-2"
            />
          </div>

          <div>
            <p className="text-xs text-gray-500 mb-1">Preset</p>
            <div className="flex gap-1 flex-wrap">
              {Object.entries(PRESET_CONFIGS).map(([key, p]) => (
                <button
                  key={key}
                  onClick={() => handlePresetChange(key as keyof typeof PRESET_CONFIGS)}
                  className={`px-2 py-1 rounded text-xs transition-colors ${
                    preset === key
                      ? "bg-brand-500 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs text-gray-500 mb-1">Config JSON</p>
            <textarea
              value={rawConfig}
              onChange={(e) => { setRawConfig(e.target.value); setConfigError(null); }}
              rows={8}
              className="w-full rounded-lg bg-gray-800 border border-gray-700 text-gray-200 text-xs px-3 py-2 font-mono resize-y"
            />
            {configError && <p className="text-xs text-red-400 mt-1">{configError}</p>}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={createTariff.isPending}
              className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-500/90 disabled:opacity-50"
            >
              {createTariff.isPending ? "Saving…" : "Save Tariff"}
            </button>
            <button
              onClick={() => { setAdding(false); setFormError(null); }}
              className="rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-gray-400 hover:bg-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────────────

interface Vehicle { id: string; display_name: string | null; model: string | null; }

function TariffRow({
  tariff,
  vehicles,
  onDelete,
  onAssign,
}: {
  tariff: Tariff;
  vehicles: Vehicle[];
  onDelete: () => void;
  onAssign: (vehicleId: string) => void;
}) {
  const configType = (tariff.config as { type?: string }).type ?? "custom";
  return (
    <div className="flex items-center justify-between rounded-lg bg-gray-800 px-3 py-2.5">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-200 truncate">{tariff.name}</p>
        <p className="text-xs text-gray-500">
          {configType} · {tariff.currency} · {tariff.timezone}
        </p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
        {vehicles.length > 0 && (
          <select
            defaultValue=""
            onChange={(e) => { if (e.target.value) onAssign(e.target.value); e.target.value = ""; }}
            className="text-xs bg-gray-700 border border-gray-600 text-gray-300 rounded px-2 py-1"
          >
            <option value="" disabled>Assign…</option>
            {vehicles.map((v) => (
              <option key={v.id} value={v.id}>
                {v.display_name ?? v.model ?? "Vehicle"}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={onDelete}
          className="text-xs text-gray-500 hover:text-red-400 transition-colors px-1"
        >
          Delete
        </button>
      </div>
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
