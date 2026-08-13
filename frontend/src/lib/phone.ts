export interface CountryDial {
  iso: string;
  code: string;
  name: string;
}

export const COUNTRY_DIALS: CountryDial[] = [
  { iso: "AF", code: "93", name: "Afghanistan" },
  { iso: "AL", code: "355", name: "Albania" },
  { iso: "DZ", code: "213", name: "Algeria" },
  { iso: "AR", code: "54", name: "Argentina" },
  { iso: "AM", code: "374", name: "Armenia" },
  { iso: "AU", code: "61", name: "Australia" },
  { iso: "AT", code: "43", name: "Austria" },
  { iso: "AZ", code: "994", name: "Azerbaijan" },
  { iso: "BH", code: "973", name: "Bahrain" },
  { iso: "BD", code: "880", name: "Bangladesh" },
  { iso: "BY", code: "375", name: "Belarus" },
  { iso: "BE", code: "32", name: "Belgium" },
  { iso: "BO", code: "591", name: "Bolivia" },
  { iso: "BA", code: "387", name: "Bosnia" },
  { iso: "BR", code: "55", name: "Brazil" },
  { iso: "BG", code: "359", name: "Bulgaria" },
  { iso: "KH", code: "855", name: "Cambodia" },
  { iso: "CM", code: "237", name: "Cameroon" },
  { iso: "CA", code: "1", name: "Canada" },
  { iso: "CL", code: "56", name: "Chile" },
  { iso: "CN", code: "86", name: "China" },
  { iso: "CO", code: "57", name: "Colombia" },
  { iso: "CR", code: "506", name: "Costa Rica" },
  { iso: "HR", code: "385", name: "Croatia" },
  { iso: "CZ", code: "420", name: "Czechia" },
  { iso: "DK", code: "45", name: "Denmark" },
  { iso: "DO", code: "1", name: "Dominican Republic" },
  { iso: "EC", code: "593", name: "Ecuador" },
  { iso: "EG", code: "20", name: "Egypt" },
  { iso: "EE", code: "372", name: "Estonia" },
  { iso: "ET", code: "251", name: "Ethiopia" },
  { iso: "FJ", code: "679", name: "Fiji" },
  { iso: "FI", code: "358", name: "Finland" },
  { iso: "FR", code: "33", name: "France" },
  { iso: "GE", code: "995", name: "Georgia" },
  { iso: "DE", code: "49", name: "Germany" },
  { iso: "GH", code: "233", name: "Ghana" },
  { iso: "GR", code: "30", name: "Greece" },
  { iso: "GT", code: "502", name: "Guatemala" },
  { iso: "HK", code: "852", name: "Hong Kong" },
  { iso: "HU", code: "36", name: "Hungary" },
  { iso: "IS", code: "354", name: "Iceland" },
  { iso: "IN", code: "91", name: "India" },
  { iso: "ID", code: "62", name: "Indonesia" },
  { iso: "IR", code: "98", name: "Iran" },
  { iso: "IQ", code: "964", name: "Iraq" },
  { iso: "IE", code: "353", name: "Ireland" },
  { iso: "IL", code: "972", name: "Israel" },
  { iso: "IT", code: "39", name: "Italy" },
  { iso: "JM", code: "1", name: "Jamaica" },
  { iso: "JP", code: "81", name: "Japan" },
  { iso: "JO", code: "962", name: "Jordan" },
  { iso: "KZ", code: "7", name: "Kazakhstan" },
  { iso: "KE", code: "254", name: "Kenya" },
  { iso: "KW", code: "965", name: "Kuwait" },
  { iso: "LV", code: "371", name: "Latvia" },
  { iso: "LB", code: "961", name: "Lebanon" },
  { iso: "LY", code: "218", name: "Libya" },
  { iso: "LT", code: "370", name: "Lithuania" },
  { iso: "LU", code: "352", name: "Luxembourg" },
  { iso: "MO", code: "853", name: "Macau" },
  { iso: "MY", code: "60", name: "Malaysia" },
  { iso: "MX", code: "52", name: "Mexico" },
  { iso: "MA", code: "212", name: "Morocco" },
  { iso: "NP", code: "977", name: "Nepal" },
  { iso: "NL", code: "31", name: "Netherlands" },
  { iso: "NZ", code: "64", name: "New Zealand" },
  { iso: "NG", code: "234", name: "Nigeria" },
  { iso: "NO", code: "47", name: "Norway" },
  { iso: "OM", code: "968", name: "Oman" },
  { iso: "PK", code: "92", name: "Pakistan" },
  { iso: "PA", code: "507", name: "Panama" },
  { iso: "PE", code: "51", name: "Peru" },
  { iso: "PH", code: "63", name: "Philippines" },
  { iso: "PL", code: "48", name: "Poland" },
  { iso: "PT", code: "351", name: "Portugal" },
  { iso: "PR", code: "1", name: "Puerto Rico" },
  { iso: "QA", code: "974", name: "Qatar" },
  { iso: "RO", code: "40", name: "Romania" },
  { iso: "RU", code: "7", name: "Russia" },
  { iso: "SA", code: "966", name: "Saudi Arabia" },
  { iso: "RS", code: "381", name: "Serbia" },
  { iso: "SG", code: "65", name: "Singapore" },
  { iso: "SK", code: "421", name: "Slovakia" },
  { iso: "SI", code: "386", name: "Slovenia" },
  { iso: "ZA", code: "27", name: "South Africa" },
  { iso: "KR", code: "82", name: "South Korea" },
  { iso: "ES", code: "34", name: "Spain" },
  { iso: "LK", code: "94", name: "Sri Lanka" },
  { iso: "SE", code: "46", name: "Sweden" },
  { iso: "CH", code: "41", name: "Switzerland" },
  { iso: "TW", code: "886", name: "Taiwan" },
  { iso: "TZ", code: "255", name: "Tanzania" },
  { iso: "TH", code: "66", name: "Thailand" },
  { iso: "TN", code: "216", name: "Tunisia" },
  { iso: "TR", code: "90", name: "Turkey" },
  { iso: "UA", code: "380", name: "Ukraine" },
  { iso: "AE", code: "971", name: "United Arab Emirates" },
  { iso: "GB", code: "44", name: "United Kingdom" },
  { iso: "US", code: "1", name: "United States" },
  { iso: "UY", code: "598", name: "Uruguay" },
  { iso: "UZ", code: "998", name: "Uzbekistan" },
  { iso: "VE", code: "58", name: "Venezuela" },
  { iso: "VN", code: "84", name: "Vietnam" },
];

const DIAL_BY_ISO = new Map(COUNTRY_DIALS.map((item) => [item.iso, item]));
const DIAL_CODES_LONGEST = Array.from(new Set(COUNTRY_DIALS.map((item) => item.code))).sort(
  (a, b) => b.length - a.length,
);

const TZ_ISO: Record<string, string> = {
  UTC: "US",
  "Africa/Cairo": "EG",
  "Africa/Casablanca": "MA",
  "Africa/Johannesburg": "ZA",
  "Africa/Lagos": "NG",
  "Africa/Nairobi": "KE",
  "Africa/Tunis": "TN",
  "Africa/Accra": "GH",
  "Africa/Addis_Ababa": "ET",
  "Africa/Algiers": "DZ",
  "Africa/Tripoli": "LY",
  "America/Argentina/Buenos_Aires": "AR",
  "America/Argentina/Cordoba": "AR",
  "America/Bogota": "CO",
  "America/Caracas": "VE",
  "America/Chicago": "US",
  "America/Denver": "US",
  "America/Detroit": "US",
  "America/Edmonton": "CA",
  "America/Halifax": "CA",
  "America/Indiana/Indianapolis": "US",
  "America/Jamaica": "JM",
  "America/Lima": "PE",
  "America/Los_Angeles": "US",
  "America/Mexico_City": "MX",
  "America/Monterrey": "MX",
  "America/Montevideo": "UY",
  "America/New_York": "US",
  "America/Panama": "PA",
  "America/Phoenix": "US",
  "America/Puerto_Rico": "PR",
  "America/Santiago": "CL",
  "America/Sao_Paulo": "BR",
  "America/St_Johns": "CA",
  "America/Toronto": "CA",
  "America/Vancouver": "CA",
  "America/Winnipeg": "CA",
  "America/Anchorage": "US",
  "America/Adak": "US",
  "America/Boise": "US",
  "America/Guatemala": "GT",
  "America/Costa_Rica": "CR",
  "America/Guayaquil": "EC",
  "America/La_Paz": "BO",
  "America/Santo_Domingo": "DO",
  "Asia/Almaty": "KZ",
  "Asia/Amman": "JO",
  "Asia/Baghdad": "IQ",
  "Asia/Baku": "AZ",
  "Asia/Bangkok": "TH",
  "Asia/Beirut": "LB",
  "Asia/Colombo": "LK",
  "Asia/Dhaka": "BD",
  "Asia/Dubai": "AE",
  "Asia/Hong_Kong": "HK",
  "Asia/Ho_Chi_Minh": "VN",
  "Asia/Jakarta": "ID",
  "Asia/Jerusalem": "IL",
  "Asia/Kabul": "AF",
  "Asia/Karachi": "PK",
  "Asia/Kathmandu": "NP",
  "Asia/Kolkata": "IN",
  "Asia/Calcutta": "IN",
  "Asia/Kuala_Lumpur": "MY",
  "Asia/Kuwait": "KW",
  "Asia/Macau": "MO",
  "Asia/Manila": "PH",
  "Asia/Muscat": "OM",
  "Asia/Qatar": "QA",
  "Asia/Riyadh": "SA",
  "Asia/Seoul": "KR",
  "Asia/Shanghai": "CN",
  "Asia/Singapore": "SG",
  "Asia/Taipei": "TW",
  "Asia/Tashkent": "UZ",
  "Asia/Tbilisi": "GE",
  "Asia/Tehran": "IR",
  "Asia/Tokyo": "JP",
  "Asia/Yerevan": "AM",
  "Atlantic/Reykjavik": "IS",
  "Australia/Adelaide": "AU",
  "Australia/Brisbane": "AU",
  "Australia/Darwin": "AU",
  "Australia/Hobart": "AU",
  "Australia/Melbourne": "AU",
  "Australia/Perth": "AU",
  "Australia/Sydney": "AU",
  "Europe/Amsterdam": "NL",
  "Europe/Athens": "GR",
  "Europe/Belgrade": "RS",
  "Europe/Berlin": "DE",
  "Europe/Brussels": "BE",
  "Europe/Bucharest": "RO",
  "Europe/Budapest": "HU",
  "Europe/Copenhagen": "DK",
  "Europe/Dublin": "IE",
  "Europe/Helsinki": "FI",
  "Europe/Istanbul": "TR",
  "Europe/Kiev": "UA",
  "Europe/Kyiv": "UA",
  "Europe/Lisbon": "PT",
  "Europe/London": "GB",
  "Europe/Madrid": "ES",
  "Europe/Moscow": "RU",
  "Europe/Oslo": "NO",
  "Europe/Paris": "FR",
  "Europe/Prague": "CZ",
  "Europe/Rome": "IT",
  "Europe/Sofia": "BG",
  "Europe/Stockholm": "SE",
  "Europe/Vienna": "AT",
  "Europe/Warsaw": "PL",
  "Europe/Zurich": "CH",
  "Europe/Riga": "LV",
  "Europe/Tallinn": "EE",
  "Europe/Vilnius": "LT",
  "Europe/Luxembourg": "LU",
  "Pacific/Auckland": "NZ",
  "Pacific/Honolulu": "US",
  "Pacific/Fiji": "FJ",
};

const PREFIX_ISO: Array<[string, string]> = [
  ["America/Argentina/", "AR"],
  ["America/Indiana/", "US"],
  ["America/Kentucky/", "US"],
  ["America/North_Dakota/", "US"],
  ["Australia/", "AU"],
];

export function countryForTimezone(timeZone: string): CountryDial {
  const iso = isoFromTimezone(timeZone);
  return DIAL_BY_ISO.get(iso) ?? DIAL_BY_ISO.get("US")!;
}

function isoFromTimezone(timeZone: string): string {
  if (TZ_ISO[timeZone]) return TZ_ISO[timeZone];
  const prefix = PREFIX_ISO.find(([start]) => timeZone.startsWith(start));
  if (prefix) return prefix[1];
  if (timeZone.startsWith("US/") || timeZone.startsWith("America/")) {
    if (timeZone.includes("Mexico")) return "MX";
    if (
      timeZone.includes("Toronto") ||
      timeZone.includes("Vancouver") ||
      timeZone.includes("Edmonton") ||
      timeZone.includes("Winnipeg") ||
      timeZone.includes("Halifax") ||
      timeZone.includes("Montreal")
    ) {
      return "CA";
    }
  }
  return "US";
}

export function toE164(dialCode: string, nationalNumber: string): string {
  const digits = nationalNumber.replace(/\D/g, "").replace(/^0+/, "");
  if (!digits) return "";
  return `+${dialCode}${digits}`;
}

export function parseE164(
  value: string | undefined,
  fallbackDial: string,
): { dial: string; national: string } {
  const raw = (value ?? "").trim();
  if (!raw) return { dial: fallbackDial, national: "" };
  const digits = (raw.startsWith("+") ? raw.slice(1) : raw).replace(/\D/g, "");
  if (!digits) return { dial: fallbackDial, national: "" };
  if (digits.startsWith(fallbackDial) && digits.length > fallbackDial.length) {
    return { dial: fallbackDial, national: digits.slice(fallbackDial.length) };
  }
  const match = DIAL_CODES_LONGEST.find((code) => digits.startsWith(code));
  if (match && digits.length > match.length) {
    return { dial: match, national: digits.slice(match.length) };
  }
  return { dial: fallbackDial, national: digits };
}

export const E164_RE = /^\+[1-9]\d{1,14}$/;
