import { describe, expect, it } from "vitest";
import { errorMessage } from "./api";
import { flagLabel, num, pct } from "./labels";

describe("labels", () => {
  it("formats Turkish percentages and decimals", () => {
    expect(pct(0.756, 1)).toBe("%75,6");
    expect(num(0.123)).toBe("0,12");
    expect(pct(null)).toBe("—");
  });
  it("labels distractor flags", () => {
    expect(flagLabel("celdirici_B_ust_grubu_cekiyor")).toContain("B çeldiricisi");
    expect(flagLabel("cok_zor")).toContain("Çok zor");
  });
});

describe("errorMessage", () => {
  it("handles FastAPI validation arrays and publish blockers", () => {
    expect(errorMessage([{ msg: "a" }, { msg: "b" }])).toBe("a · b");
    expect(errorMessage({ message: "Sınav yayımlanamaz.", blockers: ["1. soru eksik."] })).toBe("Sınav yayımlanamaz. 1. soru eksik.");
  });
});
