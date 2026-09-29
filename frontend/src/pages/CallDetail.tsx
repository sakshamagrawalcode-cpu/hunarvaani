import { Link, useParams } from "react-router-dom";

import type { CallDetail as Detail, Story } from "../api";
import { audioUrl, useApi } from "../api";
import { CONSENT, LANGUAGE, STATUS, describeEvent, occupationName, seconds, value, when } from "../labels";
import { Badge, Card, Empty, Field, Loading, statusTone } from "../ui";

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
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>
          {total > 1 ? `Try ${s.n + 1} of ${total}` : "Work story"} · {when(s.at)}
        </span>
        <span className="tabular-nums">
          speech-to-text {s.stt_ms ?? "—"} ms · search {s.search_ms ?? "—"} ms
        </span>
      </div>
      {s.audio && <audio controls preload="none" src={audioUrl(callId, s.n)} className="w-full" />}
      <blockquote className="border-l-4 border-brand-500 pl-3 text-base">
        {s.transcript ? `“${s.transcript}”` : <span className="text-slate-500">no words recognised</span>}
      </blockquote>
      <dl className="grid gap-3 sm:grid-cols-3">
        <Field label="Understood (1st)">{occupationName(s.top1)}</Field>
        <Field label="Understood (2nd)">{occupationName(s.top2)}</Field>
        <Field label="Caller confirmed">{confirmedText(s)}</Field>
      </dl>
    </div>
  );
}

export default function CallDetail() {
  const { id = "" } = useParams();
  const { data, error } = useApi<Detail>(`/calls/${id}`, 4000);
  if (!data) return <Loading error={error} />;
  const a = data.answers;
  const names = new Map<string, string>();
  for (const o of [data.occupation, ...data.stories.flatMap((s) => [s.top1, s.top2])]) {
    if (o) names.set(o.code, occupationName(o));
  }
  const name = (code: string) => names.get(code) ?? code;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link to="/calls" className="text-sm text-brand-600 hover:underline dark:text-blue-400">
          ← All calls
        </Link>
        <h1 className="text-xl font-semibold">Call {data.short}</h1>
        <Badge tone={statusTone(data.status)}>{STATUS[data.status ?? ""] ?? data.status ?? "—"}</Badge>
        {data.human_flag && <Badge tone="red">wants a human</Badge>}
        {data.keypad_only && <Badge tone="amber">keypad only</Badge>}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card title="Profile">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Field label="Number">
                <span className="font-mono">{data.number ?? "—"}</span>
              </Field>
              <Field label="Language">{LANGUAGE[data.language ?? ""] ?? "—"}</Field>
              <Field label="When (IST)">{when(data.when)}</Field>
              <Field label="Age">{value(a.q_age)}</Field>
              <Field label="Gender">{value(a.q_gender)}</Field>
              <Field label="Education">{value(a.q_education)}</Field>
              <Field label="Can travel">{value(a.q_travel)}</Field>
              <Field label="Physical difficulty">{value(a.q_physical)}</Field>
              <Field label="Wants">{value(a.q_lean)}</Field>
              <Field label="Occupation">
                {occupationName(data.occupation)}
                {data.occupation_via && (
                  <span className="ml-1 text-xs font-normal text-slate-500">({data.occupation_via})</span>
                )}
              </Field>
              <Field label="Call length">{seconds(data.duration)}</Field>
            </dl>
          </Card>

          <Card title="What the caller said, and what we understood">
            {data.stories.length ? (
              <div className="space-y-3">
                {data.stories.map((s) => (
                  <StoryBlock key={s.n} callId={data.id} s={s} total={data.stories.length} />
                ))}
              </div>
            ) : (
              <Empty>No work story in this call{data.keypad_only ? " (no recording consent)" : ""}.</Empty>
            )}
          </Card>

          {data.summary_text && (
            <Card title="Summary spoken at the end">
              <p className="text-sm">{data.summary_text}</p>
            </Card>
          )}
        </div>

        <div className="space-y-6">
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
              <Empty>No consents recorded.</Empty>
            )}
          </Card>

          <Card title="Timeline">
            <ol className="relative space-y-3 border-l border-slate-200 pl-4 dark:border-slate-800">
              {data.events.map((e, i) => (
                <li key={i} className="text-sm">
                  <span className="absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white bg-brand-500 dark:border-slate-900" />
                  <div className="text-xs tabular-nums text-slate-500">{when(e.at)}</div>
                  <div>{describeEvent(e, name)}</div>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </div>
  );
}
