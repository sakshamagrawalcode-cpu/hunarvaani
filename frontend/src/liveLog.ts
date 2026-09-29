// Turns a call's raw events into categorised, readable entries for the live log.

import type { CallEvent } from "./api";
import { CONSENT, LANGUAGE, STEP, value } from "./labels";

export type Category = "system" | "caller" | "answers" | "understanding" | "background" | "problem" | "call";

export const CATEGORIES: { key: Category; label: string; icon: string }[] = [
  { key: "system", label: "System said", icon: "🔊" },
  { key: "caller", label: "Caller", icon: "🙋" },
  { key: "answers", label: "Answers & consents", icon: "📝" },
  { key: "understanding", label: "Understanding", icon: "🧠" },
  { key: "background", label: "Background", icon: "⚙️" },
  { key: "problem", label: "Problems", icon: "⚠️" },
  { key: "call", label: "Call", icon: "📞" },
];

export type Line = { text: string; en?: string | null; label?: string };

export type Entry = {
  key: string;
  at: string;
  category: Category;
  icon: string;
  title: string;
  subtitle?: string;
  lines?: Line[];
  chips?: string[];
  bars?: { label: string; score: number }[];
  muted?: boolean;
};

type P = Record<string, unknown>;

const STOPPED: Record<string, string> = {
  silence: "stopped after silence",
  key: "caller pressed #",
  no_speech: "no speech heard",
  time_limit: "60 s limit reached",
  hangup: "caller hung up",
};

function step(p: P): string {
  const s = String(p.step ?? "");
  return STEP[s] ?? (s === "goodbye" ? "Goodbye" : s);
}

function ms(label: string, v: unknown): string | null {
  return typeof v === "number" ? `${label} ${v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`}` : null;
}

function promptLine(q: P): Line {
  const id = String(q.id ?? "");
  const text = q.text ? String(q.text) : id.startsWith("DYN:") ? "(generated sentence)" : id;
  const lang = LANGUAGE[String(q.language ?? "")]?.split(" ")[0];
  return {
    text,
    en: q.text_en ? String(q.text_en) : null,
    label: id.startsWith("DYN:") ? `generated · ${lang ?? ""}` : `${id.split("@")[0]} · ${lang ?? ""}`,
  };
}

export function buildLog(events: CallEvent[], name: (code: string) => string): Entry[] {
  const hasSay = events.some((e) => e.kind === "say");
  const out: Entry[] = [];
  for (const e of events) {
    const p = (e.payload ?? {}) as P;
    const base = { at: e.at, key: String(e.id ?? `${e.kind}-${e.at}`) };
    switch (e.kind) {
      case "say":
        out.push({
          ...base,
          category: "system",
          icon: "🔊",
          title: "System said",
          subtitle: step(p),
          lines: ((p.prompts as P[]) ?? []).map(promptLine),
          chips: p.beep ? ["🔔 beep, then recording starts"] : undefined,
        });
        break;
      case "key":
        out.push({ ...base, category: "caller", icon: "⌨️", title: `Pressed ${p.digit}`, subtitle: step(p) });
        break;
      case "timeout":
        out.push({
          ...base,
          category: "caller",
          icon: "⏳",
          title: "No key pressed in time",
          subtitle: step(p),
          muted: true,
        });
        break;
      case "recording":
        out.push({
          ...base,
          category: "caller",
          icon: "🎙️",
          title: `Spoke for ${p.seconds} s`,
          subtitle: STOPPED[String(p.stopped_by)] ?? String(p.stopped_by ?? ""),
        });
        break;
      case "story_recorded": {
        if (p.transcript) {
          out.push({
            ...base,
            key: `${base.key}-said`,
            category: "caller",
            icon: "🗣️",
            title: "Caller said",
            lines: [{ text: String(p.transcript), en: p.transcript_en ? String(p.transcript_en) : null }],
          });
        }
        const scores = (p.scores as P[]) ?? [];
        if (scores.length) {
          out.push({
            ...base,
            key: `${base.key}-understood`,
            category: "understanding",
            icon: "🧠",
            title: "Occupation search",
            subtitle: "best two matches (score out of 1.00; 0.35 or more = confident)",
            bars: scores.map((s) => ({
              label: s.title_en ? `${s.title_en} (${s.title_hi})` : name(String(s.code)),
              score: Number(s.score),
            })),
          });
        }
        const chips = [
          ms("speech-to-text", p.stt_ms),
          ms("search", p.search_ms),
          ms("voice made", p.tts_ms),
          ms("translation", p.translate_ms),
          ms("caller waited", p.wait_ms),
        ].filter((c): c is string => Boolean(c));
        if (chips.length) {
          out.push({
            ...base,
            key: `${base.key}-timing`,
            category: "background",
            icon: "⚙️",
            title: "Worker processed the story",
            subtitle: "Sarvam speech-to-text → occupation search → voice for the read-back",
            chips,
          });
        }
        if (p.error) {
          out.push({
            ...base,
            key: `${base.key}-err`,
            category: "problem",
            icon: "⚠️",
            title: String(p.error),
          });
        }
        if (p.translate_error) {
          out.push({
            ...base,
            key: `${base.key}-tr`,
            category: "problem",
            icon: "⚠️",
            title: `English translation failed: ${p.translate_error}`,
          });
        }
        break;
      }
      case "story_empty":
        out.push({
          ...base,
          category: "caller",
          icon: "🔇",
          title: "No speech heard in the story",
          muted: true,
        });
        break;
      case "readback":
        out.push({
          ...base,
          category: "understanding",
          icon: p.confirmed ? "✅" : "↩️",
          title: p.confirmed
            ? `Caller confirmed: ${name(String(p.confirmed))}`
            : "Caller said neither was right",
          subtitle: `pressed ${p.key} at the read-back`,
        });
        break;
      case "answer":
        out.push({
          ...base,
          category: "answers",
          icon: "📝",
          title: `${step(p)}: ${
            p.step === "occupation" || p.step === "trades"
              ? name(String(p.value))
              : value(String(p.value ?? ""))
          }`,
          subtitle: `key ${p.key}`,
        });
        break;
      case "skipped":
        out.push({
          ...base,
          category: "answers",
          icon: "⏭️",
          title: `${step(p)}: skipped after two tries`,
          muted: true,
        });
        break;
      case "consent":
        out.push({
          ...base,
          category: "answers",
          icon: p.granted ? "🟢" : "⚪",
          title: `${CONSENT[String(p.kind)] ?? p.kind}: ${p.granted ? "yes" : "no"}`,
          subtitle: "consent",
        });
        break;
      case "language":
        out.push({
          ...base,
          category: "answers",
          icon: "🌐",
          title: `Language: ${LANGUAGE[String(p.code)] ?? p.code}`,
        });
        break;
      case "keypad_only":
        out.push({
          ...base,
          category: "answers",
          icon: "⌨️",
          title: "No recording consent: keypad questions only",
        });
        break;
      case "human_flag":
        out.push({
          ...base,
          category: "answers",
          icon: "🧑‍💼",
          title: "Asked for a human officer",
          subtitle: `pressed 0 at ${step(p)}`,
        });
        break;
      case "summary":
        if (!hasSay) {
          out.push({
            ...base,
            category: "system",
            icon: "🔊",
            title: "Summary",
            lines: [{ text: String(p.text) }],
          });
        }
        break;
      case "problem":
        out.push({ ...base, category: "problem", icon: "⚠️", title: String(p.what) });
        break;
      case "inbound_call":
        out.push({ ...base, category: "call", icon: "📞", title: "Caller rang in; call connected" });
        break;
      case "answered":
        out.push({ ...base, category: "call", icon: "📞", title: "Our callback was answered" });
        break;
      case "call_ended":
        out.push({ ...base, category: "call", icon: "🏁", title: `Call ended after ${p.duration} s` });
        break;
      case "no_response":
        out.push({
          ...base,
          category: "call",
          icon: "📵",
          title: "Nobody answered the greeting",
          muted: true,
        });
        break;
      case "callback_requested":
        out.push({ ...base, category: "call", icon: "📅", title: "Callback requested for tomorrow" });
        break;
      case "callback_tomorrow":
        out.push({ ...base, category: "call", icon: "📅", title: "Caller asked to talk tomorrow" });
        break;
      case "provider_status":
        out.push({ ...base, category: "background", icon: "📡", title: `Exotel status: ${p.status}` });
        break;
      default:
        out.push({ ...base, category: "background", icon: "•", title: e.kind });
    }
  }
  return out;
}
