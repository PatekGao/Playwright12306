import { describe, expect, it } from "vitest";

import { buildExportUrl, buildSearchQuery, parseSearchFilters } from "./searchFilters";

describe("searchFilters", () => {
  it("parses route query into filters", () => {
    const filters = parseSearchFilters({
      query_date: "2026-03-18",
      train_code: "G5",
      page: "2",
      sort_by: "min_price",
      sort_order: "desc",
    });

    expect(filters.query_date).toBe("2026-03-18");
    expect(filters.train_code).toBe("G5");
    expect(filters.page).toBe(2);
    expect(filters.sort_by).toBe("min_price");
    expect(filters.sort_order).toBe("desc");
  });

  it("builds compact route query without defaults", () => {
    const query = buildSearchQuery({
      query_date: "2026-03-18",
      train_code: "G5",
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
    });

    expect(query).toEqual({
      query_date: "2026-03-18",
      train_code: "G5",
    });
  });

  it("builds export url with current filters", () => {
    const url = buildExportUrl(
      "/api/trains/export",
      {
        query_date: "2026-03-18",
        train_code: "G5",
        start_station_name: "北京",
        end_station_name: "上海",
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
      },
      "csv",
    );

    expect(url).toContain("query_date=2026-03-18");
    expect(url).toContain("train_code=G5");
    expect(url).toContain("start_station_name=%E5%8C%97%E4%BA%AC");
    expect(url).toContain("format=csv");
  });
});
