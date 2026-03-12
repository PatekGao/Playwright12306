import { describe, expect, it, vi } from "vitest";

import { buildApiUrl, fetchMetaSummary } from "./api";

describe("api", () => {
  it("builds absolute urls when VITE_API_BASE_URL is provided", () => {
    expect(buildApiUrl("/api/meta/summary", "https://example.com/")).toBe(
      "https://example.com/api/meta/summary",
    );
  });

  it("uses same-origin api paths by default", () => {
    vi.stubGlobal("window", {
      location: {
        hostname: "preview.example.com",
      },
      setTimeout,
      clearTimeout,
    });

    expect(buildApiUrl("/api/meta/summary")).toBe("/api/meta/summary");
  });

  it("uses configured api base for fetch requests", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ query_dates: [], total_trains: 0, total_stops: 0, latest_imported_at: null }),
    });
    vi.stubGlobal("fetch", mockFetch);
    vi.stubGlobal("window", {
      location: {
        hostname: "preview.example.com",
      },
      setTimeout,
      clearTimeout,
    });

    await fetchMetaSummary("https://preview.example.com");

    expect(mockFetch).toHaveBeenCalledWith("https://preview.example.com/api/meta/summary", {
      signal: expect.any(AbortSignal),
    });
  });
});
