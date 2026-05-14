import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { importsApi, type ImportBatch } from "../api/imports";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/40",
  completed: "bg-green-500/20 text-green-300 border border-green-500/40",
  failed: "bg-red-500/20 text-red-300 border border-red-500/40",
  dry_run: "bg-blue-500/20 text-blue-300 border border-blue-500/40",
  rolled_back: "bg-gray-500/20 text-gray-400 border border-gray-500/40",
  pending: "bg-gray-500/20 text-gray-400 border border-gray-500/40",
};

function StatusChip({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? STATUS_COLORS.pending;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {status}
    </span>
  );
}

function SummaryCard({ summary, title }: { summary: ImportBatch["summary"]; title: string }) {
  if (!summary) return null;
  return (
    <div className="mt-4 rounded-lg border border-gray-700 bg-gray-800 p-4">
      <h3 className="text-sm font-semibold text-gray-300 mb-3">{title}</h3>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {[
          { label: "Vehicles", value: summary.vehicles_found ?? 0 },
          { label: "Snapshots", value: summary.snapshots_imported ?? 0 },
          { label: "Sessions", value: summary.sessions_imported ?? 0 },
          { label: "Skipped", value: summary.skipped ?? 0 },
          { label: "Errors", value: summary.errors ?? 0 },
        ].map(({ label, value }) => (
          <div key={label} className="flex flex-col items-center rounded bg-gray-900 py-3 px-2">
            <span className="text-2xl font-bold text-gray-100">{value}</span>
            <span className="text-xs text-gray-400 mt-1">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BatchRow({
  batch,
  onRollback,
  isRollingBack,
}: {
  batch: ImportBatch;
  onRollback: (id: string) => void;
  isRollingBack: boolean;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 py-3 border-b border-gray-800 last:border-0">
      <div className="flex flex-col gap-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-200 font-mono truncate">{batch.id.slice(0, 8)}…</span>
          <StatusChip status={batch.status} />
          {batch.dry_run && (
            <span className="text-xs text-gray-500 italic">dry run</span>
          )}
        </div>
        <span className="text-xs text-gray-500">
          {new Date(batch.started_at).toLocaleString()}
          {batch.completed_at && (
            <> — {new Date(batch.completed_at).toLocaleString()}</>
          )}
        </span>
        {batch.error && (
          <span className="text-xs text-red-400 truncate">{batch.error}</span>
        )}
        {batch.summary && (
          <span className="text-xs text-gray-400">
            {batch.summary.snapshots_imported ?? 0} snapshots,{" "}
            {batch.summary.sessions_imported ?? 0} sessions
          </span>
        )}
      </div>
      <div className="flex-shrink-0">
        {batch.status === "completed" && !batch.dry_run && (
          <button
            onClick={() => onRollback(batch.id)}
            disabled={isRollingBack}
            className="px-3 py-1.5 rounded text-xs font-medium bg-red-900/40 text-red-300 border border-red-700/50 hover:bg-red-900/70 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isRollingBack ? "Rolling back…" : "Rollback"}
          </button>
        )}
      </div>
    </div>
  );
}

export function ImportsPage() {
  const queryClient = useQueryClient();

  // Form state
  const [dbUrl, setDbUrl] = useState("");
  const [dryRunResult, setDryRunResult] = useState<ImportBatch | null>(null);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  // Recent batches
  const { data: recentBatches, refetch: refetchBatches } = useQuery({
    queryKey: ["imports", "list"],
    queryFn: () => importsApi.list(5),
    refetchInterval: activeBatchId ? 3000 : false,
  });

  // Polling active batch
  const { data: activeBatch } = useQuery({
    queryKey: ["imports", "batch", activeBatchId],
    queryFn: () => importsApi.get(activeBatchId!),
    enabled: !!activeBatchId,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === "running" ? 3000 : false;
    },
  });

  // Stop polling when batch completes
  useEffect(() => {
    if (activeBatch && activeBatch.status !== "running") {
      queryClient.invalidateQueries({ queryKey: ["imports", "list"] });
    }
  }, [activeBatch, queryClient]);

  // Dry run mutation
  const dryRunMutation = useMutation({
    mutationFn: () => importsApi.dryRun({ db_url: dbUrl }),
    onSuccess: (batch) => {
      setDryRunResult(batch);
      setFormError(null);
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Dry run failed";
      setFormError(msg);
      setDryRunResult(null);
    },
  });

  // Import mutation
  const importMutation = useMutation({
    mutationFn: () => importsApi.startImport({ db_url: dbUrl }),
    onSuccess: (batch) => {
      setActiveBatchId(batch.id);
      setDryRunResult(null);
      setFormError(null);
      refetchBatches();
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Import failed to start";
      setFormError(msg);
    },
  });

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: (batchId: string) => importsApi.rollback(batchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["imports", "list"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Rollback failed";
      setFormError(msg);
    },
  });

  const canImport =
    dryRunResult !== null &&
    dryRunResult.status === "completed" &&
    ((dryRunResult.summary?.snapshots_imported ?? 0) > 0 ||
      (dryRunResult.summary?.sessions_imported ?? 0) > 0);

  const isRunning = activeBatch?.status === "running";
  const isBusy =
    dryRunMutation.isPending || importMutation.isPending || isRunning;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-100">Import Data</h1>
        <p className="text-sm text-gray-400 mt-1">
          Import your TeslaMate history into EV Lens.
        </p>
      </div>

      {/* Import form */}
      <div className="rounded-lg border border-gray-800 bg-gray-900 p-5 space-y-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">
          TeslaMate PostgreSQL
        </h2>

        <div>
          <label className="block text-xs text-gray-400 mb-1" htmlFor="db-url">
            Database URL
          </label>
          <input
            id="db-url"
            type="text"
            value={dbUrl}
            onChange={(e) => {
              setDbUrl(e.target.value);
              setDryRunResult(null);
              setFormError(null);
            }}
            placeholder="postgresql://teslamate:password@host:5432/teslamate"
            className="w-full rounded bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 font-mono"
            disabled={isBusy}
          />
        </div>

        {formError && (
          <div className="rounded bg-red-900/30 border border-red-700/50 px-3 py-2 text-sm text-red-300">
            {formError}
          </div>
        )}

        {dryRunResult && <SummaryCard summary={dryRunResult.summary} title="Dry Run Preview" />}

        {/* Progress indicator for running import */}
        {isRunning && (
          <div className="flex items-center gap-3 rounded bg-yellow-900/20 border border-yellow-700/40 px-3 py-2">
            <svg
              className="animate-spin h-4 w-4 text-yellow-400"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            <span className="text-sm text-yellow-300">Import running…</span>
          </div>
        )}

        {activeBatch && activeBatch.status === "completed" && (
          <SummaryCard summary={activeBatch.summary} title="Import Complete" />
        )}

        {activeBatch && activeBatch.status === "failed" && (
          <div className="rounded bg-red-900/30 border border-red-700/50 px-3 py-2 text-sm text-red-300">
            Import failed: {activeBatch.error}
          </div>
        )}

        <div className="flex gap-3 pt-1">
          <button
            onClick={() => dryRunMutation.mutate()}
            disabled={!dbUrl.trim() || isBusy}
            className="px-4 py-2 rounded text-sm font-medium bg-gray-700 text-gray-200 border border-gray-600 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {dryRunMutation.isPending ? "Checking…" : "Dry Run"}
          </button>
          <button
            onClick={() => importMutation.mutate()}
            disabled={!canImport || isBusy}
            className="px-4 py-2 rounded text-sm font-medium bg-brand-500 text-white hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {importMutation.isPending ? "Starting…" : "Import"}
          </button>
        </div>
      </div>

      {/* Recent batches */}
      {recentBatches && recentBatches.length > 0 && (
        <div className="rounded-lg border border-gray-800 bg-gray-900 p-5">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">
            Recent Imports
          </h2>
          <div>
            {recentBatches.map((batch) => (
              <BatchRow
                key={batch.id}
                batch={batch}
                onRollback={(id) => rollbackMutation.mutate(id)}
                isRollingBack={
                  rollbackMutation.isPending &&
                  rollbackMutation.variables === batch.id
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
