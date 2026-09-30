const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fs = require("fs");
const QRCode = require("qrcode");
const si = require("simple-icons");
const fa = require("react-icons/fa6");

const MEDIA = "/tmp/claude-0/-home-user-hunarvaani/1a479c87-c527-500c-a3b9-10fb2a163850/scratchpad/ppt/sc/ppt/media/";
const LOGO_SMALL = MEDIA + "image-1-1.png"; // SIH 2026 logo (from the official title page)
const LOGO_BIG = MEDIA + "image-1-2.png";
const TEAM = "Cognify";

// palette
const NAVY = "1B2A4A", SAFFRON = "E8772E", TEAL = "0F766E", INK = "1F2937", MUTED = "6B7280";
const LINE = "E5E7EB", WHITE = "FFFFFF", RED = "C2410C", GREEN = "15803D";
const TINT = { saffron: "FFF1E6", teal: "E6F4F1", blue: "EAF0FB", purple: "F1ECFB", gray: "F5F6F8", green: "EAF6EE" };
const ACC = { saffron: SAFFRON, teal: TEAL, blue: "2F5DA8", purple: "6D4AB8", gray: "4B5563", green: GREEN };
const HEAD = "Cambria", BODY = "Calibri";

async function iconPng(Icon, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}
async function brandPng(icon) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256"><path fill="#${icon.hex}" d="${icon.path}"/></svg>`;
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

const shadow = () => ({ type: "outer", color: "000000", blur: 4, offset: 1.5, angle: 90, opacity: 0.12 });

function card(s, x, y, w, h, fill, opts = {}) {
  s.addShape("roundRect", {
    x, y, w, h, fill: { color: fill }, rectRadius: 0.08,
    line: { color: opts.line || fill, width: opts.line ? 0.75 : 0 },
    shadow: opts.shadow === false ? undefined : shadow(),
  });
}
async function iconCircle(s, Icon, x, y, d, color) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 } });
  const pad = d * 0.24;
  s.addImage({ data: await iconPng(Icon, WHITE), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad });
}
function text(s, t, o) {
  s.addText(t, Object.assign({ isTextBox: true, fontFace: BODY, color: INK, margin: 0, valign: "top" }, o));
}
function bandLabel(s, label, sub, y, color = TEAL) {
  text(s, [
    { text: label, options: { bold: true, color, charSpacing: 1.5 } },
    { text: "   " + sub, options: { italic: true, color: MUTED } },
  ], { x: 0.3, y, w: 9.4, h: 0.24, fontSize: 10.5, valign: "middle" });
}

function header(s, title, sub, n) {
  // team name in an oval, top-left (as in the SIH template)
  s.addShape("ellipse", { x: 0.25, y: 0.16, w: 1.3, h: 0.5, fill: { color: WHITE }, line: { color: NAVY, width: 1.25 } });
  text(s, TEAM, { x: 0.25, y: 0.16, w: 1.3, h: 0.5, fontSize: 12, bold: true, color: NAVY, align: "center", valign: "middle" });
  text(s, title, { x: 1.7, y: 0.1, w: 6.1, h: 0.46, fontSize: 22, bold: true, color: NAVY, fontFace: HEAD, align: "center", valign: "middle" });
  text(s, sub, { x: 1.7, y: 0.55, w: 6.1, h: 0.3, fontSize: 10.5, italic: true, color: MUTED, align: "center", valign: "middle" });
  s.addImage({ path: LOGO_SMALL, x: 7.98, y: 0.1, w: 1.72, h: 0.81 });
  // path motif: five dots, this slide's dot lit
  for (let i = 0; i < 5; i++) {
    const on = i === n - 2;
    s.addShape("ellipse", { x: 0.32 + i * 0.22, y: 5.36, w: on ? 0.12 : 0.08, h: on ? 0.12 : 0.08, fill: { color: on ? SAFFRON : "D1D5DB" }, line: { color: on ? SAFFRON : "D1D5DB", width: 0 } });
    if (i < 4) s.addShape("line", { x: 0.44 + i * 0.22, y: 5.42, w: 0.1, h: 0, line: { color: "D1D5DB", width: 0.75, dashType: "dash" } });
  }
  text(s, "HunarMarg", { x: 1.45, y: 5.3, w: 1.2, h: 0.22, fontSize: 9, bold: true, color: MUTED, valign: "middle" });
  text(s, String(n), { x: 9.3, y: 5.28, w: 0.4, h: 0.24, fontSize: 11, bold: true, color: NAVY, align: "right", valign: "middle" });
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "HunarMarg · SIH26097";

  // ---------- Slide 1: official title page ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    text(s, "SMART INDIA HACKATHON 2026", { x: 0.45, y: 0.2, w: 7.4, h: 0.6, fontSize: 30, bold: true, color: "1F4E79", fontFace: "Times New Roman", valign: "middle" });
    s.addImage({ path: LOGO_SMALL, x: 7.9, y: 0.08, w: 1.85, h: 0.87 });
    text(s, "TITLE PAGE", { x: 2.4, y: 0.95, w: 3.5, h: 0.45, fontSize: 22, bold: true, color: "111827", fontFace: "Times New Roman", align: "center", valign: "middle" });
    s.addImage({ path: LOGO_BIG, x: 5.35, y: 1.9, w: 4.4, h: 2.08 });
    const row = (k, v, vc = "1F4E79", last = false) => [
      { text: k, options: { bold: true, color: "1F2937", fontSize: 14, bullet: true } },
      { text: v, options: { bold: true, color: vc, fontSize: 12.5, breakLine: !last } },
    ];
    text(s, [
      ...row("Problem Statement ID – ", "SIH26097"),
      ...row("Problem Statement Title – ", "AI-driven voice assistant for livelihood mapping and NSQF-aligned skilling recommendations for SC communities under the GIA component of PM-AJAY"),
      ...row("Theme – ", "Agriculture, FoodTech & Rural Development"),
      ...row("PS Category – ", "Software"),
      ...row("Team ID – ", "________  (fill from the SIH portal)", "D64545"),
      ...row("Team Name (Registered on portal) – ", TEAM, "1F4E79", true),
    ], { x: 0.45, y: 1.6, w: 4.8, h: 3.7, fontFace: "Arial", paraSpaceAfter: 7 });
    s.addNotes("Official SIH 2026 title page, unchanged. Fill the Team ID (and check the team name) from the SIH portal before exporting to PDF.");
  }

  // ---------- Slide 2: proposed solution ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, "HunarMarg", "Proposed solution  ·  one free phone call from skill to a verified livelihood", 2);

    // Band 1: problem
    card(s, 0.3, 1.0, 5.2, 0.9, TINT.saffron);
    await iconCircle(s, fa.FaFileCircleXmark, 0.45, 1.13, 0.46, SAFFRON);
    text(s, [
      { text: "THE PROBLEM   ", options: { bold: true, color: SAFFRON, fontSize: 9, charSpacing: 1.5, breakLine: true } },
      { text: "A form picks the course, not the person", options: { bold: true, color: NAVY, fontSize: 15, breakLine: true } },
      { text: "so SC job seekers land in training that was never going to fit them.", options: { color: INK, fontSize: 10 } },
    ], { x: 1.05, y: 1.08, w: 4.35, h: 0.78 });
    const stats = [
      ["41%", "of certified trainees got placed", "CAG 2025 [S5]", TINT.saffron, SAFFRON],
      ["51.6%", "of rural women have no phone of their own", "NSO 2025 [S2]", TINT.purple, ACC.purple],
      ["66.1%", "SC literacy: forms fail many people", "Census 2011 [S1]", TINT.blue, ACC.blue],
    ];
    stats.forEach(([n, l, src, bg, fg], i) => {
      const x = 5.65 + i * 1.4;
      card(s, x, 1.0, 1.3, 0.9, bg);
      text(s, n, { x: x + 0.1, y: 1.04, w: 1.1, h: 0.36, fontSize: 20, bold: true, color: fg, valign: "middle" });
      text(s, l, { x: x + 0.1, y: 1.4, w: 1.12, h: 0.3, fontSize: 8, color: INK });
      text(s, src, { x: x + 0.1, y: 1.7, w: 1.12, h: 0.16, fontSize: 7, color: MUTED });
    });

    // Band 2: solution, five steps
    bandLabel(s, "THE SOLUTION", "one free call on any keypad phone, guided end to end", 2.02);
    const steps = [
      [fa.FaPhoneVolume, "Missed call, free callback", "from a govt 1600 number*", "Within a minute, in the caller's language. No app, no internet, no reading.", "blue"],
      [fa.FaKeyboard, "Keys + own words", "keys for facts, voice for skills", "Age, education, distance by keypad; then they describe their work.", "teal"],
      [fa.FaIdCard, "AI builds a full profile", "read back; caller presses 1", "Skills mapped to NCO codes and NSQF qualifications. No paper.", "purple"],
      [fa.FaBullseye, "3 pathways that fit", "each with a plan + money path", "Training, RPL certificate, apprenticeship or own work, near home.", "green"],
      [fa.FaCalendarCheck, "Stays till they earn", "SMS, reminders, follow-ups", "Case ID + documents by SMS; calls at 1, 3 and 6 months.", "saffron"],
    ];
    for (let i = 0; i < steps.length; i++) {
      const [Ic, t, sub, body, c] = steps[i];
      const x = 0.3 + i * 1.9;
      card(s, x, 2.3, 1.8, 1.3, TINT[c]);
      await iconCircle(s, Ic, x + 0.1, 2.38, 0.38, ACC[c]);
      s.addShape("ellipse", { x: x + 1.45, y: 2.42, w: 0.26, h: 0.26, fill: { color: WHITE }, line: { color: ACC[c], width: 1 } });
      text(s, String(i + 1), { x: x + 1.45, y: 2.42, w: 0.26, h: 0.26, fontSize: 10, bold: true, color: ACC[c], align: "center", valign: "middle" });
      text(s, t, { x: x + 0.1, y: 2.8, w: 1.62, h: 0.2, fontSize: 10, bold: true, color: NAVY });
      text(s, sub, { x: x + 0.1, y: 3.0, w: 1.62, h: 0.18, fontSize: 8, italic: true, color: ACC[c] });
      text(s, body, { x: x + 0.1, y: 3.18, w: 1.62, h: 0.4, fontSize: 8, color: INK });
    }

    // Band 3: why it works
    bandLabel(s, "WHY IT WORKS WHERE A FORM FAILS", "six things only HunarMarg does", 3.7);
    const why = [
      [fa.FaMobileScreen, "Any keypad phone", "missed call, free, in their own language", "blue"],
      [fa.FaDatabase, "Never invented", "every fact from govt data, checked before it is spoken", "teal"],
      [fa.FaPenToSquare, "Writes the profile itself", "officers only review and approve", "purple"],
      [fa.FaIndianRupeeSign, "Money path", "which loan or grant fits, and the monthly EMI", "green"],
      [fa.FaShieldHalved, "Outcomes that can't be faked", "random-digit liveness check + employer check", "saffron"],
      [fa.FaBrain, "Learns from verified jobs only", "fake placements can't teach it", "gray"],
    ];
    for (let i = 0; i < why.length; i++) {
      const [Ic, t, sub, c] = why[i];
      const x = 0.3 + (i % 3) * 3.17, y = 3.98 + Math.floor(i / 3) * 0.64;
      card(s, x, y, 3.07, 0.56, WHITE, { line: LINE });
      await iconCircle(s, Ic, x + 0.1, y + 0.1, 0.36, ACC[c]);
      text(s, [
        { text: t, options: { bold: true, color: NAVY, fontSize: 10, breakLine: true } },
        { text: sub, options: { color: MUTED, fontSize: 8.5 } },
      ], { x: x + 0.56, y: y + 0.07, w: 2.45, h: 0.44, valign: "middle" });
    }
    text(s, "* needs a government MoU", { x: 6.9, y: 5.3, w: 2.3, h: 0.22, fontSize: 7.5, italic: true, color: MUTED, align: "right", valign: "middle" });
    s.addNotes("Three bands: the problem (one card, three numbers), the solution (one call, five steps, end to end), and why it works where a form fails (six points). Keys carry facts so speech errors cannot hurt; the AI writes the full profile for officers; every option comes with a plan and a money path; follow-ups continue until the person is earning, and only verified outcomes teach the ranker. The 1600 number needs a government MoU.");
  }

  // ---------- Slide 3: technical approach ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, "Technical Approach", "Indian, open-source models, fine-tuned by us, running on Indian servers", 3);

    bandLabel(s, "TECH STACK", "Indian and open-source, fine-tuned by us", 0.98);
    const groups = [
      [fa.FaTowerBroadcast, "Calls & messages", "Exotel · 1600 number* · SMS", "blue"],
      [fa.FaBrain, "AI models (fine-tuned)", "IndicConformer · Indic Parler-TTS · Sarvam-30B · MuRIL · e5 · LightGBM · Satyavaani", "purple"],
      [fa.FaServer, "Backend & data", null, "teal"],
      [fa.FaLandmark, "Apps & govt links", "React console · NCO-2015 · NQR · DigiLocker* · AJAY app*", "saffron"],
    ];
    const gw = [2.0, 2.95, 2.15, 2.0];
    let gx = 0.3;
    for (let i = 0; i < groups.length; i++) {
      const [Ic, t, body, c] = groups[i];
      card(s, gx, 1.25, gw[i], 0.58, TINT[c], { shadow: false });
      await iconCircle(s, Ic, gx + 0.08, 1.33, 0.26, ACC[c]);
      text(s, t, { x: gx + 0.4, y: 1.3, w: gw[i] - 0.45, h: 0.18, fontSize: 8.5, bold: true, color: ACC[c] });
      if (body) {
        text(s, body, { x: gx + 0.4, y: 1.48, w: gw[i] - 0.48, h: 0.32, fontSize: 7.5, color: INK });
      } else {
        const logos = [si.siPython, si.siFastapi, si.siPostgresql, si.siRedis, si.siDocker, si.siReact];
        for (let j = 0; j < logos.length; j++) {
          s.addImage({ data: await brandPng(logos[j]), x: gx + 0.42 + j * 0.28, y: 1.5, w: 0.2, h: 0.2 });
        }
        text(s, "+ pgvector · Indian GPU cloud", { x: gx + 0.4, y: 1.7, w: gw[i] - 0.45, h: 0.12, fontSize: 6.5, color: MUTED });
      }
      gx += gw[i] + 0.1;
    }

    bandLabel(s, "HOW IT WORKS", "two lanes: during the call (AI, seconds) and after it (people, days)", 1.93);
    async function lane(y, h, tag, sub, color, boxes) {
      card(s, 0.3, y, 1.0, h, color, { shadow: false });
      text(s, [
        { text: tag, options: { bold: true, color: WHITE, fontSize: 9, breakLine: true } },
        { text: sub, options: { color: WHITE, fontSize: 7.5 } },
      ], { x: 0.36, y, w: 0.9, h, valign: "middle" });
      const x0 = 1.42, avail = 9.7 - x0, gap = 0.14, bw = (avail - gap * (boxes.length - 1)) / boxes.length;
      for (let i = 0; i < boxes.length; i++) {
        const [Ic, t, b] = boxes[i];
        const x = x0 + i * (bw + gap);
        card(s, x, y, bw, h, WHITE, { line: LINE, shadow: false });
        s.addImage({ data: await iconPng(Ic, color), x: x + 0.06, y: y + 0.07, w: 0.18, h: 0.18 });
        text(s, t, { x: x + 0.28, y: y + 0.05, w: bw - 0.32, h: 0.22, fontSize: 8, bold: true, color: NAVY, valign: "middle" });
        text(s, b, { x: x + 0.06, y: y + 0.28, w: bw - 0.1, h: h - 0.3, fontSize: 7, color: MUTED });
        if (i < boxes.length - 1) s.addShape("rightArrow", { x: x + bw + 0.015, y: y + h / 2 - 0.05, w: 0.11, h: 0.1, fill: { color: color }, line: { color: color, width: 0 } });
      }
    }
    await lane(2.2, 0.62, "① During the call", "seconds · keys instant", ACC.purple, [
      [fa.FaPhoneVolume, "Phone → Exotel", "missed call, callback, keys"],
      [fa.FaMicrophone, "IndicConformer", "speech → text"],
      [fa.FaBrain, "MuRIL + Sarvam-30B", "fill the profile form, job codes only"],
      [fa.FaMagnifyingGlass, "e5 + BM25", "find the NCO job"],
      [fa.FaCircleCheck, "“You said…”", "caller confirms with 1"],
      [fa.FaScaleBalanced, "LightGBM ranker", "on govt data: courses, centres, schemes"],
      [fa.FaVolumeHigh, "Parler-TTS speaks", "facts checked, then 3 options"],
    ]);
    await lane(2.94, 0.56, "② After the call", "days · people", ACC.teal, [
      [fa.FaIdCard, "Profile → case", "FastAPI + PostgreSQL, audit log"],
      [fa.FaCommentSms, "SMS", "case ID + documents list"],
      [fa.FaUserCheck, "Officer approves*", "team console / AJAY app"],
      [fa.FaCalendarCheck, "Follow-ups 1·3·6 mo", "+ Satyavaani liveness check"],
      [fa.FaChartLine, "Verified outcomes", "ranker retrained monthly"],
    ]);
    text(s, [
      { text: "AI understands  →  data and rules decide  →  facts checked  →  humans approve", options: { bold: true, color: NAVY } },
      { text: "      GPU down → Sarvam API  ·  AI stuck → human counsellor", options: { italic: true, color: MUTED, fontSize: 8 } },
    ], { x: 0.3, y: 3.56, w: 9.4, h: 0.22, fontSize: 9.5, align: "center", valign: "middle" });

    bandLabel(s, "OUR MODELS", "what each one does, how we train it, the bar it must pass", 3.84);
    const models = [
      ["IndicConformer-600M", "Hindi error ≤ 20%", "22 languages; 8 kHz phone audio → text", "100 h consented calls per language + IndicVoices · ~72 GPU-h"],
      ["Indic Parler-TTS", "listeners ≥ 4/5", "21 languages; text + “calm, clear voice” → speech", "12 h of one local voice artist per language · ~24 GPU-h"],
      ["Sarvam-30B", "right job in top 3 ≥ 90%", "fills a fixed form: job codes, years, skills; never advises", "LoRA on 5,000 checked story → form pairs · ~16 GPU-h"],
      ["multilingual-e5 + BM25", "right job in top 5 ≥ 90%", "keyword + meaning score → top 20 → reranker → top 3", "every “1” at read-back = right pair, “none” = wrong pair"],
      ["LightGBM LambdaRank", "gender gap ≤ 5 pts", "filters, then 6 factors: wish, skills, demand, reach, finish, pay", "officer-set weights (AHP) first; then verified jobs at 6 months only"],
      ["Satyavaani (team's own)", "flags, never rejects", "4 random digits + fake-voice score; no voiceprint stored", "Indian phone speech + 3 voice-cloning tools"],
    ];
    models.forEach(([name, target, works, trains], i) => {
      const x = 0.3 + (i % 3) * 3.17, y = 4.12 + Math.floor(i / 3) * 0.6;
      card(s, x, y, 3.07, 0.54, TINT.gray, { shadow: false });
      text(s, name, { x: x + 0.1, y: y + 0.04, w: 1.75, h: 0.18, fontSize: 9, bold: true, color: NAVY });
      text(s, target, { x: x + 1.7, y: y + 0.04, w: 1.3, h: 0.18, fontSize: 7.5, bold: true, color: SAFFRON, align: "right" });
      text(s, [
        { text: "Works: ", options: { bold: true, color: TEAL } }, { text: works, options: { breakLine: true } },
        { text: "Trains: ", options: { bold: true, color: ACC.purple } }, { text: trains },
      ], { x: x + 0.1, y: y + 0.22, w: 2.9, h: 0.3, fontSize: 7, color: INK });
    });
    text(s, "No Aadhaar number stored · caste never asked · consent logged (DPDP Rules 2025) · raw audio deleted after confirmation · data stays in India · * needs a govt MoU",
      { x: 2.6, y: 5.3, w: 6.6, h: 0.22, fontSize: 7, italic: true, color: MUTED, align: "center", valign: "middle" });
    s.addNotes("During the call: Exotel handles the missed call, callback and keys; IndicConformer turns speech into text; MuRIL tags the words and Sarvam-30B fills a fixed profile form using only job codes from our list; e5 + BM25 find the NCO occupation; the caller confirms the read-back; the LightGBM ranker picks 3 options from government data; every fact is checked before Indic Parler-TTS speaks it. If a GPU fails the Sarvam API takes over; if the AI is stuck a human counsellor calls back. After the call: the profile becomes a case, the caller gets an SMS, an officer approves, follow-ups at 1, 3 and 6 months use Satyavaani, and only verified outcomes retrain the ranker. All models are open-source Indian models that we fine-tune; details in docs/MODELS.md.");
  }

  // ---------- Slide 4: feasibility ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, "Feasibility and Viability", "Can it be built and run? Yes: every part already runs in India, and it costs 0.24% of GIA per person.", 4);

    bandLabel(s, "ALREADY WORKING IN INDIA", "nothing here is untested", 0.98);
    const proof = [
      ["22 crore", "feature-phone users", "The channel already exists.", "Business Standard 2026 [S11]", "blue"],
      ["3 crore+", "reached by Kilkari", "A govt voice-call line; answers rise 50% → 76% by the 3rd try.", "BMJ Global Health [S12]", "purple"],
      ["22 · 21", "languages, open models", "Indian speech (IndicConformer) and voice (Parler-TTS) models exist.", "AI4Bharat [S15]", "teal"],
      ["19.3%", "speech error to beat", "Best Indian speech AI on IndicVoices; we switch only after beating it.", "Sarvam 2026 [S14]", "saffron"],
      ["Prototype", "works on real calls", "3 languages, profile + read-back, top 3 from 115 courses, 124 centres.", "GitHub [S21]", "green"],
    ];
    proof.forEach(([n, l, b, src, c], i) => {
      const x = 0.3 + i * 1.9;
      card(s, x, 1.26, 1.8, 1.0, TINT[c]);
      text(s, n, { x: x + 0.1, y: 1.3, w: 1.6, h: 0.32, fontSize: 17, bold: true, color: ACC[c], valign: "middle" });
      text(s, l, { x: x + 0.1, y: 1.62, w: 1.6, h: 0.16, fontSize: 8.5, bold: true, color: NAVY });
      text(s, b, { x: x + 0.1, y: 1.79, w: 1.62, h: 0.3, fontSize: 7.5, color: INK });
      text(s, src, { x: x + 0.1, y: 2.08, w: 1.6, h: 0.14, fontSize: 6.5, color: MUTED });
    });

    bandLabel(s, "WHAT IT COSTS", "four final numbers; every rate is in the calculations", 2.36);
    const costs = [
      ["₹163", "per person, all-in", "at 50,000 people a year", "saffron"],
      ["0.24%", "of GIA support per person", "₹163 of ₹69,200 [S3]", "teal"],
      ["₹8.8 L", "a year of GPUs in India", "2× L4 + 1× L40S [S17]", "blue"],
      ["₹2 L", "one time per language", "100 h data + voice + GPU", "purple"],
    ];
    costs.forEach(([n, l, sub, c], i) => {
      const x = 0.3 + (i % 2) * 2.3, y = 2.64 + Math.floor(i / 2) * 0.66;
      card(s, x, y, 2.2, 0.58, TINT[c]);
      text(s, n, { x: x + 0.1, y: y + 0.05, w: 0.95, h: 0.48, fontSize: 18, bold: true, color: ACC[c], valign: "middle" });
      text(s, [
        { text: l, options: { bold: true, color: NAVY, fontSize: 8.5, breakLine: true } },
        { text: sub, options: { color: MUTED, fontSize: 7.5 } },
      ], { x: x + 1.05, y: y + 0.05, w: 1.12, h: 0.48, valign: "middle" });
    });
    // training strip
    const tsteps = ["Collect 100 h", "Fine-tune ~112 GPU-h", "Beat 19.3%", "Improve monthly"];
    tsteps.forEach((t, i) => {
      const x = 0.3 + i * 1.15;
      s.addShape("roundRect", { x, y: 3.98, w: 1.02, h: 0.26, fill: { color: WHITE }, line: { color: TEAL, width: 0.75 }, rectRadius: 0.06 });
      text(s, t, { x, y: 3.98, w: 1.02, h: 0.26, fontSize: 7.5, bold: true, color: TEAL, align: "center", valign: "middle" });
      if (i < 3) s.addShape("rightArrow", { x: x + 1.03, y: 4.06, w: 0.1, h: 0.1, fill: { color: TEAL }, line: { color: TEAL, width: 0 } });
    });
    // chart
    card(s, 5.0, 2.64, 4.7, 1.6, WHITE, { line: LINE, shadow: false });
    s.addChart(pres.charts.BAR, [
      { name: "Our own models", labels: ["50,000", "1 lakh", "5 lakh", "10 lakh"], values: [163, 94, 39, 32] },
      { name: "Paid APIs", labels: ["50,000", "1 lakh", "5 lakh", "10 lakh"], values: [121, 73, 35, 30] },
    ], {
      x: 5.05, y: 2.66, w: 4.6, h: 1.56, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
      chartColors: [SAFFRON, "CBD5E1"],
      showTitle: true, title: "Cost per person (₹) falls as more people call (people a year)", titleFontSize: 8.5, titleColor: NAVY, titleFontFace: BODY,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 7, dataLabelColor: INK,
      catAxisLabelFontSize: 7.5, catAxisLabelColor: MUTED, valAxisHidden: true,
      valGridLine: { style: "none" }, catGridLine: { style: "none" },
      showLegend: true, legendPos: "r", legendFontSize: 7, legendColor: MUTED,
    });

    bandLabel(s, "WHAT COULD GO WRONG, AND WHAT ALREADY HANDLES IT", "", 4.33, SAFFRON);
    const risks = [
      ["Village dialects", "keys for facts, every answer read back, human fallback"],
      ["AI says something wrong", "only facts that match a govt data row are spoken"],
      ["Unknown numbers ignored", "they call first; callback from an official 1600 number*"],
      ["Our model worse than APIs", "switch a language only after it beats 19.3%; API backup"],
    ];
    const xIcon = await iconPng(fa.FaCircleXmark, RED), cIcon = await iconPng(fa.FaCircleCheck, GREEN);
    risks.forEach(([r, f], i) => {
      const x = 0.3 + (i % 2) * 4.75, y = 4.6 + Math.floor(i / 2) * 0.32;
      s.addImage({ data: xIcon, x, y: y + 0.04, w: 0.16, h: 0.16 });
      text(s, r, { x: x + 0.2, y, w: 1.45, h: 0.24, fontSize: 8.5, bold: true, color: RED, valign: "middle" });
      s.addImage({ data: cIcon, x: x + 1.65, y: y + 0.04, w: 0.16, h: 0.16 });
      text(s, f, { x: x + 1.85, y, w: 2.8, h: 0.24, fontSize: 8.5, color: INK, valign: "middle" });
    });
    s.addNotes("Proof that each piece already runs in India, then four final numbers. Costs come from scripts/cost_model.py: phone minutes, API cost and team budget from our v4 research; GPU prices from E2E Networks (L4 Rs 49/h, L40S Rs 102/h); GPUs run 12 hours a day. At 50,000 people a year our own models cost Rs 163 per person (Rs 159-172 for carrier rates Rs 0.60-1.20 a minute) against Rs 121 on paid APIs; at 10 lakh people it is Rs 32 against Rs 30. We run our own models for 22 languages, dialect tuning and data control, not to save money. Calls each GPU can serve are estimates to be confirmed by a load test.");
  }

  // ---------- Slide 5: impact ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, "Impact and Benefits", "Who gains? SC families, officers, training centres and the Ministry.", 5);

    bandLabel(s, "WHAT CHANGES", "four numbers, each with its source", 0.98);
    const impact = [
      ["41% → 70%", "placed after training", "CAG found 41% placed; 70% is the GIA target. Courses that fit close the gap.", "CAG 2025 [S5] · PM-AJAY [S4]", "saffron", [41, 70]],
      ["62% → 73%", "stay in the job", "when trainees hear real pay and place before joining; HunarMarg says it on the call.", "J-PAL field trial [S13]", "teal", [62, 73]],
      ["109 min", "officer time saved per person", "≈ 52 staff-years a year: the AI writes the profile, officers approve.", "our estimate", "blue", null],
      ["₹44,136", "saved on one loan", "on a woman's ₹80,000 tailoring unit, with the right grant + loan path.", "our calculation", "purple", null],
    ];
    impact.forEach(([n, l, b, src, c, bar], i) => {
      const x = 0.3 + i * 2.37;
      card(s, x, 1.26, 2.27, 1.5, TINT[c]);
      text(s, n, { x: x + 0.12, y: 1.32, w: 2.05, h: 0.4, fontSize: 21, bold: true, color: ACC[c], valign: "middle" });
      text(s, l, { x: x + 0.12, y: 1.72, w: 2.05, h: 0.18, fontSize: 9, bold: true, color: NAVY });
      if (bar) {
        const bx = x + 0.12, bw = 2.02, by = 1.95;
        s.addShape("roundRect", { x: bx, y: by, w: bw, h: 0.09, fill: { color: WHITE }, line: { color: WHITE, width: 0 }, rectRadius: 0.04 });
        s.addShape("roundRect", { x: bx, y: by, w: bw * bar[0] / 100, h: 0.09, fill: { color: "9CA3AF" }, line: { color: "9CA3AF", width: 0 }, rectRadius: 0.04 });
        s.addShape("line", { x: bx + bw * bar[1] / 100, y: by - 0.04, w: 0, h: 0.17, line: { color: ACC[c], width: 2 } });
      }
      text(s, b, { x: x + 0.12, y: bar ? 2.1 : 1.95, w: 2.05, h: 0.45, fontSize: 8, color: INK });
      text(s, src, { x: x + 0.12, y: 2.56, w: 2.05, h: 0.16, fontSize: 7, color: MUTED });
    });

    card(s, 0.3, 2.88, 9.4, 0.42, TINT.gray, { shadow: false });
    await iconCircle(s, fa.FaUsers, 0.4, 2.93, 0.32, NAVY);
    text(s, [
      { text: "~50,000", options: { bold: true, color: SAFFRON, fontSize: 13 } },
      { text: " GIA beneficiaries a year [S3]      ", options: { color: INK } },
      { text: "47,000+", options: { bold: true, color: SAFFRON, fontSize: 13 } },
      { text: " SC-majority villages already on the PM-AJAY dashboard [S10]", options: { color: INK } },
    ], { x: 0.85, y: 2.88, w: 8.8, h: 0.42, fontSize: 9.5, valign: "middle" });

    bandLabel(s, "WHO GAINS WHAT", "social · economic · governance · environment", 3.42);
    const gains = [
      [fa.FaHandshake, "Social", "SC families, women, non-readers", "Right course the first time, free, in their own language; women-only batches; calls until they earn.", "saffron"],
      [fa.FaIndianRupeeSign, "Economic", "the Ministry and the trainee", "0.24% extra per person makes sure the other 99.76% buys the right course; the cheapest loan path.", "teal"],
      [fa.FaLandmark, "Governance", "officers and CSC operators", "Ready profiles, one case record from call to job, block-level demand for the annual plan.", "blue"],
      [fa.FaLeaf, "Environment", "every district office", "No paper forms, fewer trips to offices, runs on Indian cloud.", "green"],
    ];
    for (let i = 0; i < gains.length; i++) {
      const [Ic, t, who, b, c] = gains[i];
      const x = 0.3 + i * 2.37;
      card(s, x, 3.7, 2.27, 1.45, WHITE, { line: LINE });
      await iconCircle(s, Ic, x + 0.12, 3.8, 0.42, ACC[c]);
      text(s, [
        { text: t, options: { bold: true, color: NAVY, fontSize: 11, breakLine: true } },
        { text: who, options: { italic: true, color: ACC[c], fontSize: 8 } },
      ], { x: x + 0.62, y: 3.8, w: 1.6, h: 0.42, valign: "middle" });
      text(s, b, { x: x + 0.12, y: 4.3, w: 2.05, h: 0.8, fontSize: 8.5, color: INK });
    }
    text(s, "Pilot: 6–8 blocks, ~540 people per group, results in 6 months", { x: 2.6, y: 5.3, w: 6.2, h: 0.22, fontSize: 8.5, bold: true, color: TEAL, align: "center", valign: "middle" });
    s.addNotes("CAG Report No. 20 of 2025: of 56 lakh certified PMKVY trainees, 41% were placed; the GIA target is 70%. J-PAL (Chakravorty et al., DDU-GKY in Bihar and Jharkhand): trainees told about real jobs were 11 points more likely to stay 5+ months (62% to 73%). 109 minutes of staff time per person and Rs 44,136 on Sunita's Rs 80,000 tailoring unit are our own estimates from the v4 idea file. Reach: about 50,000 GIA beneficiaries a year; the PM-AJAY dashboard already covers 47,000+ SC-majority villages.");
  }

  // ---------- Slide 6: references ----------
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, "Research and References", "Every number in this deck, with where it came from", 6);

    bandLabel(s, "SOURCES", "by type, each with its website", 0.98);
    const cols = [
      [fa.FaLandmark, "Government data", "blue", [
        "S1 Census 2011 (MoSJE Handbook 2021): SC literacy 66.1% · socialjustice.gov.in",
        "S2 NSO Telecom survey 2025: phone ownership · mospi.gov.in",
        "S3 MoSJE PM-AJAY factsheet, 28 Sep 2026: ₹1,730 cr, 2.5 lakh people · pib.gov.in",
        "S4 PM-AJAY guidelines: 70% placement, 30% women · socialjustice.gov.in",
        "S5 CAG Report No. 20 of 2025: 41% placed · cag.gov.in",
        "S6 NCO-2015 · S7 NQR / NCVET · S8 NSFDC · S9 PIB PM Vishwakarma",
        "S10 PIB: PM-AJAY portal + AJAY app, 26 May 2026 · pib.gov.in",
      ]],
      [fa.FaFlask, "Research", "purple", [
        "S11 Business Standard, Apr 2026: 22 crore feature-phone users",
        "S12 BMJ Global Health: Kilkari reach and answer rates · gh.bmj.com",
        "S13 Chakravorty et al., J-PAL: job information → retention 62% → 73% · povertyactionlab.org",
      ]],
      [fa.FaMicrochip, "Technology", "teal", [
        "S14 Sarvam: Saaras v3, 19.31% WER on IndicVoices · sarvam.ai",
        "S15 AI4Bharat: IndicConformer, IndicVoices, Indic Parler-TTS · huggingface.co/ai4bharat",
        "S16 Sarvam-30B open weights, Apache 2.0 · huggingface.co/sarvamai",
        "S17 E2E Networks: L4 ₹49/h, L40S ₹102/h · e2enetworks.com",
        "S18 Sarvam API pricing; carrier rate cards (team research)",
      ]],
      [fa.FaScaleBalanced, "Policy & our work", "saffron", [
        "S19 DPDP Rules 2025 (14 Nov 2025) · meity.gov.in",
        "S20 TRAI 1600 series for govt-to-citizen calls · trai.gov.in",
        "S21 Our work: prototype code, MODELS.md, cost_model.py, measure.py · GitHub",
      ]],
    ];
    const cw = [2.75, 2.05, 2.5, 1.8];
    let cx = 0.3;
    for (let i = 0; i < cols.length; i++) {
      const [Ic, t, c, items] = cols[i];
      card(s, cx, 1.26, cw[i], 2.8, TINT[c], { shadow: false });
      await iconCircle(s, Ic, cx + 0.1, 1.34, 0.3, ACC[c]);
      text(s, t, { x: cx + 0.48, y: 1.34, w: cw[i] - 0.55, h: 0.3, fontSize: 10, bold: true, color: ACC[c], valign: "middle" });
      text(s, items.map((it, j) => ({ text: it, options: { bullet: { indent: 9 }, breakLine: j < items.length - 1 } })),
        { x: cx + 0.1, y: 1.72, w: cw[i] - 0.18, h: 2.3, fontSize: 7.5, color: INK, paraSpaceAfter: 4 });
      cx += cw[i] + 0.1;
    }

    bandLabel(s, "SEE MORE", "code, prototype, video and every calculation, one scan each", 4.16);
    const repo = "https://github.com/sakshamagrawalcode-cpu/hunarvaani";
    const qr = "image/png;base64," + (await QRCode.toBuffer(repo, { margin: 1, width: 300, color: { dark: "#1B2A4A", light: "#FFFFFF" } })).toString("base64");
    const more = [
      [fa.FaGithub, "GitHub repo", "code, architecture, docs/MODELS.md", qr],
      [fa.FaPhoneVolume, "Try the prototype", "call number + PIN (add)", null],
      [fa.FaVideo, "Demo video", "a real call, start to finish (add link)", null],
      [fa.FaCalculator, "Calculations", "scripts/cost_model.py: every rate + source", qr],
    ];
    for (let i = 0; i < more.length; i++) {
      const [Ic, t, sub, q] = more[i];
      const x = 0.3 + i * 2.37;
      card(s, x, 4.44, 2.27, 0.76, WHITE, { line: LINE });
      if (q) s.addImage({ data: q, x: x + 0.08, y: 4.5, w: 0.64, h: 0.64 });
      else {
        s.addShape("roundRect", { x: x + 0.08, y: 4.5, w: 0.64, h: 0.64, fill: { color: TINT.gray }, line: { color: "D1D5DB", width: 0.75, dashType: "dash" }, rectRadius: 0.05 });
        s.addImage({ data: await iconPng(Ic, "9CA3AF"), x: x + 0.24, y: 4.66, w: 0.32, h: 0.32 });
      }
      text(s, [
        { text: t, options: { bold: true, color: NAVY, fontSize: 9.5, breakLine: true } },
        { text: sub, options: { color: MUTED, fontSize: 7.5 } },
      ], { x: x + 0.8, y: 4.5, w: 1.42, h: 0.64, valign: "middle" });
    }
    text(s, "Ideas credited to: SkillCall, VoicePath, Kaushal Saathi, Sahayak, Saksham, MSOL · estimates are marked and fully worked on GitHub",
      { x: 2.6, y: 5.3, w: 6.6, h: 0.22, fontSize: 7, italic: true, color: MUTED, align: "center", valign: "middle" });
    s.addNotes("Sources by type. The two QR codes open the GitHub repository (make it public before submitting). Add the prototype number and the demo video link (unlisted, opens without login) and replace the two dashed boxes with their QR codes.");
  }

  await pres.writeFile({ fileName: "/tmp/pw/HunarMarg_SIH26097.pptx" });
  console.log("written");
}
main().catch((e) => { console.error(e); process.exit(1); });
