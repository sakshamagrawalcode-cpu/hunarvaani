import { useEffect, useMemo, useRef, useState } from "react";

import type { PromptCheck, PromptFile } from "../api";
import { useApi } from "../api";
import { LANGUAGE } from "../labels";
import { Badge, Card, Loading, td, th } from "../ui";

// Loudness bar: -40 dBFS (very quiet) … -6 dBFS (very loud). Speech on a phone sits near -20.
function Level({ f }: { f: PromptFile }) {
  if (f.level_db == null) return <span className="text-xs text-slate-400">—</span>;
  const pct = Math.max(0, Math.min(100, ((f.level_db + 40) / 34) * 100));
  const ok = f.level_db >= -32 && (f.peak_db ?? -99) < -0.1;
  return (
    <div className="w-28">
      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
        <div
          className={`h-1.5 rounded-full ${ok ? "bg-emerald-500" : "bg-amber-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-0.5 font-mono text-[11px] text-slate-500">
        {f.level_db} dB · peak {f.peak_db ?? "—"}
      </div>
    </div>
  );
}

export default function Prompts() {
  const { data, error } = useApi<PromptCheck>("/prompts");
  const [lang, setLang] = useState<string>("hi-IN");
  const [playing, setPlaying] = useState<string | null>(null);
  const [onlyProblems, setOnlyProblems] = useState(false);
  const players = useRef(new Map<string, HTMLAudioElement>());
  const queue = useRef<string[]>([]);
  const stamp = useMemo(() => Date.now(), [data]); // a re-rendered file is fetched fresh

  useEffect(() => {
    if (data && !data.languages.includes(lang)) setLang(data.languages[0]);
  }, [data, lang]);

  if (!data) return <Loading error={error} />;

  const rows = data.prompts.map((p) => ({ ...p, f: p.languages[lang] ?? { text: null } }));
  const files = rows.filter((r) => r.f.audio);
  const problems = rows.filter((r) => !r.dynamic && (r.f.issues ?? []).length);
  const shown = onlyProblems ? problems : rows;

  function stopAll() {
    queue.current = [];
    players.current.forEach((a) => {
      a.pause();
      a.currentTime = 0;
    });
    setPlaying(null);
  }

  function playNext() {
    const id = queue.current.shift();
    if (!id) return setPlaying(null);
    const el = players.current.get(id);
    if (!el) return playNext();
    setPlaying(id);
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    el.currentTime = 0;
    void el.play();
  }

  function playAll() {
    stopAll();
    queue.current = files.map((r) => r.id);
    playNext();
  }

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex gap-1 rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
            {data.languages.map((code) => (
              <button
                key={code}
                onClick={() => {
                  stopAll();
                  setLang(code);
                }}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  lang === code ? "bg-white shadow-sm dark:bg-slate-900" : "text-slate-500"
                }`}
              >
                {LANGUAGE[code] ?? code}
              </button>
            ))}
          </div>
          <button
            onClick={playing ? stopAll : playAll}
            className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
          >
            {playing ? "■ Stop" : "▶ Play all in call order"}
          </button>
          <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
            <input type="checkbox" checked={onlyProblems} onChange={(e) => setOnlyProblems(e.target.checked)} />
            only files with problems
          </label>
          <span className="ml-auto text-sm text-slate-500">
            {files.length} files ·{" "}
            {problems.length ? (
              <span className="font-medium text-amber-700 dark:text-amber-400">{problems.length} to check</span>
            ) : (
              <span className="text-emerald-700 dark:text-emerald-400">no problems found</span>
            )}
          </span>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-slate-500">
          These are the files on this laptop in <code>audio/</code>, exactly as rendered. During a call every
          prompt is also brought to the same loudness, so small level differences here do not reach the caller.
          A file marked “text changed” or “not rendered” is fixed with <code>python scripts\render_prompts.py</code>.
        </p>
      </Card>

      <Card>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead>
              <tr>
                <th className={th}>Prompt</th>
                <th className={th}>Words</th>
                <th className={th}>Listen</th>
                <th className={th}>Length</th>
                <th className={th}>Loudness</th>
                <th className={th}>Check</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {shown.map((r) => (
                <tr key={r.id} className={playing === r.id ? "bg-brand-50 dark:bg-blue-950/40" : ""}>
                  <td className={`${td} whitespace-nowrap`}>
                    <div className="font-mono font-semibold">{r.id}</div>
                    <div className="max-w-40 whitespace-normal text-xs text-slate-500">{r.used_for}</div>
                  </td>
                  <td className={`${td} min-w-64 max-w-xl leading-relaxed`}>
                    {r.f.text ?? <span className="text-slate-400">—</span>}
                  </td>
                  <td className={td}>
                    {r.f.audio ? (
                      <audio
                        ref={(el) => {
                          if (el) players.current.set(r.id, el);
                          else players.current.delete(r.id);
                        }}
                        controls
                        preload="none"
                        src={`${r.f.audio}?v=${stamp}`}
                        onEnded={() => playing === r.id && playNext()}
                        className="h-9 w-64"
                      />
                    ) : r.dynamic ? (
                      <span className="text-xs text-slate-500">made during each call</span>
                    ) : (
                      <span className="text-xs text-slate-400">no file</span>
                    )}
                  </td>
                  <td className={`${td} whitespace-nowrap tabular-nums`}>
                    {r.f.seconds != null ? `${r.f.seconds.toFixed(1)} s` : "—"}
                    {r.f.silence_start != null && (
                      <div className="text-[11px] text-slate-500">
                        silent {r.f.silence_start}s / {r.f.silence_end}s
                      </div>
                    )}
                  </td>
                  <td className={td}>
                    <Level f={r.f} />
                  </td>
                  <td className={td}>
                    <div className="flex flex-wrap gap-1">
                      {r.dynamic ? (
                        <Badge tone="blue">live</Badge>
                      ) : (r.f.issues ?? []).length ? (
                        (r.f.issues ?? []).map((i) => (
                          <Badge key={i} tone={r.f.missing ? "red" : "amber"}>
                            {i}
                          </Badge>
                        ))
                      ) : (
                        <Badge tone="green">ok</Badge>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
