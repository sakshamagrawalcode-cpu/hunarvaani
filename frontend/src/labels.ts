// Readable names for the values the interview stores. English first, the caller's words in
// brackets where that helps.

import type { Occupation } from "./api";

export const LANGUAGE: Record<string, string> = {
  "hi-IN": "Hindi (हिंदी)",
  "en-IN": "English",
  "mr-IN": "Marathi (मराठी)",
};

export const STEP: Record<string, string> = {
  opening: "Greeting",
  language: "Language",
  safe_to_talk: "OK to talk now?",
  consent_recording: "Consent: recording",
  consent_share: "Consent: share with centre/bank",
  consent_research: "Consent: anonymous research",
  q_age: "Age",
  q_gender: "Gender",
  q_education: "Education",
  q_travel: "Can travel",
  q_physical: "Physical difficulty",
  q_lean: "Wants",
  story: "Work story",
  readback: "Read-back",
  trades: "Trade list",
  occupation: "Occupation",
};

export const VALUE: Record<string, string> = {
  under_18: "Under 18",
  "18_25": "18–25",
  "26_35": "26–35",
  "36_45": "36–45",
  "46_60": "46–60",
  over_60: "Over 60",
  female: "Woman",
  male: "Man",
  other: "Other",
  not_said: "Prefers not to say",
  none: "None",
  upto_5th: "Up to 5th",
  upto_8th: "Up to 8th",
  "10th": "10th pass",
  "12th": "12th pass",
  iti_or_diploma: "ITI / diploma",
  graduate: "Graduate",
  village: "Only in village",
  "10km": "Up to 10 km",
  "30km": "Up to 30 km",
  district_hq: "District HQ",
  hostel: "Can stay in hostel",
  some: "Some difficulty",
  job: "A regular job",
  own_work: "Own work / business",
  unsure: "Not sure",
  skipped: "Skipped",
};

export const CONSENT: Record<string, string> = {
  recording: "Record the call",
  share: "Share with a training centre or bank",
  research: "Use (without name and number) to train our AI and recommendation models",
};

export const STATUS: Record<string, string> = {
  completed: "Completed",
  in_call: "In call now",
  queued: "Callback queued",
  dialing: "Dialling",
  no_answer: "No answer",
  dial_failed: "Dial failed",
};

export function value(v: string | null | undefined): string {
  if (!v) return "—";
  return VALUE[v] ?? v;
}

export function occupationName(o: Occupation | null | undefined): string {
  if (!o) return "—";
  return o.title_hi ? `${o.title_en} (${o.title_hi})` : o.title_en || o.code;
}

const IST = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

export function when(iso: string | null | undefined): string {
  return iso ? IST.format(new Date(iso)) : "—";
}

export function seconds(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  return s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
}
