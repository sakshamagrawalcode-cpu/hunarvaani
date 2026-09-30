import { useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Person } from "../api";
import { useApi } from "../api";
import { LANGUAGE, occupationName, optionText, value, when } from "../labels";
import { Badge, Card, DistrictFilter, Empty, Loading, byDistrict, td, th } from "../ui";

export default function People() {
  const { data, error } = useApi<Person[]>("/people", 10000);
  const navigate = useNavigate();
  const [district, setDistrict] = useState("");
  if (!data) return <Loading error={error} />;
  const shown = data.filter(byDistrict(district));
  return (
    <Card
      title={`People (${shown.length} of ${data.length})`}
      right={<DistrictFilter rows={data} value={district} onChange={setDistrict} />}
    >
      <p className="mb-3 text-sm text-slate-500">
        One row per caller, with the latest answer they gave for each question across all their calls.
      </p>
      {shown.length ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
            <thead>
              <tr>
                <th className={th}>Number</th>
                <th className={th}>Calls</th>
                <th className={th}>Last call</th>
                <th className={th}>Language</th>
                <th className={th}>Age</th>
                <th className={th}>Gender</th>
                <th className={th}>Education</th>
                <th className={th}>Can travel</th>
                <th className={th}>Physical</th>
                <th className={th}>District</th>
                <th className={th}>Wants</th>
                <th className={th}>Occupation</th>
                <th className={th}>Chosen option</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {shown.map((p) => (
                <tr
                  key={p.id}
                  onClick={() => navigate(`/calls/${p.last_call_id}`)}
                  className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/60"
                >
                  <td className={`${td} font-mono`}>
                    {p.number ?? "—"} {p.human_flag && <Badge tone="red">human</Badge>}
                  </td>
                  <td className={`${td} tabular-nums`}>{p.calls}</td>
                  <td className={`${td} whitespace-nowrap`}>{when(p.last_call)}</td>
                  <td className={td}>{LANGUAGE[p.language ?? ""] ?? "—"}</td>
                  <td className={td}>{value(p.answers.q_age)}</td>
                  <td className={td}>{value(p.answers.q_gender)}</td>
                  <td className={td}>{value(p.answers.q_education)}</td>
                  <td className={td}>{value(p.answers.q_travel)}</td>
                  <td className={td}>{value(p.answers.q_physical)}</td>
                  <td className={td}>{value(p.answers.q_district)}</td>
                  <td className={td}>{value(p.answers.q_lean)}</td>
                  <td className={td}>{occupationName(p.occupation)}</td>
                  <td className={td}>{optionText(p.option)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty>No callers yet.</Empty>
      )}
    </Card>
  );
}
