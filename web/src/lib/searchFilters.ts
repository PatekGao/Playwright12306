import type { LocationQuery, LocationQueryRaw } from "vue-router";

import type { SearchFilters, SortBy, SortOrder } from "@/types";

export const DEFAULT_FILTERS: SearchFilters = {
  query_date: "",
  train_code: "",
  start_station_name: "",
  end_station_name: "",
  train_class_name: "",
  seat_name: "",
  min_price: "",
  max_price: "",
  sale_status: "",
  depart_time_from: "",
  depart_time_to: "",
  page: 1,
  page_size: 20,
  sort_by: "depart_time",
  sort_order: "asc",
};

const SORT_BY_VALUES = new Set<SortBy>([
  "depart_time",
  "arrive_time",
  "duration",
  "min_price",
  "train_code",
]);

const SORT_ORDER_VALUES = new Set<SortOrder>(["asc", "desc"]);

function firstValue(value: LocationQuery[string]): string {
  if (Array.isArray(value)) {
    return value[0] ?? "";
  }
  return value ?? "";
}

function parsePositiveInt(value: string, fallback: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function parseSearchFilters(query: LocationQuery): SearchFilters {
  const sortBy = firstValue(query.sort_by) as SortBy;
  const sortOrder = firstValue(query.sort_order) as SortOrder;

  return {
    query_date: firstValue(query.query_date),
    train_code: firstValue(query.train_code),
    start_station_name: firstValue(query.start_station_name),
    end_station_name: firstValue(query.end_station_name),
    train_class_name: firstValue(query.train_class_name),
    seat_name: firstValue(query.seat_name),
    min_price: firstValue(query.min_price),
    max_price: firstValue(query.max_price),
    sale_status: firstValue(query.sale_status),
    depart_time_from: firstValue(query.depart_time_from),
    depart_time_to: firstValue(query.depart_time_to),
    page: parsePositiveInt(firstValue(query.page), DEFAULT_FILTERS.page),
    page_size: parsePositiveInt(firstValue(query.page_size), DEFAULT_FILTERS.page_size),
    sort_by: SORT_BY_VALUES.has(sortBy) ? sortBy : DEFAULT_FILTERS.sort_by,
    sort_order: SORT_ORDER_VALUES.has(sortOrder) ? sortOrder : DEFAULT_FILTERS.sort_order,
  };
}

export function buildSearchQuery(filters: SearchFilters): LocationQueryRaw {
  const query: LocationQueryRaw = {};
  for (const [key, rawValue] of Object.entries(filters)) {
    if (rawValue === "" || rawValue === DEFAULT_FILTERS[key as keyof SearchFilters]) {
      continue;
    }
    query[key] = String(rawValue);
  }
  if (filters.query_date) {
    query.query_date = filters.query_date;
  }
  return query;
}

export function mergeFilters(
  current: SearchFilters,
  patch: Partial<SearchFilters>,
): SearchFilters {
  const next = { ...current, ...patch };
  if (patch.page === undefined && Object.keys(patch).some((key) => key !== "page" && key !== "page_size")) {
    next.page = 1;
  }
  return next;
}

export function buildExportUrl(baseUrl: string, filters: SearchFilters, format: "csv" | "json"): string {
  const params = new URLSearchParams();
  Object.entries(buildSearchQuery(filters)).forEach(([key, value]) => {
    if (value !== undefined) {
      params.set(key, String(value));
    }
  });
  params.set("format", format);
  return `${baseUrl}?${params.toString()}`;
}
