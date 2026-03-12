import type {
  MetaOptions,
  MetaSummary,
  SearchFilters,
  TrainDetailResponse,
  TrainListResponse,
} from "@/types";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";
const REQUEST_TIMEOUT_MS = 15000;

function normalizeApiBaseUrl(apiBaseUrl?: string): string {
  const configuredBaseUrl = (apiBaseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "").replace(
    /\/$/,
    "",
  );
  if (configuredBaseUrl) {
    return configuredBaseUrl;
  }

  if (typeof window === "undefined") {
    return "";
  }

  const hostname = window.location.hostname;
  if (hostname === "127.0.0.1" || hostname === "localhost") {
    return "";
  }
  return DEFAULT_API_BASE_URL;
}

export function buildApiUrl(path: string, apiBaseUrl?: string): string {
  const baseUrl = normalizeApiBaseUrl(apiBaseUrl);
  return baseUrl ? `${baseUrl}${path}` : path;
}

async function getJson<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const response = await fetch(url, { signal: controller.signal }).finally(() => {
    window.clearTimeout(timeoutId);
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchMetaSummary(apiBaseUrl?: string): Promise<MetaSummary> {
  return getJson<MetaSummary>(buildApiUrl("/api/meta/summary", apiBaseUrl));
}

export function fetchMetaOptions(apiBaseUrl?: string): Promise<MetaOptions> {
  return getJson<MetaOptions>(buildApiUrl("/api/meta/options", apiBaseUrl));
}

export function fetchTrains(
  filters: SearchFilters,
  apiBaseUrl?: string,
): Promise<TrainListResponse> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value === "" || value === undefined || value === null) {
      return;
    }
    params.set(key, String(value));
  });
  return getJson<TrainListResponse>(buildApiUrl(`/api/trains?${params.toString()}`, apiBaseUrl));
}

export function fetchTrainDetail(
  queryDate: string,
  trainNo: string,
  apiBaseUrl?: string,
): Promise<TrainDetailResponse> {
  return getJson<TrainDetailResponse>(
    buildApiUrl(`/api/trains/${queryDate}/${trainNo}`, apiBaseUrl),
  );
}
