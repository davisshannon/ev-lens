import { api } from "./client";

export interface AppSettingOut {
  key: string;
  value: string;       // "••••••" if secret+set, "" if secret+unset, plaintext otherwise
  is_secret: boolean;
  is_set: boolean;
  label: string;
  updated_at: string | null;
}

export const appSettingsApi = {
  list: () => api.get<AppSettingOut[]>("/app-settings").then((r) => r.data),
  set: (key: string, value: string) =>
    api.put<AppSettingOut>(`/app-settings/${key}`, { value }).then((r) => r.data),
  clear: (key: string) => api.delete(`/app-settings/${key}`),
};
