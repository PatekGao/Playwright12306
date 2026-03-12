import { render, screen } from "@testing-library/vue";
import { describe, expect, it } from "vitest";

import ResultsTable from "./ResultsTable.vue";

describe("ResultsTable", () => {
  it("renders result rows with key columns", () => {
    render(ResultsTable, {
      props: {
        items: [
          {
            query_date: "2026-03-18",
            train_no: "24000000G50A",
            train_code: "G5",
            station_train_code: "G5",
            train_class_name: "高速",
            start_station_name: "北京南",
            end_station_name: "上海虹桥",
            from_station_name: "北京南",
            to_station_name: "上海虹桥",
            depart_time: "07:00",
            arrive_time: "11:38",
            duration: "04:38",
            arrive_day_diff: 0,
            from_station_code: "VNP",
            to_station_code: "AOH",
            seat_price_json: "[]",
            stop_count: 2,
            route_signature: "VNP->AOH",
            sale_status: "预订",
            can_web_buy: "Y",
            seat_inventory_json: "",
            min_price: 553,
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
        sortBy: "depart_time",
        sortOrder: "asc",
      },
    });

    expect(screen.getByText("G5")).toBeTruthy();
    expect(screen.getByText("北京南")).toBeTruthy();
    expect(screen.getByText("上海虹桥")).toBeTruthy();
    expect(screen.getByText("¥553.0")).toBeTruthy();
  });

  it("renders empty state when there are no results", () => {
    render(ResultsTable, {
      props: {
        items: [],
        total: 0,
        page: 1,
        pageSize: 20,
        sortBy: "depart_time",
        sortOrder: "asc",
      },
    });

    expect(screen.getByText("当前筛选条件下没有结果")).toBeTruthy();
  });
});
