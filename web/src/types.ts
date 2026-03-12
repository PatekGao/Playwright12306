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
