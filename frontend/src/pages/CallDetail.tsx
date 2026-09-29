import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import type { CallDetail as Detail, Story } from "../api";
import { audioUrl, useApi } from "../api";
import { CONSENT, LANGUAGE, STATUS, occupationName, seconds, value, when } from "../labels";
import LiveLog from "../LiveLog";
import { buildLog } from "../liveLog";
import { Badge, Card, Empty, Field, LiveBadge, Loading, statusTone } from "../ui";

function confirmedText(s: Story): string {
  if (!s.confirmed) return "not asked (unclear or too slow)";
  if (s.confirmed === "none") return "neither was right";
  if (s.top1?.code === s.confirmed) return `yes: ${occupationName(s.top1)}`;
  if (s.top2?.code === s.confirmed) return `yes: ${occupationName(s.top2)}`;
  return s.confirmed;
}

function StoryBlock({ callId, s, total }: { callId: string; s: Story; total: number }) {
  return (
    <div className="space-y-2 rounded-lg border border-slate-200 p-3 dark:border-slate-800">
      <div className="text-xs text-slate-500">
        {total > 1 ? `Try ${s.n + 1} of ${total}` : "Work story"} · {when(s.at)}
      </div>
      {s.audio && <audio controls preload="none" src={audioUrl(callId, s.n)} className="w-full" />}
      <blockquote className="border-l-4 border-emerald-500 pl-3">
        <div>
          {s.transcript ? `“${s.transcript}”` : <span className="text-slate-500">no words recognised</span>}
        </div>
        {s.transcript_en && s.transcript_en !== s.transcript && (
          <div className="mt-1 text-sm italic text-slate-500">EN: “{s.transcript_en}”</div>
        )}
      </blockquote>
      <dl className="grid gap-2">
        <Field label="Understood">
          {occupationName(s.top1)}
          {s.top2 && <span className="font-normal text-slate-500"> · or {occupationName(s.top2)}</span>}
        </Field>
        <Field label="Caller confirmed">{confirmedText(s)}</Field>
      </dl>
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
  for (const o of [data.occupation, ...data.stories.flatMap((s) => [s.top1, s.top2])]) {
    if (o) names.set(o.code, occupationName(o));
  }
  const entries = buildLog(data.events, (code) => names.get(code) ?? code);
  const started = data.answered_at ?? data.callback_at ?? data.when;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/calls" className="text-sm text-brand-600 hover:underline dark:text-blue-400">
          ← All calls
        </Link>
        <h1 className="text-xl font-semibold">Call {data.short}</h1>
        {data.live ? (
          <LiveBadge />
        ) : (
          <Badge tone={statusTone(data.status)}>{STATUS[data.status ?? ""] ?? data.status ?? "—"}</Badge>
        )}
        {data.human_flag && <Badge tone="red">wants a human</Badge>}
        {data.keypad_only && <Badge tone="amber">keypad only</Badge>}
        <span className="text-sm text-slate-500">
          {LANGUAGE[data.language ?? ""] ?? "language not chosen yet"} ·{" "}
          <span className="font-mono">{data.number ?? "—"}</span> · started {when(started)}
          {data.duration !== null && ` · ${seconds(data.duration)}`}
        </span>
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card title="Live log: everything that happened, step by step">
            <LiveLog entries={entries} live={data.live} startedAt={started} />
          </Card>
        </div>

        <div className="space-y-5">
          <Card title="Profile">
            <dl className="grid grid-cols-2 gap-3">
              <Field label="Age">{value(a.q_age)}</Field>
              <Field label="Gender">{value(a.q_gender)}</Field>
              <Field label="Education">{value(a.q_education)}</Field>
              <Field label="Can travel">{value(a.q_travel)}</Field>
              <Field label="Physical difficulty">{value(a.q_physical)}</Field>
              <Field label="Wants">{value(a.q_lean)}</Field>
              <div className="col-span-2">
                <Field label="Occupation">
                  {occupationName(data.occupation)}
                  {data.occupation_via && (
                    <span className="ml-1 text-xs font-normal text-slate-500">({data.occupation_via})</span>
                  )}
                </Field>
              </div>
            </dl>
          </Card>

          <Card title="Work story: said, understood, confirmed">
            {data.stories.length ? (
              <div className="space-y-3">
                {data.stories.map((s) => (
                  <StoryBlock key={s.n} callId={data.id} s={s} total={data.stories.length} />
                ))}
              </div>
            ) : (
              <Empty>No work story yet{data.keypad_only ? " (no recording consent)" : ""}.</Empty>
            )}
          </Card>

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
    </div>
  );
}
