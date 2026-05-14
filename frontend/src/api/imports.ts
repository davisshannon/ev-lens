import { api } from "./client";

export interface ImportBatch {
  id: string;
  source_type: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  dry_run: boolean;
  summary: {
    vehicles_found?: number;
    snapshots_imported?: number;
    sessions_imported?: number;
    skipped?: number;
    errors?: number;
  } | null;
  error: string | null;
}

export interface TeslamateImportRequest {
  db_url: string;
  vehicle_id?: string | null;
}

export const importsApi = {
  list: (limit = 5) =>
    api.get<ImportBatch[]>("/imports/", { params: { limit } }).then((r) => r.data),

  get: (batchId: string) =>
    api.get<ImportBatch>(`/imports/${batchId}`).then((r) => r.data),

  dryRun: (body: TeslamateImportRequest) =>
    api.post<ImportBatch>("/imports/teslamate/dry-run", body).then((r) => r.data),

  startImport: (body: TeslamateImportRequest) =>
    api.post<ImportBatch>("/imports/teslamate/import", body).then((r) => r.data),

  rollback: (batchId: string) =>
    api.post<ImportBatch>(`/imports/${batchId}/rollback`).then((r) => r.data),
};
