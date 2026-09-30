import { useMemo, useState } from "react";

import type { CallRow } from "../api";
import { API, useApi } from "../api";
import CallTable from "../CallTable";
import { LANGUAGE, STATUS, occupationName, optionText, value, when } from "../labels";
import { Card, DistrictFilter, Loading, byDistrict } from "../ui";

function searchText(c: CallRow): string {
  return [
    when(c.when),
    c.number,
    c.short,
    c.ref,
    STATUS[c.status ?? ""] ?? c.status,
    LANGUAGE[c.language ?? ""],
    ...Object.values(c.answers).map((v) => value(v)),
    occupationName(c.occupation),
    optionText(c.option),
    ...c.transcripts,
  ]
    .join(" ")
    .toLowerCase();
}

export default function Calls() {
  const { data, error, updated } = useApi<CallRow[]>("/calls", 5000);
  const [q, setQ] = useState("");
  const [district, setDistrict] = useState("");
  const shown = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return (data ?? [])
      .filter(byDistrict(district))
      .filter((c) => words.every((w) => searchText(c).includes(w)));
  }, [data, q, district]);
  if (!data) return <Loading error={error} />;
  return (
    <Card
      title={`Calls (${shown.length} of ${data.length})`}
      right={
        <div className="flex flex-wrap items-center justify-end gap-3">
          {updated && (
            <span className="hidden text-xs text-slate-500 sm:inline">
              updated {when(updated.toISOString())}
            </span>
          )}
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search reference no., number, occupation…"
            className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
          <DistrictFilter rows={data} value={district} onChange={setDistrict} />
          <a
            href={`${API}/calls.csv`}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Download CSV
          </a>
        </div>
      }
    >
      <CallTable calls={shown} />
    </Card>
  );
}
