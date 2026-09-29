import { Link } from "react-router-dom";

import type { Summary } from "../api";
import { useApi } from "../api";
import CallTable from "../CallTable";
import { LANGUAGE, STATUS, occupationName, seconds } from "../labels";
import { Card, Empty, LiveBadge, Loading, Stat } from "../ui";

function Bars({ counts, labels }: { counts: Record<string, number>; labels: Record<string, string> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, n]) => s + n, 0);
  if (!total) return <Empty>No data yet.</Empty>;
  return (
    <ul className="space-y-2">
      {entries.map(([k, n]) => (
        <li key={k}>
          <div className="flex justify-between text-sm">
            <span>{labels[k] ?? k}</span>
            <span className="tabular-nums text-slate-500">{n}</span>
          </div>
          <div className="mt-1 h-2 rounded-full bg-slate-100 dark:bg-slate-800">
            <div className="h-2 rounded-full bg-brand-500" style={{ width: `${(100 * n) / total}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function Overview() {
  const { data, error } = useApi<Summary>("/summary", 3000);
  if (!data) return <Loading error={error} />;
  return (
    <div className="space-y-6">
      {data.live_now.map((c) => (
        <Link
          key={c.id}
          to={`/calls/${c.id}`}
          className="flex flex-wrap items-center gap-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm shadow-sm hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950/50 dark:hover:bg-rose-950"
        >
          <LiveBadge />
          <span className="font-medium">A call is happening now</span>
          <span className="font-mono text-slate-600 dark:text-slate-300">{c.number ?? "—"}</span>
          <span className="text-slate-500">{LANGUAGE[c.language ?? ""] ?? "choosing language"}</span>
          <span className="ml-auto font-medium text-rose-700 dark:text-rose-300">Watch live →</span>
        </Link>
      ))}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
        <Stat label="Calls" value={data.calls} />
        <Stat label="Today" value={data.today} />
        <Stat label="People" value={data.people} />
        <Stat label="Completed" value={data.completed} />
        <Stat label="Avg length" value={seconds(data.avg_duration)} />
        <Stat label="Occupation found" value={data.with_occupation} />
        <Stat label="Want a human" value={data.human_flags} />
      </div>
      <div className="grid gap-6 md:grid-cols-3">
        <Card title="Languages">
          <Bars counts={data.languages} labels={LANGUAGE} />
        </Card>
        <Card title="Call status">
          <Bars counts={data.statuses} labels={STATUS} />
        </Card>
        <Card title="Most common occupations">
          {data.occupations.length ? (
            <ol className="space-y-1 text-sm">
              {data.occupations.map((o) => (
                <li key={o.code} className="flex justify-between gap-2">
                  <span>{occupationName(o)}</span>
                  <span className="tabular-nums text-slate-500">{o.count}</span>
                </li>
              ))}
            </ol>
          ) : (
            <Empty>No occupations confirmed yet.</Empty>
          )}
        </Card>
      </div>
      <Card
        title="Latest calls"
        right={
          <Link to="/calls" className="text-sm font-medium text-brand-600 hover:underline dark:text-blue-400">
            All calls →
          </Link>
        }
      >
        <CallTable calls={data.recent} />
      </Card>
    </div>
  );
}
