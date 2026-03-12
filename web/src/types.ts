export type QueryDateOption = string;

export interface MetaSummary {
  query_dates: QueryDateOption[];
  total_trains: number;
  total_stops: number;
  latest_imported_at: string | null;
}

export interface MetaOptions {
  query_dates: QueryDateOption[];
  train_classes: string[];
  stations: string[];
  seat_names: string[];
}

export interface MatchedSeatPrice {
  seat_code: string;
  seat_name: string;
  price: number;
}

export interface TrainListItem {
  query_date: string;
  train_no: string;
  train_code: string;
  station_train_code: string;
  train_class_name: string;
  start_station_name: string;
  end_station_name: string;
  from_station_name: string;
  to_station_name: string;
  depart_time: string;
  arrive_time: string;
  duration: string;
  arrive_day_diff: number | string;
  from_station_code: string;
  to_station_code: string;
  seat_price_json: string;
  stop_count: number | string;
  route_signature: string;
  sale_status: string;
  can_web_buy: string;
  seat_inventory_json: string;
  matched_seat_prices?: MatchedSeatPrice[];
  min_price?: number | null;
}

export interface TrainListSummary {
  total_trains: number;
  matched_prices: number;
  min_price: number | null;
  max_price: number | null;
}

export interface TrainListResponse {
  items: TrainListItem[];
  total: number;
  page: number;
  page_size: number;
  summary: TrainListSummary;
}

export interface SeatPriceDetail {
  seat_code: string;
  seat_name: string;
  price: number;
  route_signature: string;
}

export interface TrainStop {
  query_date: string;
  train_no: string;
  station_train_code: string;
  station_no: string;
  station_name: string;
  arrive_time: string;
  start_time: string;
  running_time: string;
  arrive_day_diff: number | string;
  is_start: string;
  is_end: string;
}

export interface TrainDetailResponse {
  train: TrainListItem;
  stops: TrainStop[];
  seat_prices: SeatPriceDetail[];
  route_signature: string;
}

export type SortBy = "depart_time" | "arrive_time" | "duration" | "min_price" | "train_code";
export type SortOrder = "asc" | "desc";

export interface SearchFilters {
  query_date: string;
  train_code: string;
  start_station_name: string;
  end_station_name: string;
  train_class_name: string;
  seat_name: string;
  min_price: string;
  max_price: string;
  sale_status: string;
  depart_time_from: string;
  depart_time_to: string;
  page: number;
  page_size: number;
  sort_by: SortBy;
  sort_order: SortOrder;
}

export interface RealtimeMetaStations {
  stations: string[];
  cities: string[];
}

export interface RealtimeSeatOffer {
  seat_code: string;
  seat_name: string;
  price: number | null;
  inventory_text: string;
  is_available: boolean;
}

export interface RealtimeDailyItem {
  query_date: string;
  train_no: string;
  train_code: string;
  train_class_name: string;
  start_station_name: string;
  end_station_name: string;
  query_scope?: "station" | "city";
  from_station_name?: string;
  to_station_name?: string;
  matched_from_station_name?: string;
  matched_to_station_name?: string;
  matched_station_name?: string;
  matched_station_no?: string;
  matched_arrive_time?: string;
  matched_depart_time?: string;
  depart_time: string;
  arrive_time: string;
  duration: string;
  arrive_day_diff?: number | string;
  sale_status: string;
  can_web_buy: string;
  route_signature: string;
  matched_route_signature?: string;
  seat_offers: RealtimeSeatOffer[];
  min_price: number | null;
  stop_count?: number;
  detail_available?: boolean;
}

export interface RealtimeDailySummary {
  matched_train_count: number;
  available_train_count: number;
  cheapest_available_price: number | null;
  fastest_duration: string | null;
}

export interface RealtimeDailyResult {
  query_date: string;
  items: RealtimeDailyItem[];
  summary: RealtimeDailySummary;
  failure: string | null;
}

export interface RealtimeAggregatedResult {
  train_code: string;
  train_class_name: string;
  start_station_name: string;
  end_station_name: string;
  query_mode: "route" | "single_head";
  query_scope?: "station" | "city";
  route_signature: string;
  matched_route_signature?: string;
  matched_from_station_name?: string;
  matched_to_station_name?: string;
  matched_station_name: string;
  available_days: number;
  sold_out_days: number;
  first_seen_date: string;
  last_seen_date: string;
  min_price: number | null;
  max_price: number | null;
  sample_depart_time: string;
  sample_arrive_time: string;
  sample_duration: string;
}

export interface RealtimeSummary {
  total_days: number;
  successful_days: number;
  failed_days: number;
  available_train_count: number;
  cheapest_available_price: number | null;
  fastest_duration: string | null;
  matched_train_count: number;
}

export interface RealtimePartialFailure {
  query_date: string;
  stage: string;
  error_type: string;
  message: string;
}

export interface RealtimeQueryRequest {
  date?: string;
  date_from?: string;
  date_to?: string;
  from_station_name?: string;
  to_station_name?: string;
  train_code?: string;
  train_class_name?: string;
  query_mode?: "route" | "single_head";
  query_scope?: "station" | "city";
}

export interface RealtimeQueryResult {
  request: {
    date_from: string;
    date_to: string;
    query_mode: "route" | "single_head";
    query_scope: "station" | "city";
    from_station_name: string;
    to_station_name: string;
    train_code: string;
    train_class_name: string;
  };
  daily_results: RealtimeDailyResult[];
  aggregated_results: RealtimeAggregatedResult[];
  partial_failures: RealtimePartialFailure[];
  summary: RealtimeSummary;
}

export interface RealtimeJobResponse {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  updated_at: string;
  request: RealtimeQueryResult["request"];
  result: RealtimeQueryResult | null;
  error: string | null;
}

export interface RealtimeJobCreatedResponse {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  request: RealtimeQueryResult["request"];
}

export interface RealtimeJobEvent {
  event: string;
  timestamp: string;
  message?: string;
  query_date?: string;
  query_mode?: string;
  total_days?: number;
  matched_train_count?: number;
  train_code?: string;
  error_type?: string;
}

export interface RealtimeTrainDetail {
  train: {
    query_date: string;
    train_no: string;
    train_code: string;
    train_class_name: string;
    start_station_name: string;
    end_station_name: string;
    depart_time: string;
    arrive_time: string;
    duration: string;
    arrive_day_diff: string;
    from_station_name?: string;
    to_station_name?: string;
    sale_status?: string;
    can_web_buy?: string;
  };
  stops: TrainStop[];
  seat_offers: RealtimeSeatOffer[];
  route_signature: string;
}
