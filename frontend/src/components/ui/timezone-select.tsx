import { useMemo, useState } from "react";
import { groupTimezones, listTimezones, timezoneLabel } from "@/lib/timezones";
import { cn } from "@/lib/utils";

const selectClass =
  "flex h-10 w-full rounded-md border border-border bg-card px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 disabled:cursor-not-allowed disabled:opacity-50";

export function TimezoneSelect({
  id,
  value,
  onChange,
  disabled,
  className,
}: {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
}) {
  const [query, setQuery] = useState("");
  const zones = useMemo(() => listTimezones(), []);
  const selected = value || "UTC";
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    const matches = term
      ? zones.filter(
          (zone) =>
            timezoneLabel(zone).toLowerCase().includes(term) || zone.toLowerCase().includes(term),
        )
      : zones;
    if (selected && !matches.includes(selected)) return [selected, ...matches];
    return matches;
  }, [query, selected, zones]);
  const groups = useMemo(() => groupTimezones(filtered), [filtered]);

  return (
    <div className="space-y-2">
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search timezones"
        disabled={disabled}
        className={cn(selectClass, "h-9", className)}
        aria-label="Search timezones"
      />
      <select
        id={id}
        value={selected}
        disabled={disabled}
        className={cn(selectClass, className)}
        onChange={(e) => onChange(e.target.value)}
      >
        {groups.length === 0 ? (
          <option value={selected}>{timezoneLabel(selected)}</option>
        ) : (
          groups.map(([region, items]) => (
            <optgroup key={region} label={region}>
              {items.map((zone) => (
                <option key={zone} value={zone}>
                  {timezoneLabel(zone)}
                </option>
              ))}
            </optgroup>
          ))
        )}
      </select>
    </div>
  );
}
