import { useMemo, useState } from "react";

import type { Dataset } from "../api";
import { useApi } from "../api";
import { value } from "../labels";
import { Badge, Card, Empty, Loading, td, th } from "../ui";

const TABS = ["courses", "centres", "schemes"] as const;
type Tab = (typeof TABS)[number];

const KIND: Record<string, string> = {
  upskill: "Upskilling",
  certificate: "Certificate (RPL)",
  startup: "Own work",
};

function matches(words: string[], ...parts: (string | number | boolean | string[])[]): boolean {
  const text = parts.flat().join(" ").toLowerCase();
  return words.every((w) => text.includes(w));
}

export default function SampleData() {
  const { data, error } = useApi<Dataset>("/dataset");
  const [tab, setTab] = useState<Tab>("courses");
  const [q, setQ] = useState("");
  const [district, setDistrict] = useState("");
  const words = useMemo(() => q.toLowerCase().split(/\s+/).filter(Boolean), [q]);
  if (!data) return <Loading error={error} />;

  const courses = data.courses.filter((c) =>
    matches(words, c.id, c.title, c.for, c.sector, c.scheme, c.skills, KIND[c.kind] ?? c.kind),
  );
  const centres = data.centres.filter(
    (c) => (!district || c.district_code === district) && matches(words, c.name, c.district, c.type, c.sectors),
  );
  const schemes = data.schemes.filter((s) => matches(words, s.name, s.name_hi, s.benefit, s.eligibility));
  const count = { courses: courses.length, centres: centres.length, schemes: schemes.length };

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
        <b>Sample data for the demonstration.</b> Courses, centres, distances, demand and wages are made up; course
        ids are ours, not real NSQF codes. Scheme descriptions are simplified and must be checked against the official
        sources.
      </div>
      <Card
        right={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {tab === "centres" && (
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
              >
                <option value="">All districts</option>
                {data.districts.map((d) => (
                  <option key={d.code} value={d.code}>
                    {d.name}
                  </option>
                ))}
              </select>
            )}
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search…"
              className="w-56 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-950"
            />
          </div>
        }
        title={undefined}
      >
        <div className="mb-3 flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize ${
                tab === t ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900" : "hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              {t} ({count[t]})
            </button>
          ))}
        </div>
        <div className="overflow-x-auto">
          {tab === "courses" &&
            (courses.length ? (
              <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
                <thead>
                  <tr>
                    <th className={th}>Course</th>
                    <th className={th}>For</th>
                    <th className={th}>Kind</th>
                    <th className={th}>NSQF</th>
                    <th className={th}>Hours</th>
                    <th className={th}>Min. education</th>
                    <th className={th}>Ages</th>
                    <th className={th}>Scheme</th>
                    <th className={th}>Skills taught</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {courses.map((c) => (
                    <tr key={c.id}>
                      <td className={td}>
                        <div className="font-medium">{c.title}</div>
                        <div className="text-xs text-slate-500">
                          {c.id} · {c.fee_inr ? `Rs ${c.fee_inr}` : "free"}
                          {c.placement && " · placement"}
                          {c.heavy_work && " · heavy work"}
                        </div>
                      </td>
                      <td className={`${td} max-w-[12rem]`}>{c.for.join(", ")}</td>
                      <td className={td}>{KIND[c.kind] ?? c.kind}</td>
                      <td className={td}>{c.nsqf_level}</td>
                      <td className={td}>{c.hours}</td>
                      <td className={td}>{value(c.min_education)}</td>
                      <td className={td}>{c.ages}</td>
                      <td className={`${td} max-w-[12rem]`}>{c.scheme}</td>
                      <td className={`${td} max-w-[16rem] text-xs`}>{c.skills.join(", ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <Empty>No course matches.</Empty>
            ))}
          {tab === "centres" &&
            (centres.length ? (
              <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800">
                <thead>
                  <tr>
                    <th className={th}>Centre</th>
                    <th className={th}>District</th>
                    <th className={th}>Distance</th>
                    <th className={th}>Facilities</th>
                    <th className={th}>Teaches</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {centres.map((c) => (
                    <tr key={c.id}>
                      <td className={td}>{c.name}</td>
                      <td className={td}>{c.district}</td>
                      <td className={td}>{c.distance_km} km</td>
                      <td className={`${td} space-x-1`}>
                        {c.hostel && <Badge tone="blue">hostel</Badge>}
                        {c.women_batches && <Badge tone="green">women-only batches</Badge>}
                      </td>
                      <td className={`${td} max-w-[24rem] text-xs`}>{c.sectors.join(", ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <Empty>No centre matches.</Empty>
            ))}
          {tab === "schemes" &&
            (schemes.length ? (
              <ul className="space-y-3">
                {schemes.map((s) => (
                  <li key={s.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-800">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{s.name}</span>
                      <span className="text-sm text-slate-500">{s.name_hi}</span>
                      <Badge>{s.kind.replace(/_/g, " ")}</Badge>
                    </div>
                    <p className="mt-1 text-sm">{s.benefit}</p>
                    <p className="mt-1 text-xs text-slate-500">Who: {s.eligibility}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>No scheme matches.</Empty>
            ))}
        </div>
      </Card>
    </div>
  );
}
