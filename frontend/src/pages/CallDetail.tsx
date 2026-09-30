import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import type { CallDetail as Detail, Recommendation, Story } from "../api";
import { audioUrl, useApi } from "../api";
import CallPanels from "../CallPanels";
import { CONSENT, LANGUAGE, STATUS, occupationName, seconds, value, when } from "../labels";
import { buildStreams } from "../liveLog";
import { Badge, Card, Empty, LiveBadge, Loading, statusTone } from "../ui";

function confirmedText(s: Story): string {
  if (!s.confirmed) return "not asked (unclear or too slow)";
  if (s.confirmed === "none") return "none of them was right";
  if (s.top1?.code === s.confirmed) return `yes: ${occupationName(s.top1)}`;
  if (s.top2?.code === s.confirmed) return `yes: ${occupationName(s.top2)}`;
  if (s.top3?.code === s.confirmed) return `yes: ${occupationName(s.top3)}`;
  return s.confirmed;
}

const KIND: Record<string, string> = {
  upskill: "Upskilling course",
  certificate: "Certificate (RPL)",
  startup: "Own work / business",
};

function Options({ items }: { items: Recommendation[] }) {
  if (!items.length) return <Empty>No options yet (they come after the occupation is known).</Empty>;
  const spoken = items.some((r) => r.spoken);
  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500">
        {spoken ? "Said on the call" : "Found, but not said on the call (voice could not be made)"}
        {" · "}all courses, centres and numbers are sample data
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        {items.map((r) => (
          <div
            key={r.rank}
            className={`space-y-2 rounded-lg border p-3 ${
              r.chosen
                ? "border-emerald-400 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/40"
                : "border-slate-200 dark:border-slate-800"
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm font-semibold">
                {r.rank}. {r.title}
              </div>
              {r.chosen && <Badge tone="green">caller chose</Badge>}
            </div>
            <div className="text-xs text-slate-500">
              {KIND[r.kind] ?? r.kind} · NSQF {r.nsqf_level} · {r.hours} h ·{" "}
              {r.fee_inr ? `Rs ${r.fee_inr}` : "free"}
              {r.placement && " · placement"}
            </div>
            <div className="text-xs">
              {r.centre ? `${r.centre}, about ${r.distance_km} km` : "Centre to be confirmed"}
              {r.farther && (
                <>
                  {" "}
                  <Badge tone="amber">farther than they said</Badge>
                </>
              )}
            </div>
            <div className="text-xs text-slate-500">
              Scheme: {r.scheme}
              {r.loan && ` · loan: ${r.loan}`}
            </div>
            <ul className="list-disc space-y-0.5 pl-4 text-xs">
              {r.reasons.map((why) => (
                <li key={why}>{why}</li>
              ))}
            </ul>
            <div className="text-xs">
              <span className="font-medium">Skill gap: </span>
              {r.skill_gap.length ? r.skill_gap.join(", ") : "none (certificate for what they know)"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="text-[11px] font-medium uppercase tracking-wide text-slate-400">{label}</div>
      <div className="truncate text-sm font-medium">{children}</div>
    </div>
  );
}

export default function CallDetail() {
  const { id = "" } = useParams();
  const [fast, setFast] = useState(true); // refresh every 1.5 s while the call is live
  const { data, error } = useApi<Detail>(`/calls/${id}`, fast ? 1500 : 10000);
  useEffect(() => {
    if (data) setFast(data.live);
  }, [data]);
  if (!data) return <Loading error={error} />;
  const a = data.answers;
  const names = new Map<string, string>();
  for (const o of [data.occupation, ...data.stories.flatMap((s) => [s.top1, s.top2, s.top3])]) {
    if (o) names.set(o.code, occupationName(o));
  }
  const streams = buildStreams(data.events, (code) => names.get(code) ?? code);
  const started = data.answered_at ?? data.callback_at ?? data.when;
  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-3">
          <Link to="/calls" className="text-sm text-brand-600 hover:underline dark:text-blue-400">
            ← Calls
          </Link>
          <h1 className="text-lg font-semibold">Call {data.short}</h1>
          <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-sm dark:bg-slate-800" title="reference number said to the caller">
            Ref {data.ref}
          </span>
          {data.live ? (
            <LiveBadge />
          ) : (
            <Badge tone={statusTone(data.status)}>{STATUS[data.status ?? ""] ?? data.status ?? "—"}</Badge>
          )}
          {data.human_flag && <Badge tone="red">wants a human</Badge>}
          {data.keypad_only && <Badge tone="amber">keypad only</Badge>}
          <span className="ml-auto text-sm text-slate-500">
            <span className="font-mono">{data.number ?? "—"}</span> ·{" "}
            {LANGUAGE[data.language ?? ""] ?? "choosing language"} · started {when(started)}
            {data.duration !== null && ` · ${seconds(data.duration)}`}
          </span>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-4 border-t border-slate-100 pt-4 sm:grid-cols-4 lg:grid-cols-8 dark:border-slate-800">
          <Fact label="Age">{value(a.q_age)}</Fact>
          <Fact label="Gender">{value(a.q_gender)}</Fact>
          <Fact label="Education">{value(a.q_education)}</Fact>
          <Fact label="Can travel">{value(a.q_travel)}</Fact>
          <Fact label="Physical difficulty">{value(a.q_physical)}</Fact>
          <Fact label="District">{value(a.q_district)}</Fact>
          <Fact label="Wants">{value(a.q_lean)}</Fact>
          <Fact label="Occupation">{occupationName(data.occupation)}</Fact>
        </div>
      </div>

      <CallPanels streams={streams} live={data.live} startedAt={started} />

      <Card title="Training and livelihood options">
        <Options items={data.recommendations ?? []} />
      </Card>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card title="Work story recordings">
            {data.stories.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {data.stories.map((s) => (
                  <div
                    key={s.n}
                    className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800"
                  >
                    <div className="text-xs text-slate-500">
                      {data.stories.length > 1 ? `Try ${s.n + 1}` : "Work story"} · {when(s.at)}
                    </div>
                    {s.audio && (
                      <audio controls preload="none" src={audioUrl(data.id, s.n)} className="w-full" />
                    )}
                    <p className="text-sm">
                      {s.transcript ? (
                        `“${s.transcript}”`
                      ) : (
                        <span className="text-slate-500">no words recognised</span>
                      )}
                    </p>
                    <p className="text-xs text-slate-500">
                      Understood: {occupationName(s.top1)}
                      {s.top2 && ` · or ${occupationName(s.top2)}`}
                      {s.top3 && ` · or ${occupationName(s.top3)}`} · Confirmed: {confirmedText(s)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <Empty>No work story{data.keypad_only ? " (no recording consent)" : " yet"}.</Empty>
            )}
          </Card>
        </div>
        <Card title="Consents">
          {data.consents.length ? (
            <ul className="space-y-2 text-sm">
              {data.consents.map((c) => (
                <li key={c.kind} className="flex justify-between gap-3">
                  <span>{CONSENT[c.kind] ?? c.kind}</span>
                  <Badge tone={c.granted ? "green" : "gray"}>{c.granted ? "yes" : "no"}</Badge>
                </li>
              ))}
            </ul>
          ) : (
            <Empty>No consents yet.</Empty>
          )}
        </Card>
      </div>
    </div>
  );
}
