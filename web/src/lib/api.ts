import type {
  MetaOptions,
  MetaSummary,
  RealtimeJobCreatedResponse,
  RealtimeJobResponse,
  RealtimeMetaStations,
  RealtimeQueryRequest,
  RealtimeTrainDetail,
  SearchFilters,
  TrainDetailResponse,
  TrainListResponse,
} from "@/types";

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
  return "";
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

async function postJson<T>(url: string, payload: object): Promise<T> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    signal: controller.signal,
  }).finally(() => {
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

export function fetchRealtimeStations(apiBaseUrl?: string): Promise<RealtimeMetaStations> {
  return getJson<RealtimeMetaStations>(buildApiUrl("/api/realtime/meta/stations", apiBaseUrl));
}

export function createRealtimeJob(
  payload: RealtimeQueryRequest,
  apiBaseUrl?: string,
): Promise<RealtimeJobCreatedResponse> {
  return postJson<RealtimeJobCreatedResponse>(buildApiUrl("/api/realtime/jobs", apiBaseUrl), payload);
}

export function fetchRealtimeJob(jobId: string, apiBaseUrl?: string): Promise<RealtimeJobResponse> {
  return getJson<RealtimeJobResponse>(buildApiUrl(`/api/realtime/jobs/${jobId}`, apiBaseUrl));
}

export function fetchRealtimeTrainDetail(
  queryDate: string,
  trainNo: string,
  fromStationName?: string,
  toStationName?: string,
  apiBaseUrl?: string,
): Promise<RealtimeTrainDetail> {
  const params = new URLSearchParams();
  if (fromStationName) {
    params.set("from_station_name", fromStationName);
  }
  if (toStationName) {
    params.set("to_station_name", toStationName);
  }
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return getJson<RealtimeTrainDetail>(
    buildApiUrl(`/api/realtime/trains/${queryDate}/${trainNo}${suffix}`, apiBaseUrl),
  );
}

export function buildRealtimeEventsUrl(jobId: string, apiBaseUrl?: string): string {
  return buildApiUrl(`/api/realtime/jobs/${jobId}/events`, apiBaseUrl);
}

export function buildRealtimeExportUrl(
  jobId: string,
  format: "csv" | "json",
  apiBaseUrl?: string,
): string {
  const url = new URL(buildApiUrl(`/api/realtime/jobs/${jobId}/export`, apiBaseUrl), window.location.origin);
  url.searchParams.set("format", format);
  if (!normalizeApiBaseUrl(apiBaseUrl)) {
    return `${url.pathname}${url.search}`;
  }
  return url.toString();
}
