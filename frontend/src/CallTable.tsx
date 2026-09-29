import { useNavigate } from "react-router-dom";

import type { CallRow } from "./api";
import { LANGUAGE, STATUS, occupationName, seconds, value, when } from "./labels";
import { Badge, Empty, LiveBadge, statusTone, td, th } from "./ui";

export default function CallTable({ calls }: { calls: CallRow[] }) {
  const navigate = useNavigate();
  if (!calls.length) return <Empty>No calls yet. Make a test call and it shows up here.</Empty>;
  return (
    <>
      {/* phones: one card per call */}
      <ul className="space-y-2 md:hidden">
        {calls.map((c) => (
          <li
            key={c.id}
            onClick={() => navigate(`/calls/${c.id}`)}
            className="cursor-pointer rounded-lg border border-slate-200 p-3 dark:border-slate-800"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-sm">{c.number ?? "—"}</span>
              {c.live ? (
                <LiveBadge />
              ) : (
                <Badge tone={statusTone(c.status)}>{STATUS[c.status ?? ""] ?? c.status ?? "—"}</Badge>
              )}
            </div>
            <div className="mt-1 text-xs text-slate-500">
              {when(c.when)} · {LANGUAGE[c.language ?? ""] ?? "—"} · {seconds(c.duration)}
            </div>
            <div className="mt-1 text-sm">{occupationName(c.occupation)}</div>
            <div className="mt-1 text-xs text-slate-500">
              {[value(c.answers.q_age), value(c.answers.q_gender), value(c.answers.q_education)].join(" · ")}
            </div>
            {(c.human_flag || c.keypad_only) && (
              <div className="mt-1 space-x-1">
                {c.human_flag && <Badge tone="red">wants a human</Badge>}
                {c.keypad_only && <Badge tone="amber">keypad only</Badge>}
              </div>
            )}
          </li>
        ))}
      </ul>
      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
          <thead>
            <tr>
              <th className={th}>When (IST)</th>
              <th className={th}>Number</th>
              <th className={th}>Status</th>
              <th className={th}>Language</th>
              <th className={th}>Duration</th>
              <th className={th}>Age</th>
              <th className={th}>Gender</th>
              <th className={th}>Education</th>
              <th className={th}>Occupation</th>
              <th className={th}>Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {calls.map((c) => (
              <tr
                key={c.id}
                onClick={() => navigate(`/calls/${c.id}`)}
                className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60"
              >
                <td className={`${td} whitespace-nowrap`}>{when(c.when)}</td>
                <td className={`${td} whitespace-nowrap font-mono`}>{c.number ?? "—"}</td>
                <td className={td}>
                  {c.live ? (
                    <LiveBadge />
                  ) : (
                    <Badge tone={statusTone(c.status)}>{STATUS[c.status ?? ""] ?? c.status ?? "—"}</Badge>
                  )}
                </td>
                <td className={`${td} whitespace-nowrap`}>{LANGUAGE[c.language ?? ""] ?? "—"}</td>
                <td className={`${td} whitespace-nowrap`}>{seconds(c.duration)}</td>
                <td className={`${td} whitespace-nowrap`}>{value(c.answers.q_age)}</td>
                <td className={`${td} whitespace-nowrap`}>{value(c.answers.q_gender)}</td>
                <td className={td}>{value(c.answers.q_education)}</td>
                <td className={td}>
                  {c.occupation ? (
                    <>
                      <div>{occupationName(c.occupation)}</div>
                      <div className="text-xs text-slate-500">{c.occupation_via}</div>
                    </>
                  ) : (
                    "—"
                  )}
                </td>
                <td className={`${td} space-x-1`}>
                  {c.human_flag && <Badge tone="red">wants a human</Badge>}
                  {c.keypad_only && <Badge tone="amber">keypad only</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
