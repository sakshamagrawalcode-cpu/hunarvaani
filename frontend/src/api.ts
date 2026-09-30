import { useCallback, useEffect, useState } from "react";

export type Occupation = { code: string; title_en: string; title_hi: string; title_mr: string };

export type CallRow = {
  id: string;
  short: string;
  ref: string;
  when: string | null;
  number: string | null;
  status: string | null;
  language: string | null;
  duration: number | null;
  answers: Record<string, string | null>;
  occupation: Occupation | null;
  occupation_via: string | null;
  transcripts: string[];
  human_flag: boolean;
  keypad_only: boolean;
  live: boolean;
  district_code: string | null;
  option: OptionOutcome | null;
};

// What happened with the training options on a call (null: none were found yet)
export type OptionOutcome = { offered: number; spoken: boolean; chosen: string | null; declined: boolean };

export type Story = {
  n: number;
  transcript: string | null;
  top1: Occupation | null;
  top2: Occupation | null;
  top3: Occupation | null;
  llm: { occupations: string[]; years: number | null; skills: string[]; wants: string | null; said: string } | null;
  confirmed: string | null;
  stt_ms: number | null;
  search_ms: number | null;
  at: string | null;
  audio: boolean;
};

export type CallEvent = { id: number; kind: string; payload: Record<string, unknown> | null; at: string };

export type Recommendation = {
  rank: number;
  course_id: string;
  kind: string;
  title: string;
  nsqf_level: number;
  hours: number;
  fee_inr: number;
  placement: boolean;
  scheme: string;
  loan: string | null;
  centre: string | null;
  distance_km: number | null;
  farther: boolean;
  score: number;
  reasons: string[];
  skill_gap: string[];
  spoken: boolean;
  chosen: boolean;
};

export type CallDetail = CallRow & {
  answer_log: { step: string; key: string | null; value: string | null; at: string }[];
  consents: { kind: string; granted: boolean; at: string }[];
  stories: Story[];
  events: CallEvent[];
  summary_text: string | null;
  recommendations: Recommendation[];
  missed_at: string | null;
  callback_at: string | null;
  answered_at: string | null;
  ended_at: string | null;
};

export type Summary = {
  calls: number;
  completed: number;
  today: number;
  people: number;
  avg_duration: number | null;
  human_flags: number;
  keypad_only: number;
  with_occupation: number;
  languages: Record<string, number>;
  statuses: Record<string, number>;
  occupations: (Occupation & { count: number })[];
  recent: CallRow[];
  live_now: CallRow[];
};

export type Person = {
  id: string;
  number: string | null;
  calls: number;
  last_call: string | null;
  last_call_id: string;
  language: string | null;
  answers: Record<string, string>;
  occupation: Occupation | null;
  human_flag: boolean;
  district_code: string | null;
  option: OptionOutcome | null;
};

export type Dataset = {
  courses: {
    id: string;
    kind: string;
    title: string;
    for: string[];
    sector: string;
    nsqf_level: number;
    hours: number;
    min_education: string;
    ages: string;
    fee_inr: number;
    placement: boolean;
    heavy_work: boolean;
    skills: string[];
    scheme: string;
  }[];
  centres: {
    id: string;
    name: string;
    type: string;
    district_code: string;
    district: string;
    distance_km: number;
    hostel: boolean;
    women_batches: boolean;
    sectors: string[];
  }[];
  schemes: { id: string; name: string; name_hi: string; kind: string; benefit: string; eligibility: string }[];
  districts: { code: string; name: string }[];
};

export type OccupationRow = Occupation & { aliases: string[]; callers: number };

export type PromptFile = {
  text: string | null;
  audio?: string;
  missing?: boolean;
  seconds?: number;
  level_db?: number | null;
  peak_db?: number | null;
  silence_start?: number;
  silence_end?: number;
  issues?: string[];
};

export type PromptCheck = {
  languages: string[];
  prompts: { id: string; used_for: string; dynamic: boolean; languages: Record<string, PromptFile> }[];
};

export const API = "/console/api";

export function audioUrl(callId: string, n: number): string {
  return `${API}/calls/${callId}/audio/${n}`;
}

export async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(API + path, { credentials: "same-origin" });
  if (res.status === 401) throw new Error("Signed out: reload the page and enter the password.");
  if (!res.ok) throw new Error(`The server answered ${res.status}.`);
  return res.json() as Promise<T>;
}

/** Load `path` and reload it every `everyMs` (0 = once); `everyMs` may change (e.g. faster while live). */
export function useApi<T>(path: string, everyMs = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [updated, setUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await getJson<T>(path));
      setError(null);
      setUpdated(new Date());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [path]);

  useEffect(() => {
    setData(null);
  }, [path]);

  useEffect(() => {
    void load();
    if (!everyMs) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, everyMs);
    return () => window.clearInterval(timer);
  }, [load, everyMs]);

  return { data, error, updated, reload: load };
}
