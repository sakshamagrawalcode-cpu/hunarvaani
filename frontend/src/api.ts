import { useCallback, useEffect, useState } from "react";

export type Occupation = { code: string; title_en: string; title_hi: string; title_mr: string };

export type CallRow = {
  id: string;
  short: string;
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
};

export type Story = {
  n: number;
  transcript: string | null;
  top1: Occupation | null;
  top2: Occupation | null;
  confirmed: string | null;
  stt_ms: number | null;
  search_ms: number | null;
  at: string | null;
  audio: boolean;
};

export type CallEvent = { kind: string; payload: Record<string, unknown> | null; at: string };

export type CallDetail = CallRow & {
  answer_log: { step: string; key: string | null; value: string | null; at: string }[];
  consents: { kind: string; granted: boolean; at: string }[];
  stories: Story[];
  events: CallEvent[];
  summary_text: string | null;
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
};

export type OccupationRow = Occupation & { aliases: string[]; callers: number };

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

/** Load `path` and reload it every `everyMs` (0 = once). */
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
    void load();
    if (!everyMs) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, everyMs);
    return () => window.clearInterval(timer);
  }, [load, everyMs]);

  return { data, error, updated, reload: load };
}
