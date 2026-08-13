import { describe, expect, it } from "vitest";
import { countryForTimezone, parseE164, toE164 } from "@/lib/phone";

describe("phone helpers", () => {
  it("maps timezone to country calling code", () => {
    expect(countryForTimezone("Asia/Karachi")).toMatchObject({ iso: "PK", code: "92" });
    expect(countryForTimezone("America/New_York")).toMatchObject({ iso: "US", code: "1" });
    expect(countryForTimezone("Europe/London")).toMatchObject({ iso: "GB", code: "44" });
    expect(countryForTimezone("Asia/Dubai")).toMatchObject({ iso: "AE", code: "971" });
    expect(countryForTimezone("America/Toronto")).toMatchObject({ iso: "CA", code: "1" });
  });

  it("builds E.164 from dial code and national number", () => {
    expect(toE164("92", "03001234567")).toBe("+923001234567");
    expect(toE164("1", "5551234567")).toBe("+15551234567");
    expect(toE164("92", "")).toBe("");
  });

  it("parses E.164 using the timezone dial code", () => {
    expect(parseE164("+923001234567", "92")).toEqual({ dial: "92", national: "3001234567" });
    expect(parseE164("", "92")).toEqual({ dial: "92", national: "" });
  });
});
