import { useEffect, useMemo, useRef, useState } from "react";

import { when } from "./labels";
import type { Category, Entry } from "./liveLog";
import { CATEGORIES } from "./liveLog";

const STYLE: Record<Category, { box: string; side: "left" | "right" | "center" }> = {
  system: {
    side: "left",
    box: "border-brand-100 bg-brand-50 dark:border-blue-900 dark:bg-blue-950/60",
  },
  caller: {
    side: "right",
    box: "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/60",
  },
  answers: {
    side: "center",
    box: "border-l-4 border-slate-300 bg-white dark:border-slate-600 dark:bg-slate-900",
  },
  understanding: {
    side: "center",
    box: "border-l-4 border-violet-400 bg-violet-50 dark:border-violet-500 dark:bg-violet-950/50",
  },
  background: {
    side: "center",
    box: "border-l-4 border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/60",
  },
  problem: {
    side: "center",
    box: "border-l-4 border-rose-400 bg-rose-50 dark:border-rose-500 dark:bg-rose-950/50",
  },
  call: {
    side: "center",
    box: "border-l-4 border-sky-300 bg-sky-50 dark:border-sky-600 dark:bg-sky-950/50",
  },
};

function offset(at: string, start: number): string {
  const s = Math.max(0, Math.round((Date.parse(at) - start) / 1000));
  return `+${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function EntryView({ e, start }: { e: Entry; start: number }) {
  const style = STYLE[e.category];
  const align = style.side === "left" ? "mr-auto" : style.side === "right" ? "ml-auto" : "mx-auto w-full";
  const width = style.side === "center" ? "" : "max-w-[88%]";
  return (
    <li className={`${align} ${width} ${e.muted ? "opacity-70" : ""}`}>
      <div className={`rounded-xl border px-3 py-2 shadow-sm ${style.box}`}>
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <span aria-hidden>{e.icon}</span>
          <span className="text-sm font-semibold">{e.title}</span>
          {e.subtitle && <span className="text-xs text-slate-500 dark:text-slate-400">· {e.subtitle}</span>}
          <span className="ml-auto text-xs tabular-nums text-slate-400" title={when(e.at)}>
            {offset(e.at, start)}
          </span>
        </div>
        {e.lines && (
          <div className="mt-1.5 space-y-2">
            {e.lines.map((l, i) => (
              <div key={i}>
                {l.label && (
                  <div className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                    {l.label}
                  </div>
                )}
                <div className="text-sm leading-relaxed">{l.text}</div>
                {l.en && (
                  <div className="mt-0.5 text-sm italic text-slate-500 dark:text-slate-400">
                    <span className="mr-1 rounded bg-slate-200 px-1 text-[10px] not-italic font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                      EN
                    </span>
                    {l.en}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        {e.bars && (
          <ul className="mt-2 space-y-1.5">
            {e.bars.map((b) => (
              <li key={b.label}>
                <div className="flex justify-between gap-2 text-xs">
                  <span>{b.label}</span>
                  <span className="tabular-nums text-slate-500">{b.score.toFixed(2)}</span>
                </div>
                <div className="mt-0.5 h-1.5 rounded-full bg-violet-100 dark:bg-violet-900/60">
                  <div
                    className={`h-1.5 rounded-full ${b.score >= 0.35 ? "bg-violet-500" : "bg-slate-400"}`}
                    style={{ width: `${Math.min(100, b.score * 100)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
        {e.chips && (
          <div className="mt-2 flex flex-wrap gap-1">
            {e.chips.map((c) => (
              <span
                key={c}
                className="rounded-full bg-white/80 px-2 py-0.5 text-xs text-slate-600 ring-1 ring-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:ring-slate-700"
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

export default function LiveLog({
  entries,
  live,
  startedAt,
}: {
  entries: Entry[];
  live: boolean;
  startedAt?: string | null;
}) {
  const [hidden, setHidden] = useState<Set<Category>>(new Set());
  const [q, setQ] = useState("");
  const [follow, setFollow] = useState(true);
  const box = useRef<HTMLOListElement>(null);
  const start = Date.parse(startedAt ?? entries[0]?.at ?? new Date().toISOString());

  const counts = useMemo(() => {
    const c: Partial<Record<Category, number>> = {};
    for (const e of entries) c[e.category] = (c[e.category] ?? 0) + 1;
    return c;
  }, [entries]);

  const shown = useMemo(() => {
    const w = q.trim().toLowerCase();
    return entries.filter((e) => {
      if (hidden.has(e.category)) return false;
      if (!w) return true;
      const text = [
        e.title,
        e.subtitle,
        ...(e.lines ?? []).flatMap((l) => [l.text, l.en]),
        ...(e.chips ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return text.includes(w);
    });
  }, [entries, hidden, q]);

  useEffect(() => {
    if (follow && box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [shown.length, follow]);

  const toggle = (c: Category) =>
    setHidden((h) => {
      const next = new Set(h);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-1.5">
        {CATEGORIES.filter((c) => counts[c.key]).map((c) => {
          const off = hidden.has(c.key);
          return (
            <button
              key={c.key}
              onClick={() => toggle(c.key)}
              className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 transition ${
                off
                  ? "bg-transparent text-slate-400 ring-slate-200 line-through dark:ring-slate-700"
                  : "bg-white text-slate-700 ring-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:ring-slate-600"
              }`}
              title={off ? "Show" : "Hide"}
            >
              {c.icon} {c.label} <span className="tabular-nums text-slate-400">{counts[c.key]}</span>
            </button>
          );
        })}
        {hidden.size > 0 && (
          <button onClick={() => setHidden(new Set())} className="text-xs text-brand-600 hover:underline">
            show all
          </button>
        )}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search the log…"
          className="ml-auto w-44 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-sm dark:border-slate-700 dark:bg-slate-950"
        />
      </div>
      <ol
        ref={box}
        onScroll={(ev) => {
          const el = ev.currentTarget;
          setFollow(el.scrollHeight - el.scrollTop - el.clientHeight < 40);
        }}
        className="flex max-h-[70vh] min-h-64 flex-col gap-2 overflow-y-auto rounded-lg bg-slate-50/60 p-3 dark:bg-slate-950/40"
      >
        {shown.map((e) => (
          <EntryView key={e.key} e={e} start={start} />
        ))}
        {live && (
          <li className="mx-auto flex items-center gap-2 py-2 text-xs text-slate-500">
            <span className="relative flex h-2.5 w-2.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-rose-400 opacity-75" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-rose-500" />
            </span>
            call in progress, new steps appear here…
          </li>
        )}
        {!shown.length && !live && (
          <li className="py-6 text-center text-sm text-slate-500">Nothing to show.</li>
        )}
      </ol>
      {!follow && (
        <button
          onClick={() => setFollow(true)}
          className="self-center rounded-full bg-brand-600 px-3 py-1 text-xs font-medium text-white shadow hover:bg-brand-700"
        >
          ↓ Jump to latest
        </button>
      )}
    </div>
  );
}
