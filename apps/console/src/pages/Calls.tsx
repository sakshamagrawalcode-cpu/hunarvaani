import { useMemo, useState } from "react";

import type { CallRow } from "../api";
import { useApi } from "../api";
import CallTable from "../CallTable";
import { LANGUAGE, STATUS, occupationName, value, when } from "../labels";
import { Card, Loading } from "../ui";

function searchText(c: CallRow): string {
  return [
    when(c.when),
    c.number,
    c.short,
    STATUS[c.status ?? ""] ?? c.status,
    LANGUAGE[c.language ?? ""],
    ...Object.values(c.answers).map((v) => value(v)),
    occupationName(c.occupation),
    ...c.transcripts,
  ]
    .join(" ")
    .toLowerCase();
}

export default function Calls() {
  const { data, error, updated } = useApi<CallRow[]>("/calls", 5000);
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const words = q.toLowerCase().split(/\s+/).filter(Boolean);
    return (data ?? []).filter((c) => words.every((w) => searchText(c).includes(w)));
  }, [data, q]);
  if (!data) return <Loading error={error} />;
  return (
    <Card
      title={`Calls (${shown.length} of ${data.length})`}
      right={
        <div className="flex items-center gap-3">
          {updated && (
            <span className="hidden text-xs text-slate-500 sm:inline">
              updated {when(updated.toISOString())}
            </span>
          )}
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search number, occupation, words…"
            className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
          />
        </div>
      }
    >
      <CallTable calls={shown} />
    </Card>
  );
}
