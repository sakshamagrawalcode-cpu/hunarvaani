// Splits a call's events into three streams for the call page:
// the conversation (what the system said, what the caller said or pressed), the processing
// going on in the background, and errors & warnings.

import type { CallEvent } from "./api";
import { CONSENT, LANGUAGE, STEP, value } from "./labels";

export type Row = {
  key: string;
  at: string;
  icon: string;
  title: string;
  who?: "system" | "caller";
  text?: string;
  meta?: string;
  chips?: string[];
  bars?: { label: string; score: number }[];
  tone?: "ok" | "warn" | "error" | "muted";
};

export type Streams = { conversation: Row[]; processing: Row[]; problems: Row[] };

type P = Record<string, unknown>;

const STOPPED: Record<string, string> = {
  silence: "stopped after silence",
  key: "caller pressed #",
  no_speech: "no speech heard",
  time_limit: "60 s limit reached",
  hangup: "caller hung up",
};

function stepName(s: unknown): string {
  const k = String(s ?? "");
  return STEP[k] ?? (k === "goodbye" ? "Goodbye" : k);
}

function ms(label: string, v: unknown): string | null {
  if (typeof v !== "number") return null;
  return `${label} ${v >= 1000 ? `${(v / 1000).toFixed(1)} s` : `${v} ms`}`;
}

// What a key press meant: the answer, consent, language or read-back saved right after it.
function meaning(events: CallEvent[], i: number, name: (c: string) => string): string | null {
  const step = String((events[i].payload ?? {}).step ?? "");
  for (let j = i + 1; j < events.length && j < i + 5; j++) {
    const e = events[j];
    const p = (e.payload ?? {}) as P;
    if (e.kind === "key" || e.kind === "say") return null;
    if (e.kind === "interest" && step === "options") {
      return p.rank ? `option ${p.rank}` : "none of these";
    }
    if (e.kind === "answer" && p.step === step) {
      return p.step === "occupation" || p.step === "trades"
        ? name(String(p.value))
        : value(String(p.value ?? ""));
    }
    if (e.kind === "consent" && step === `consent_${p.kind}`) return p.granted ? "yes" : "no";
    if (e.kind === "language" && step === "language") return LANGUAGE[String(p.code)] ?? String(p.code);
    if (e.kind === "readback") return p.confirmed ? `yes, ${name(String(p.confirmed))}` : "none of these";
    if (e.kind === "human_flag") return "asked for a human officer";
    if (e.kind === "callback_tomorrow") return "talk later";
  }
  if (step === "opening" || step === "safe_to_talk") return "continue";
  return null;
}

export function buildStreams(events: CallEvent[], name: (code: string) => string): Streams {
  const s: Streams = { conversation: [], processing: [], problems: [] };
  const hasSay = events.some((e) => e.kind === "say");
  events.forEach((e, i) => {
    const p = (e.payload ?? {}) as P;
    const base = { at: e.at, key: String(e.id ?? `${e.kind}-${i}`) };
    switch (e.kind) {
      case "say":
        if (((p.prompts as P[]) ?? [])[0]?.id === "P29") {
          const prev = (events[i - 1]?.payload ?? {}) as P;
          s.problems.push({
            ...base,
            key: `${base.key}-wrong`,
            icon: "🔢",
            title: `Wrong key${prev.digit ? ` ${prev.digit}` : ""} at “${stepName(p.step)}”`,
            text: "not one of the options; the question is asked again",
            tone: "warn",
          });
        }
        for (const [n, q] of ((p.prompts as P[]) ?? []).entries()) {
          const id = String(q.id ?? "");
          s.conversation.push({
            ...base,
            key: `${base.key}-${n}`,
            who: "system",
            icon: "🔊",
            title: stepName(p.step),
            text: q.text ? String(q.text) : "(generated sentence)",
            meta: id.startsWith("DYN:") ? "generated voice" : id.split("@")[0],
          });
        }
        if (p.beep) {
          s.conversation.push({
            ...base,
            key: `${base.key}-beep`,
            who: "system",
            icon: "🔔",
            title: "Beep",
            text: "recording starts",
            tone: "muted",
          });
        }
        break;
      case "summary":
        if (!hasSay)
          s.conversation.push({ ...base, who: "system", icon: "🔊", title: "Summary", text: String(p.text) });
        break;
      case "key": {
        const m = meaning(events, i, name);
        s.conversation.push({
          ...base,
          who: "caller",
          icon: "⌨️",
          title: stepName(p.step),
          text: `Pressed ${p.digit}${m ? `  →  ${m}` : ""}`,
        });
        break;
      }
      case "timeout":
        s.conversation.push({
          ...base,
          who: "caller",
          icon: "⏳",
          title: stepName(p.step),
          text: "No key pressed",
          tone: "muted",
        });
        s.problems.push({
          ...base,
          icon: "⏳",
          title: `No answer at “${stepName(p.step)}”`,
          text: "the question is asked again until the caller answers",
          tone: "warn",
        });
        break;
      case "recording":
        s.conversation.push({
          ...base,
          who: "caller",
          icon: "🎙️",
          title: "Work story",
          text: `Spoke for ${p.seconds} s`,
          meta: STOPPED[String(p.stopped_by)] ?? String(p.stopped_by ?? ""),
        });
        s.processing.push({
          ...base,
          icon: "💾",
          title: "Recording saved",
          text: `${p.seconds} s, ${STOPPED[String(p.stopped_by)] ?? p.stopped_by}`,
        });
        break;
      case "story_recorded": {
        if (p.transcript) {
          s.conversation.push({
            ...base,
            key: `${base.key}-said`,
            who: "caller",
            icon: "🗣️",
            title: "Caller said",
            text: `“${p.transcript}”`,
          });
        }
        const chips = [
          ms("speech-to-text", p.stt_ms),
          ms("English", p.translate_ms),
          ms("search", p.search_ms),
          ms("voice made", p.tts_ms),
          ms("caller waited", p.wait_ms),
        ].filter((c): c is string => Boolean(c));
        s.processing.push({
          ...base,
          key: `${base.key}-stt`,
          icon: "📝",
          title: "Speech-to-text (Sarvam)",
          text: p.transcript ? `“${p.transcript}”` : "no words recognised",
          chips,
        });
        const scores = (p.scores as P[]) ?? [];
        if (scores.length) {
          s.processing.push({
            ...base,
            key: `${base.key}-search`,
            icon: "🔎",
            title: "Occupation search",
            meta: "score out of 1.00 · 0.35 or more = confident",
            bars: scores.map((x) => ({
              label: x.title_en ? `${x.title_en} (${x.title_hi})` : name(String(x.code)),
              score: Number(x.score),
            })),
          });
        }
        if (p.translate_error)
          s.problems.push({
            ...base,
            key: `${base.key}-en`,
            icon: "🌐",
            title: "English translation failed",
            text: `searched the caller's own words only (${p.translate_error})`,
            tone: "warn",
          });
        if (p.error)
          s.problems.push({
            ...base,
            key: `${base.key}-err`,
            icon: "⛔",
            title: "Story processing failed",
            text: String(p.error),
            tone: "error",
          });
        break;
      }
      case "story_empty":
        s.conversation.push({
          ...base,
          who: "caller",
          icon: "🔇",
          title: "Work story",
          text: "No speech heard",
          tone: "muted",
        });
        s.problems.push({
          ...base,
          icon: "🔇",
          title: "No speech in the work story",
          text: "the caller is asked once more",
          tone: "warn",
        });
        break;
      case "readback":
        s.processing.push({
          ...base,
          icon: p.confirmed ? "✅" : "↩️",
          title: p.confirmed
            ? `Occupation confirmed: ${name(String(p.confirmed))}`
            : "Caller said none of the guesses was right",
          tone: p.confirmed ? "ok" : undefined,
        });
        break;
      case "answer":
        s.processing.push({
          ...base,
          icon: "💾",
          title: `Saved ${stepName(p.step).toLowerCase()}`,
          text:
            p.step === "occupation" || p.step === "trades"
              ? name(String(p.value))
              : value(String(p.value ?? "")),
        });
        break;
      case "consent":
        s.processing.push({
          ...base,
          icon: p.granted ? "🟢" : "⚪",
          title: "Consent saved",
          text: `${CONSENT[String(p.kind)] ?? p.kind}: ${p.granted ? "yes" : "no"}`,
        });
        break;
      case "language":
        s.processing.push({
          ...base,
          icon: "🌐",
          title: "Language set",
          text: LANGUAGE[String(p.code)] ?? String(p.code),
        });
        break;
      case "skipped":
        s.problems.push({
          ...base,
          icon: "⏭️",
          title: `Skipped “${stepName(p.step)}”`,
          text: "no valid answer after two tries",
          tone: "warn",
        });
        break;
      case "keypad_only":
        s.processing.push({
          ...base,
          icon: "⌨️",
          title: "Keypad-only mode",
          text: "no recording consent, so no spoken story",
        });
        break;
      case "human_flag":
        s.problems.push({
          ...base,
          icon: "🧑‍💼",
          title: "Caller asked for a human officer",
          text: `pressed 0 at “${stepName(p.step)}”`,
          tone: "warn",
        });
        break;
      case "problem":
        s.problems.push({ ...base, icon: "⛔", title: String(p.what), tone: "error" });
        break;
      case "inbound_call":
        s.processing.push({ ...base, icon: "📞", title: "Call connected", text: "caller rang in" });
        break;
      case "answered":
        s.processing.push({ ...base, icon: "📞", title: "Callback answered" });
        break;
      case "call_ended":
        s.processing.push({ ...base, icon: "🏁", title: "Call ended", text: `after ${p.duration} s` });
        break;
      case "no_response":
        s.problems.push({ ...base, icon: "📵", title: "Nobody answered the greeting", tone: "warn" });
        break;
      case "callback_tomorrow":
        s.processing.push({ ...base, icon: "📅", title: "Callback queued for tomorrow" });
        break;
      case "review":
        s.processing.push({
          ...base,
          icon: p.ok ? "✅" : "✏️",
          title: p.ok ? "Caller confirmed the saved answers" : `Caller changes “${stepName(p.change)}”`,
          tone: p.ok ? "ok" : undefined,
        });
        break;
      case "recommendations": {
        const options = (Array.isArray(p.options) ? p.options : []) as P[];
        s.processing.push({
          ...base,
          icon: "🎯",
          title: `${options.length} training option${options.length === 1 ? "" : "s"} found (sample data)`,
          text:
            options.map((o) => `${o.rank}. ${o.title}`).join(" · ") +
            (p.spoken ? "" : " (not said: no voice)"),
          tone: options.length ? "ok" : undefined,
        });
        break;
      }
      case "interest":
        s.processing.push({
          ...base,
          icon: p.rank ? "👍" : "✋",
          title: p.rank ? `Caller chose option ${p.rank}` : "Caller chose none of the options",
          tone: p.rank ? "ok" : undefined,
        });
        break;
      case "provider_status":
        s.processing.push({ ...base, icon: "📡", title: "Exotel status", text: String(p.status) });
        break;
      default:
        s.processing.push({ ...base, icon: "•", title: e.kind });
    }
  });
  return s;
}
