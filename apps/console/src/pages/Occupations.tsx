import { useMemo, useState } from "react";

import type { OccupationRow } from "../api";
import { useApi } from "../api";
import { Card, Empty, Loading, td, th } from "../ui";

export default function Occupations() {
  const { data, error } = useApi<OccupationRow[]>("/occupations");
  const [q, setQ] = useState("");
  const shown = useMemo(() => {
    const w = q.trim().toLowerCase();
    return (data ?? []).filter(
      (o) =>
        !w || [o.code, o.title_en, o.title_hi, o.title_mr, ...o.aliases].join(" ").toLowerCase().includes(w),
    );
  }, [data, q]);
  if (!data) return <Loading error={error} />;
  return (
    <Card
      title={`Occupations the call can recognise (${shown.length} of ${data.length})`}
      right={
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search any word…"
          className="w-56 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
        />
      }
    >
      <p className="mb-3 text-sm text-slate-500">
        NCO code and names in English, Hindi and Marathi. The words underneath are what callers may say
        (Hindi, Marathi, English and romanised); matching also uses meaning, not only these words.
      </p>
      {shown.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead>
              <tr>
                <th className={th}>NCO</th>
                <th className={th}>Occupation</th>
                <th className={th}>Callers</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {shown.map((o) => (
                <tr key={o.code}>
                  <td className={`${td} font-mono`}>{o.code}</td>
                  <td className={td}>
                    <div className="font-medium">
                      {o.title_en} · {o.title_hi} · {o.title_mr}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {o.aliases.map((a) => (
                        <span
                          key={a}
                          className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300"
                        >
                          {a}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className={`${td} tabular-nums`}>{o.callers}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty>No occupation matches “{q}”.</Empty>
      )}
    </Card>
  );
}
