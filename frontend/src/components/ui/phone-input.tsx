import { useEffect, useRef, useState } from "react";
import { COUNTRY_DIALS, countryForTimezone, parseE164, toE164 } from "@/lib/phone";
import { cn } from "@/lib/utils";

const selectClass =
  "h-10 max-w-[9.5rem] shrink-0 rounded-md border border-border bg-card px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50";

export function PhoneInput({
  id,
  timezone,
  value,
  onChange,
  disabled,
  className,
}: {
  id?: string;
  timezone: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  const suggested = countryForTimezone(timezone || "UTC");
  const initial = parseE164(value, suggested.code);
  const [dial, setDial] = useState(initial.dial);
  const [iso, setIso] = useState(
    COUNTRY_DIALS.find((item) => item.iso === suggested.iso && item.code === initial.dial)?.iso ??
      COUNTRY_DIALS.find((item) => item.code === initial.dial)?.iso ??
      suggested.iso,
  );
  const [national, setNational] = useState(initial.national);
  const timezoneRef = useRef(timezone);
  const nationalRef = useRef(national);
  const lastEmitted = useRef(value);
  const onChangeRef = useRef(onChange);
  nationalRef.current = national;
  onChangeRef.current = onChange;

  useEffect(() => {
    if (value === lastEmitted.current) return;
    lastEmitted.current = value;
    const next = parseE164(value, countryForTimezone(timezoneRef.current || "UTC").code);
    const nextCountry = countryForTimezone(timezoneRef.current || "UTC");
    setDial(next.dial);
    setIso(
      next.dial === nextCountry.code
        ? nextCountry.iso
        : (COUNTRY_DIALS.find((item) => item.code === next.dial)?.iso ?? nextCountry.iso),
    );
    setNational(next.national);
  }, [value]);

  useEffect(() => {
    if (timezoneRef.current === timezone) return;
    timezoneRef.current = timezone;
    const nextCountry = countryForTimezone(timezone || "UTC");
    const e164 = toE164(nextCountry.code, nationalRef.current);
    setDial(nextCountry.code);
    setIso(nextCountry.iso);
    lastEmitted.current = e164;
    onChangeRef.current(e164);
  }, [timezone]);

  const selected =
    COUNTRY_DIALS.find((item) => item.iso === iso && item.code === dial) ??
    COUNTRY_DIALS.find((item) => item.code === dial) ??
    suggested;

  function emit(nextIso: string, nextDial: string, nextNational: string) {
    setIso(nextIso);
    setDial(nextDial);
    setNational(nextNational);
    const e164 = toE164(nextDial, nextNational);
    lastEmitted.current = e164;
    onChange(e164);
  }

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex gap-2">
        <select
          aria-label="Country calling code"
          className={selectClass}
          disabled={disabled}
          value={`${selected.iso}:${selected.code}`}
          onChange={(e) => {
            const [iso, code] = e.target.value.split(":");
            const match = COUNTRY_DIALS.find((item) => item.iso === iso && item.code === code);
            emit(match?.iso ?? iso, match?.code ?? code, national);
          }}
        >
          {COUNTRY_DIALS.map((item) => (
            <option key={`${item.iso}:${item.code}`} value={`${item.iso}:${item.code}`}>
              +{item.code} {item.iso}
            </option>
          ))}
        </select>
        <input
          id={id}
          type="tel"
          inputMode="numeric"
          autoComplete="tel-national"
          disabled={disabled}
          value={national}
          placeholder="Phone number"
          onChange={(e) => emit(iso, dial, e.target.value)}
          className="flex h-10 w-full rounded-md border border-border bg-card px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>
      <p className="text-xs text-muted-foreground">
        +{selected.code} {selected.name}
        {value ? ` · saved as ${value}` : " · country code follows the timezone"}
      </p>
    </div>
  );
}
