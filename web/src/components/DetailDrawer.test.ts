import { render, screen } from "@testing-library/vue";
import { describe, expect, it } from "vitest";

import DetailDrawer from "./DetailDrawer.vue";

describe("DetailDrawer", () => {
  it("shows stop list and seat prices", () => {
    render(DetailDrawer, {
      props: {
        open: true,
        loading: false,
        detail: {
          route_signature: "HGH->AOH",
          train: {
            query_date: "2026-03-18",
            train_no: "24000000G50A",
            train_code: "G5",
            station_train_code: "G5",
            train_class_name: "高速",
            start_station_name: "杭州东",
            end_station_name: "上海虹桥",
            from_station_name: "杭州东",
            to_station_name: "上海虹桥",
            depart_time: "08:00",
            arrive_time: "09:15",
            duration: "01:15",
            arrive_day_diff: 0,
            from_station_code: "HGH",
            to_station_code: "AOH",
            seat_price_json: "[]",
            stop_count: 2,
            route_signature: "HGH->AOH",
            sale_status: "预订",
            can_web_buy: "Y",
            seat_inventory_json: "",
          },
          seat_prices: [
            {
              seat_code: "O",
              seat_name: "二等座",
              price: 73.5,
              route_signature: "HGH->AOH",
            },
          ],
          stops: [
            {
              query_date: "2026-03-18",
              train_no: "24000000G50A",
              station_train_code: "G5",
              station_no: "01",
              station_name: "杭州东",
              arrive_time: "----",
              start_time: "08:00",
              running_time: "00:00",
              arrive_day_diff: 0,
              is_start: "Y",
              is_end: "",
            },
            {
              query_date: "2026-03-18",
              train_no: "24000000G50A",
              station_train_code: "G5",
              station_no: "02",
              station_name: "上海虹桥",
              arrive_time: "09:15",
              start_time: "09:15",
              running_time: "01:15",
              arrive_day_diff: 0,
              is_start: "",
              is_end: "Y",
            },
          ],
        },
      },
    });

    expect(screen.getByText("G5")).toBeTruthy();
    expect(screen.getByText("二等座")).toBeTruthy();
    expect(screen.getByText("¥73.5")).toBeTruthy();
    expect(screen.getByText("上海虹桥")).toBeTruthy();
  });
});
