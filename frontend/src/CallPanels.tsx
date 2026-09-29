import { useEffect, useRef, useState } from "react";

import { when } from "./labels";
import type { Row, Streams } from "./liveLog";

type PanelKey = keyof Streams;

const PANELS: { key: PanelKey; title: string; hint: string; empty: string }[] = [
  {
    key: "conversation",
    title: "Conversation",
    hint: "what the system said, what the caller said and pressed",
    empty: "Nothing said yet.",
  },
  {
    key: "processing",
    title: "Processing",
    hint: "what the system did in the background",
    empty: "No processing yet.",
  },
  {
    key: "problems",
    title: "Errors & warnings",
    hint: "timeouts, skipped answers, failures",
    empty: "✓ No problems in this call.",
  },
];

const TONE: Record<NonNullable<Row["tone"]>, string> = {
  ok: "text-emerald-700 dark:text-emerald-400",
  warn: "text-amber-700 dark:text-amber-400",
  error: "text-rose-700 dark:text-rose-400",
  muted: "text-slate-400",
};

function offset(at: string, start: number): string {
  const s = Math.max(0, Math.round((Date.parse(at) - start) / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function Who({ who }: { who: Row["who"] }) {
  if (!who) return null;
  return who === "system" ? (
    <span className="rounded bg-brand-100 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-brand-700 dark:bg-blue-950 dark:text-blue-300">
      SYSTEM
    </span>
  ) : (
    <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold tracking-wide text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300">
      CALLER
    </span>
  );
}

function RowView({ r, start }: { r: Row; start: number }) {
  return (
    <li className="grid grid-cols-[3rem_1.5rem_1fr] gap-x-2 px-3 py-2.5">
      <span className="pt-0.5 text-xs tabular-nums text-slate-400" title={when(r.at)}>
        {offset(r.at, start)}
      </span>
      <span aria-hidden className="text-base leading-5">
        {r.icon}
      </span>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <Who who={r.who} />
          <span className={`text-sm font-medium ${r.tone ? TONE[r.tone] : ""}`}>{r.title}</span>
          {r.meta && <span className="text-xs text-slate-400">· {r.meta}</span>}
        </div>
        {r.text && (
          <p
            className={`mt-0.5 text-sm leading-relaxed ${r.tone === "muted" ? "text-slate-400" : "text-slate-700 dark:text-slate-200"}`}
          >
            {r.text}
          </p>
        )}
        {r.bars && (
          <ul className="mt-1.5 space-y-1.5">
            {r.bars.map((b) => (
              <li key={b.label}>
                <div className="flex justify-between gap-2 text-xs">
                  <span className="truncate">{b.label}</span>
                  <span className="tabular-nums text-slate-500">{b.score.toFixed(2)}</span>
                </div>
                <div className="mt-0.5 h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
                  <div
                    className={`h-1.5 rounded-full ${b.score >= 0.35 ? "bg-brand-500" : "bg-slate-400"}`}
                    style={{ width: `${Math.min(100, b.score * 100)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
        {r.chips && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {r.chips.map((c) => (
              <span
                key={c}
                className="rounded-md bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-300"
              >
                {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

function Panel({
  title,
  hint,
  empty,
  rows,
  start,
  live,
  danger,
}: {
  title: string;
  hint: string;
  empty: string;
  rows: Row[];
  start: number;
  live: boolean;
  danger?: boolean;
}) {
  const box = useRef<HTMLOListElement>(null);
  const [follow, setFollow] = useState(true);
  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [rows.length, follow]);
  return (
    <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <header className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
        <div>
          <h2 className="text-sm font-semibold">
            {title}{" "}
            <span
              className={`ml-1 rounded-full px-1.5 py-0.5 text-xs tabular-nums ${
                danger && rows.length
                  ? "bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300"
                  : "bg-slate-100 text-slate-500 dark:bg-slate-800"
              }`}
            >
              {rows.length}
            </span>
          </h2>
          <p className="text-xs text-slate-500">{hint}</p>
        </div>
        {!follow && (
          <button
            onClick={() => setFollow(true)}
            className="rounded-md bg-brand-600 px-2 py-1 text-xs font-medium text-white hover:bg-brand-700"
          >
            ↓ latest
          </button>
        )}
      </header>
      <ol
        ref={box}
        onScroll={(ev) => {
          const el = ev.currentTarget;
          setFollow(el.scrollHeight - el.scrollTop - el.clientHeight < 40);
        }}
        className="h-[62vh] divide-y divide-slate-100 overflow-y-auto dark:divide-slate-800"
      >
        {rows.map((r) => (
          <RowView key={r.key} r={r} start={start} />
        ))}
        {!rows.length && <li className="p-6 text-center text-sm text-slate-500">{empty}</li>}
        {live && rows.length > 0 && (
          <li className="flex items-center gap-2 px-3 py-2 text-xs text-slate-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-rose-500" /> waiting for the next step…
          </li>
        )}
      </ol>
    </section>
  );
}

export default function CallPanels({
  streams,
  live,
  startedAt,
}: {
  streams: Streams;
  live: boolean;
  startedAt: string | null;
}) {
  const [tab, setTab] = useState<PanelKey>("conversation");
  const start = Date.parse(startedAt ?? streams.conversation[0]?.at ?? new Date().toISOString());
  return (
    <div>
      {/* small screens: one panel at a time */}
      <div className="mb-3 flex gap-1 rounded-lg bg-slate-100 p-1 xl:hidden dark:bg-slate-800">
        {PANELS.map((p) => (
          <button
            key={p.key}
            onClick={() => setTab(p.key)}
            className={`flex-1 rounded-md px-2 py-1.5 text-sm font-medium ${
              tab === p.key ? "bg-white shadow-sm dark:bg-slate-900" : "text-slate-500"
            }`}
          >
            {p.title} <span className="tabular-nums text-slate-400">{streams[p.key].length}</span>
          </button>
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-12">
        {PANELS.map((p) => (
          <div
            key={p.key}
            className={`${tab === p.key ? "" : "hidden"} xl:block ${
              p.key === "conversation"
                ? "xl:col-span-5"
                : p.key === "processing"
                  ? "xl:col-span-4"
                  : "xl:col-span-3"
            }`}
          >
            <Panel
              title={p.title}
              hint={p.hint}
              empty={p.empty}
              rows={streams[p.key]}
              start={start}
              live={live}
              danger={p.key === "problems"}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
