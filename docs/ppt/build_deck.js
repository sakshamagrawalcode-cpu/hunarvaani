// HunarMarg SIH 2026 deck, original design ("Marg" = path: milestones on a dotted path).
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const QRCode = require("qrcode");
const si = require("simple-icons");
const fa = require("react-icons/fa6");

const LOGO = process.env.SIH_LOGO || require("path").join(__dirname, "sih_logo.png"); // official SIH 2026 logo
const OUT = process.env.OUT || "/tmp/pw/HunarMarg_SIH26097.pptx";

// Indigo + marigold
const IND = "26215C", IND2 = "3B3486", MARI = "F2A33A", MARI_D = "C97A12", GRN = "2E7D5B";
const INK = "1F2937", MUTED = "6B7280", SOFT = "EEEDF7", LINE = "D9D7EA", WHITE = "FFFFFF", RED = "B4432C";
const HEAD = "Cambria", BODY = "Calibri";

async function png(Icon, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { color: "#" + color, size: String(size) }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}
async function brand(icon) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="256" height="256"><path fill="#${icon.hex}" d="${icon.path}"/></svg>`;
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}
function T(s, t, o) {
  s.addText(t, Object.assign({ isTextBox: true, fontFace: BODY, color: INK, margin: 0, valign: "top" }, o));
}
async function node(s, Icon, x, y, d, fill, iconColor = WHITE, line) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color: fill }, line: { color: line || fill, width: line ? 1.5 : 0 } });
  const p = d * 0.26;
  s.addImage({ data: await png(Icon, iconColor), x: x + p, y: y + p, w: d - 2 * p, h: d - 2 * p });
}
function dotted(s, x1, y, x2, color = MARI) {
  s.addShape("line", { x: x1, y, w: x2 - x1, h: 0, line: { color, width: 1.5, dashType: "dash" } });
}
function heading(s, t, x, y, w, color = IND) {
  T(s, t, { x, y, w, h: 0.28, fontSize: 13, bold: true, color, fontFace: HEAD, valign: "middle" });
}
function header(s, n, kicker, title) {
  T(s, `0${n}  ·  ${kicker}`, { x: 0.4, y: 0.2, w: 6, h: 0.2, fontSize: 9, bold: true, color: MARI_D, charSpacing: 2 });
  T(s, title, { x: 0.4, y: 0.42, w: 7.6, h: 0.46, fontSize: 24, bold: true, color: IND, fontFace: HEAD, valign: "middle" });
  s.addImage({ path: LOGO, x: 8.3, y: 0.14, w: 1.45, h: 0.685 });
  footer(s, n);
}
function footer(s, n, dark = false) {
  T(s, "HunarMarg  ·  SIH26097", { x: 0.4, y: 5.3, w: 2.5, h: 0.2, fontSize: 8, bold: true, color: dark ? "C9C6E8" : MUTED, valign: "middle" });
  // milestone path: slides 2-6
  const x0 = 8.35;
  dotted(s, x0 + 0.05, 5.4, x0 + 1.2, "BDB9DC");
  for (let i = 0; i < 5; i++) {
    const on = i + 2 === n, d = on ? 0.2 : 0.1, cx = x0 + i * 0.28;
    s.addShape("ellipse", { x: cx - d / 2 + 0.05, y: 5.4 - d / 2, w: d, h: d, fill: { color: on ? MARI : (i + 2 < n ? IND2 : "D6D3EA") }, line: { color: WHITE, width: 0 } });
    if (on) T(s, String(n), { x: cx - d / 2 + 0.05, y: 5.4 - d / 2, w: d, h: d, fontSize: 7.5, bold: true, color: IND, align: "center", valign: "middle" });
  }
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.title = "HunarMarg · SIH26097";

  // ============ 1. Title page (SIH template fields) ============
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    T(s, "SMART INDIA HACKATHON 2026", { x: 0.5, y: 0.35, w: 6.2, h: 0.55, fontSize: 28, bold: true, color: "1F4E79", fontFace: "Times New Roman", valign: "middle" });
    T(s, "TITLE PAGE", { x: 0.5, y: 0.95, w: 6.2, h: 0.4, fontSize: 20, bold: true, color: "111827", fontFace: "Times New Roman", valign: "middle" });
    s.addImage({ path: LOGO, x: 6.1, y: 1.55, w: 3.5, h: 1.65 });
    const f = (k, v, c = "1F4E79", last = false) => [
      { text: k, options: { bold: true, color: "1F2937", fontSize: 14, bullet: true } },
      { text: v, options: { bold: true, color: c, fontSize: 13, breakLine: !last } },
    ];
    T(s, [
      ...f("Problem Statement ID – ", "SIH26097"),
      ...f("Problem Statement Title – ", "AI-driven voice assistant for livelihood mapping and NSQF-aligned skilling recommendations for SC communities under the GIA component of PM-AJAY"),
      ...f("Theme – ", "Agriculture, FoodTech & Rural Development"),
      ...f("PS Category – ", "Software"),
      ...f("Team ID – ", "________", "B4432C"),
      ...f("Team Name (Registered on portal) – ", "________", "B4432C", true),
    ], { x: 0.5, y: 1.55, w: 5.3, h: 3.6, fontFace: "Arial", paraSpaceAfter: 8 });
    s.addNotes("Official SIH 2026 title page. Fill Team ID and Team Name exactly as on the SIH portal.");
  }

  // ============ 2. Proposed solution ============
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    // left panel: idea + the gap
    s.addShape("rect", { x: 0, y: 0, w: 3.3, h: 5.625, fill: { color: IND }, line: { color: IND, width: 0 } });
    T(s, "02  ·  PROPOSED SOLUTION", { x: 0.4, y: 0.2, w: 2.8, h: 0.2, fontSize: 9, bold: true, color: MARI, charSpacing: 2 });
    T(s, "HunarMarg", { x: 0.4, y: 0.45, w: 2.8, h: 0.55, fontSize: 30, bold: true, color: WHITE, fontFace: HEAD, valign: "middle" });
    T(s, "हुनरमार्ग · the path from skill to livelihood", { x: 0.4, y: 1.0, w: 2.8, h: 0.25, fontSize: 10, italic: true, color: MARI });
    T(s, "The gap", { x: 0.4, y: 1.48, w: 2.6, h: 0.24, fontSize: 11, bold: true, color: "C9C6E8", charSpacing: 1 });
    T(s, "A form picks the course, not the person, so SC job seekers land in training that doesn't fit them.",
      { x: 0.4, y: 1.74, w: 2.6, h: 0.62, fontSize: 11, color: WHITE });
    const gap = [["41%", "of certified trainees were placed", "CAG 2025"], ["51.6%", "of rural women have no phone of their own", "NSO 2025"], ["66.1%", "SC literacy: forms don't reach many", "Census 2011"]];
    gap.forEach(([n, l, src], i) => {
      const y = 2.55 + i * 0.82;
      T(s, n, { x: 0.4, y, w: 1.15, h: 0.45, fontSize: 24, bold: true, color: MARI, valign: "middle" });
      T(s, [{ text: l, options: { color: WHITE, breakLine: true } }, { text: src, options: { color: "A9A5D3", fontSize: 7.5 } }],
        { x: 1.6, y: y + 0.02, w: 1.5, h: 0.6, fontSize: 9 });
    });
    footer(s, 2, true);
    s.addImage({ path: LOGO, x: 8.3, y: 0.14, w: 1.45, h: 0.685 });

    // right: the journey on a path
    heading(s, "The journey: one call, guided end to end", 3.65, 0.95, 4.6);
    const steps = [
      [fa.FaPhoneVolume, "Missed call", "free callback from a govt 1600 number*, in their language"],
      [fa.FaKeyboard, "Keypad + voice", "facts by keypad; they describe their work in their own words"],
      [fa.FaIdCard, "Full profile", "AI maps skills to NCO and NSQF; read back, confirmed with 1"],
      [fa.FaRoute, "3 pathways", "training, RPL, apprenticeship or own work, with plan + money path"],
      [fa.FaCalendarCheck, "Till they earn", "SMS case ID, reminders, follow-ups at 1, 3, 6 months"],
    ];
    const px0 = 3.75, step = 1.2;
    dotted(s, px0 + 0.25, 1.75, px0 + 4 * step + 0.25);
    for (let i = 0; i < steps.length; i++) {
      const [Ic, t, d] = steps[i];
      const x = px0 + i * step;
      await node(s, Ic, x, 1.5, 0.5, i === 4 ? MARI : IND, i === 4 ? IND : WHITE);
      s.addShape("ellipse", { x: x + 0.36, y: 1.44, w: 0.2, h: 0.2, fill: { color: WHITE }, line: { color: MARI, width: 1 } });
      T(s, String(i + 1), { x: x + 0.36, y: 1.44, w: 0.2, h: 0.2, fontSize: 7.5, bold: true, color: MARI_D, align: "center", valign: "middle" });
      T(s, t, { x: x - 0.3, y: 2.08, w: 1.1, h: 0.2, fontSize: 10, bold: true, color: IND, align: "center" });
      T(s, d, { x: x - 0.32, y: 2.3, w: 1.14, h: 0.62, fontSize: 8, color: INK, align: "center" });
    }

    heading(s, "What only HunarMarg does", 3.65, 3.08, 4.6);
    const only = [
      [fa.FaMobileScreen, "Any keypad phone", "missed call, free, no reading needed"],
      [fa.FaDatabase, "Never invented", "every fact from govt data, checked before it is spoken"],
      [fa.FaFileSignature, "Writes the profile itself", "officers review and approve, no data entry"],
      [fa.FaIndianRupeeSign, "Money path", "which grant or loan fits, and the monthly EMI"],
      [fa.FaShieldHalved, "Outcomes that can't be faked", "random-digit liveness + employer check"],
      [fa.FaBrain, "Learns from verified jobs only", "fake placements can't teach the ranker"],
    ];
    for (let i = 0; i < only.length; i++) {
      const [Ic, t, d] = only[i];
      const x = 3.65 + (i % 2) * 3.05, y = 3.45 + Math.floor(i / 2) * 0.58;
      await node(s, Ic, x, y + 0.04, 0.36, SOFT, IND);
      T(s, [{ text: t, options: { bold: true, color: IND, fontSize: 10, breakLine: true } }, { text: d, options: { color: MUTED, fontSize: 8.5 } }],
        { x: x + 0.46, y, w: 2.5, h: 0.46, valign: "middle" });
    }
    T(s, "* needs a government MoU", { x: 6.2, y: 5.3, w: 1.95, h: 0.2, fontSize: 7.5, italic: true, color: MUTED, align: "right", valign: "middle" });
    s.addNotes("Left: the idea and the gap (CAG Report 20 of 2025: 41% of 56 lakh certified PMKVY trainees placed; NSO 2025; Census 2011). Right: the caller's journey in five steps, from a missed call to verified work, and six things only HunarMarg does. The 1600 number needs a government MoU.");
  }

  // ============ 3. Technical approach ============
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, 3, "TECHNICAL APPROACH", "How HunarMarg works");

    async function lane(y, label, sub, items, color) {
      T(s, [{ text: label, options: { bold: true, color, fontSize: 9.5, breakLine: true } }, { text: sub, options: { italic: true, color: MUTED, fontSize: 8 } }],
        { x: 0.4, y: y + 0.02, w: 1.05, h: 0.5 });
      const x0 = 1.55, sp = (6.6 - x0 - 0.42) / (items.length - 1), cw = Math.min(1.02, sp - 0.04);
      dotted(s, x0 + 0.21, y + 0.21, x0 + (items.length - 1) * sp + 0.21, color === IND ? "9C97CF" : MARI);
      for (let i = 0; i < items.length; i++) {
        const [Ic, t, d] = items[i];
        const x = x0 + i * sp;
        await node(s, Ic, x, y, 0.42, color, WHITE);
        T(s, t, { x: x + 0.21 - cw / 2, y: y + 0.46, w: cw, h: 0.18, fontSize: 8, bold: true, color: IND, align: "center" });
        T(s, d, { x: x + 0.21 - cw / 2, y: y + 0.63, w: cw, h: 0.3, fontSize: 7, color: MUTED, align: "center" });
      }
    }
    await lane(1.05, "During the call", "seconds", [
      [fa.FaPhoneVolume, "Exotel", "callback + keys"],
      [fa.FaMicrophone, "IndicConformer", "speech → text"],
      [fa.FaBrain, "Sarvam-30B", "fills the profile form"],
      [fa.FaMagnifyingGlass, "e5 + BM25", "finds the NCO job"],
      [fa.FaCircleCheck, "Read-back", "caller confirms"],
      [fa.FaScaleBalanced, "LightGBM", "ranks on govt data"],
      [fa.FaVolumeHigh, "Parler-TTS", "speaks checked facts"],
    ], IND);
    await lane(2.12, "After the call", "days", [
      [fa.FaIdCard, "Case", "profile + audit log"],
      [fa.FaCommentSms, "SMS", "case ID + documents"],
      [fa.FaUserCheck, "Officer*", "approves on console"],
      [fa.FaCalendarCheck, "Follow-ups", "1·3·6 months + liveness"],
      [fa.FaChartLine, "Learning", "retrains on verified jobs"],
    ], MARI_D);
    s.addShape("roundRect", { x: 0.4, y: 3.12, w: 6.35, h: 0.3, fill: { color: SOFT }, line: { color: SOFT, width: 0 }, rectRadius: 0.15 });
    T(s, "AI understands  →  rules and data decide  →  facts checked  →  people approve", { x: 0.4, y: 3.12, w: 6.35, h: 0.3, fontSize: 9.5, bold: true, color: IND, align: "center", valign: "middle" });

    // stack panel
    s.addShape("roundRect", { x: 7.0, y: 1.0, w: 2.7, h: 2.42, fill: { color: SOFT }, line: { color: SOFT, width: 0 }, rectRadius: 0.08 });
    heading(s, "Stack", 7.15, 1.06, 2.4);
    const stack = [
      ["Calls", "Exotel · 1600 number* · SMS"],
      ["AI (fine-tuned)", "IndicConformer · Indic Parler-TTS · Sarvam-30B · MuRIL · e5 · LightGBM · Satyavaani"],
      ["Govt data", "NCO-2015 · NQR · schemes · DigiLocker* · AJAY app*"],
    ];
    let sy = 1.38;
    for (const [k, v] of stack) {
      T(s, [{ text: k + "  ", options: { bold: true, color: MARI_D } }, { text: v, options: { color: INK } }], { x: 7.15, y: sy, w: 2.45, h: 0.46, fontSize: 8 });
      sy += k === "AI (fine-tuned)" ? 0.5 : 0.36;
    }
    T(s, "Backend", { x: 7.15, y: 2.66, w: 1, h: 0.16, fontSize: 8, bold: true, color: MARI_D });
    const logos = [si.siPython, si.siFastapi, si.siPostgresql, si.siRedis, si.siDocker, si.siReact];
    for (let j = 0; j < logos.length; j++) s.addImage({ data: await brand(logos[j]), x: 7.15 + j * 0.36, y: 2.88, w: 0.24, h: 0.24 });
    T(s, "on Indian GPU cloud", { x: 7.15, y: 3.16, w: 2.4, h: 0.16, fontSize: 7, italic: true, color: MUTED });

    // models table
    heading(s, "Models we fine-tune", 0.4, 3.52, 5);
    const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: IND }, fontSize: 7.5 } });
    const rows = [
      ["IndicConformer-600M", "speech → text, 22 languages", "100 h consented phone calls per language + IndicVoices · ~72 GPU-h", "Hindi error ≤ 20%"],
      ["Indic Parler-TTS", "voice, 21 languages", "12 h of one local voice artist per language · ~24 GPU-h", "listeners ≥ 4/5"],
      ["Sarvam-30B", "reads the story, fills a fixed form", "LoRA on 5,000 story → form pairs checked by people · ~16 GPU-h", "right job in top 3 ≥ 90%"],
      ["multilingual-e5 + BM25", "keyword + meaning job search", "every “1” at read-back = right pair, “none” = wrong pair", "right job in top 5 ≥ 90%"],
      ["LightGBM LambdaRank", "filters, then scores 6 factors", "officer-set weights (AHP) first, then verified jobs at 6 months", "gender gap ≤ 5 pts"],
      ["Satyavaani (team's own)", "liveness on follow-up calls", "Indian phone speech + 3 voice-cloning tools; no voiceprint", "flags, never rejects"],
    ];
    const data = [[hdr("Model"), hdr("What it does"), hdr("How we train it"), hdr("Must pass")]];
    rows.forEach((r, i) => data.push(r.map((c, j) => ({
      text: c, options: { fontSize: 7.5, bold: j === 0, color: j === 0 ? IND : (j === 3 ? MARI_D : INK), fill: { color: i % 2 ? WHITE : "F7F6FC" } },
    }))));
    s.addTable(data, {
      x: 0.4, y: 3.82, w: 9.3, colW: [1.75, 2.1, 3.95, 1.5], rowH: 0.195, fontFace: BODY, margin: [0.02, 0.06, 0.02, 0.06],
      border: { type: "solid", pt: 0.5, color: LINE }, valign: "middle",
    });
    T(s, "No Aadhaar number stored · caste never asked · consent logged (DPDP 2025) · data in India · * govt MoU",
      { x: 2.5, y: 5.3, w: 5.7, h: 0.2, fontSize: 7, italic: true, color: MUTED, align: "center", valign: "middle" });
    s.addNotes("During the call: Exotel takes the missed call and calls back; IndicConformer turns speech into text; Sarvam-30B (with the MuRIL tagger) fills a fixed profile form using only job codes from our list; e5 + BM25 find the NCO occupation; the caller confirms; LightGBM ranks options from government data; Indic Parler-TTS speaks only checked facts. If a GPU fails, the Sarvam API takes over; if the AI is stuck, a human counsellor calls back. After the call: the case is saved with an audit log, an SMS goes out, an officer approves, follow-ups at 1, 3 and 6 months include the Satyavaani liveness check, and only verified jobs retrain the ranker. Full details: docs/MODELS.md.");
  }

  // ============ 4. Feasibility ============
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, 4, "FEASIBILITY & VIABILITY", "Can it be built and run? Yes.");

    heading(s, "Proof it can work", 0.4, 0.98, 3);
    const proof = [
      ["22 cr", "feature-phone users: the channel exists", "Business Standard 2026"],
      ["3 cr+", "reached by Kilkari, a govt voice-call line; answers 50% → 76% by the 3rd try", "BMJ Global Health"],
      ["22 · 21", "languages in open Indian speech and voice models", "AI4Bharat"],
      ["19.3%", "best Indian speech error on IndicVoices: our bar before we switch", "Sarvam 2026"],
      ["✓", "our prototype takes real calls in 3 languages and gives top 3 options", "GitHub"],
    ];
    proof.forEach(([n, l, src], i) => {
      const y = 1.3 + i * 0.62;
      const last = i === proof.length - 1;
      T(s, n, { x: 0.4, y, w: 0.95, h: 0.5, fontSize: last ? 22 : 17, bold: true, color: last ? GRN : MARI_D, valign: "middle" });
      T(s, [{ text: l, options: { color: INK, breakLine: true } }, { text: src, options: { color: MUTED, fontSize: 7 } }],
        { x: 1.38, y: y + 0.02, w: 2.05, h: 0.56, fontSize: 8.5 });
      if (!last) s.addShape("line", { x: 0.4, y: y + 0.59, w: 3.05, h: 0, line: { color: LINE, width: 0.5 } });
    });

    heading(s, "What it costs", 3.8, 0.98, 3);
    const cost = [["₹163", "per person, all-in, at 50,000 a year"], ["0.24%", "of ₹69,200 GIA support per person"], ["₹8.8 L", "GPUs a year, in India"], ["₹2 L", "one time per language"]];
    cost.forEach(([n, l], i) => {
      const x = 3.8 + i * 1.5;
      s.addShape("roundRect", { x, y: 1.3, w: 1.4, h: 0.72, fill: { color: i === 0 ? IND : SOFT }, line: { color: i === 0 ? IND : SOFT, width: 0 }, rectRadius: 0.08 });
      T(s, n, { x: x + 0.1, y: 1.34, w: 1.2, h: 0.32, fontSize: 17, bold: true, color: i === 0 ? MARI : IND, valign: "middle" });
      T(s, l, { x: x + 0.1, y: 1.66, w: 1.22, h: 0.32, fontSize: 7.5, color: i === 0 ? WHITE : INK });
    });
    s.addChart(pres.charts.BAR, [
      { name: "Our own models", labels: ["50,000", "1 lakh", "5 lakh", "10 lakh"], values: [163, 94, 39, 32] },
      { name: "Paid APIs", labels: ["50,000", "1 lakh", "5 lakh", "10 lakh"], values: [121, 73, 35, 30] },
    ], {
      x: 3.75, y: 2.1, w: 6.0, h: 1.6, barDir: "col", barGrouping: "clustered", barGapWidthPct: 70,
      chartColors: [IND2, "D6D3EA"],
      showTitle: true, title: "Cost per person (₹) by people served a year", titleFontSize: 8.5, titleColor: IND, titleFontFace: BODY,
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 7, dataLabelColor: INK,
      catAxisLabelFontSize: 7.5, catAxisLabelColor: MUTED, valAxisHidden: true, catAxisLineShow: false,
      valGridLine: { style: "none" }, catGridLine: { style: "none" },
      showLegend: true, legendPos: "r", legendFontSize: 7, legendColor: MUTED,
    });
    // training path
    T(s, "Training plan", { x: 3.8, y: 3.74, w: 1.5, h: 0.2, fontSize: 9, bold: true, color: IND });
    const tp = [["Collect", "100 h per language"], ["Fine-tune", "~112 GPU-hours"], ["Test", "beat 19.3% error"], ["Improve", "every month"]];
    dotted(s, 4.3, 4.02, 8.95);
    for (let i = 0; i < tp.length; i++) {
      const cx = 4.3 + i * 1.55;
      s.addShape("ellipse", { x: cx - 0.08, y: 3.94, w: 0.16, h: 0.16, fill: { color: MARI }, line: { color: WHITE, width: 1 } });
      T(s, [{ text: tp[i][0], options: { bold: true, color: IND, breakLine: true } }, { text: tp[i][1], options: { color: MUTED } }],
        { x: cx - 0.65, y: 4.12, w: 1.3, h: 0.32, fontSize: 7.5, align: "center" });
    }

    heading(s, "Risks and safeguards", 0.4, 4.5, 4);
    const risks = [["Village dialects", "keypad for facts, everything read back, human fallback"], ["AI says something wrong", "only facts that match a govt data row are spoken"],
      ["Unknown numbers ignored", "they call first; callback from a 1600 number*"], ["Our model is weaker", "switch a language only after it beats 19.3%; API backup"]];
    const shield = await png(fa.FaShieldHalved, GRN);
    risks.forEach(([r, f], i) => {
      const x = 0.4 + i * 2.35;
      s.addImage({ data: shield, x, y: 4.86, w: 0.2, h: 0.2 });
      T(s, [{ text: r, options: { bold: true, color: RED, breakLine: true } }, { text: f, options: { color: INK } }], { x: x + 0.27, y: 4.82, w: 2.0, h: 0.46, fontSize: 8 });
    });
    s.addNotes("Costs from scripts/cost_model.py: journey minutes, API cost and team budget from our v4 research; E2E Networks GPU prices (L4 Rs 49/h, L40S Rs 102/h), 12 hours a day. At 50,000 people a year our own models cost Rs 163 per person (Rs 159-172 for carrier Rs 0.60-1.20/min) against Rs 121 on paid APIs; at 10 lakh it is Rs 32 against Rs 30. We choose our own models for 22 languages, dialect tuning and data control. Calls per GPU are estimates to be confirmed by a load test.");
  }

  // ============ 5. Impact ============
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, 5, "IMPACT & BENEFITS", "What changes on the ground");

    s.addShape("roundRect", { x: 0.4, y: 1.0, w: 9.3, h: 1.62, fill: { color: IND }, line: { color: IND, width: 0 }, rectRadius: 0.1 });
    const big = [
      ["41% → 70%", "placed after training", "CAG found 41%; 70% is the GIA target", [41, 70]],
      ["62% → 73%", "stay in the job", "when told real pay and place first (J-PAL trial)", [62, 73]],
      ["109 min", "officer time saved per person", "≈ 52 staff-years a year · our estimate", null],
      ["₹44,136", "saved on one small-business loan", "₹80,000 tailoring unit, right money path · our calculation", null],
    ];
    big.forEach(([n, l, d, bar], i) => {
      const x = 0.62 + i * 2.3;
      T(s, n, { x, y: 1.12, w: 2.1, h: 0.42, fontSize: 21, bold: true, color: MARI, valign: "middle" });
      T(s, l, { x, y: 1.56, w: 2.1, h: 0.2, fontSize: 9.5, bold: true, color: WHITE });
      if (bar) {
        s.addShape("rect", { x, y: 1.84, w: 1.9, h: 0.07, fill: { color: "4A4494" }, line: { color: "4A4494", width: 0 } });
        s.addShape("rect", { x, y: 1.84, w: 1.9 * bar[0] / 100, h: 0.07, fill: { color: "C9C6E8" }, line: { color: "C9C6E8", width: 0 } });
        s.addShape("ellipse", { x: x + 1.9 * bar[1] / 100 - 0.06, y: 1.815, w: 0.12, h: 0.12, fill: { color: MARI }, line: { color: IND, width: 0.75 } });
      }
      T(s, d, { x, y: bar ? 2.0 : 1.82, w: 2.05, h: 0.5, fontSize: 8, color: "C9C6E8" });
    });

    await node(s, fa.FaUsers, 0.4, 2.76, 0.34, SOFT, IND);
    T(s, [
      { text: "~50,000", options: { bold: true, color: MARI_D, fontSize: 13 } }, { text: " GIA beneficiaries a year      ", options: {} },
      { text: "47,000+", options: { bold: true, color: MARI_D, fontSize: 13 } }, { text: " SC-majority villages already on the PM-AJAY dashboard", options: {} },
    ], { x: 0.85, y: 2.76, w: 8.8, h: 0.34, fontSize: 9.5, color: INK, valign: "middle" });

    heading(s, "Who benefits, and how", 0.4, 3.24, 5);
    const who = [
      [fa.FaPersonDigging, "SC job seeker", "right course first time, free, own language, no middleman"],
      [fa.FaPersonDress, "Women", "keypad-only option, “safe to talk?”, women-only batches"],
      [fa.FaLandmark, "District officers", "ready profiles, less paperwork, one case record"],
      [fa.FaSchool, "Training centres", "trainees who fit, fewer dropouts"],
      [fa.FaBuildingColumns, "Banks · NSFDC", "better-matched loan applicants"],
      [fa.FaChartPie, "Ministry", "block-level demand for plans, outcomes it can trust"],
    ];
    for (let i = 0; i < who.length; i++) {
      const [Ic, t, d] = who[i];
      const x = 0.4 + i * 1.56;
      await node(s, Ic, x + 0.5, 3.6, 0.48, WHITE, IND, MARI);
      T(s, t, { x, y: 4.14, w: 1.48, h: 0.2, fontSize: 9.5, bold: true, color: IND, align: "center" });
      T(s, d, { x: x + 0.02, y: 4.36, w: 1.44, h: 0.5, fontSize: 8, color: INK, align: "center" });
    }
    T(s, [
      { text: "Social ", options: { bold: true, color: IND } }, { text: "fair, right-first-time advice   ·   " },
      { text: "Economic ", options: { bold: true, color: IND } }, { text: "0.24% extra so the rest buys the right course   ·   " },
      { text: "Environment ", options: { bold: true, color: IND } }, { text: "no paper, fewer office trips" },
    ], { x: 0.4, y: 4.92, w: 9.3, h: 0.22, fontSize: 8, color: MUTED, align: "center", valign: "middle" });
    T(s, "Pilot: 6–8 blocks, results in 6 months", { x: 3.0, y: 5.3, w: 4.0, h: 0.2, fontSize: 8.5, bold: true, color: GRN, align: "center", valign: "middle" });
    s.addNotes("CAG Report No. 20 of 2025: 41% of 56 lakh certified PMKVY trainees placed; the GIA target is 70%. J-PAL (Chakravorty et al., DDU-GKY, Bihar and Jharkhand): trainees told about real jobs were 11 points more likely to stay 5+ months (62% to 73%). 109 minutes and Rs 44,136 are our estimates from the v4 idea file. About 50,000 GIA beneficiaries a year (MoSJE factsheet, Sep 2026); the PM-AJAY dashboard covers 47,000+ SC-majority villages (PIB, May 2026).");
  }

  // ============ 6. References ============
  {
    const s = pres.addSlide();
    s.background = { color: WHITE };
    header(s, 6, "RESEARCH & REFERENCES", "Where every number comes from");
    const colA = [
      ["S1", "Census 2011 via MoSJE Handbook 2021: SC literacy 66.1%", "socialjustice.gov.in"],
      ["S2", "NSO Telecom survey 2025: phone ownership", "mospi.gov.in"],
      ["S3", "MoSJE PM-AJAY factsheet, 28 Sep 2026: ₹1,730 cr, 2.5 lakh people", "pib.gov.in"],
      ["S4", "PM-AJAY guidelines: 70% placement, 30% women", "socialjustice.gov.in"],
      ["S5", "CAG Report No. 20 of 2025: 41% of 56 lakh placed", "cag.gov.in"],
      ["S6", "NCO-2015 · NQR / NCVET · NSFDC · PM Vishwakarma", "nqr.gov.in"],
      ["S7", "PIB: PM-AJAY portal and AJAY app, 26 May 2026", "pib.gov.in"],
      ["S8", "Business Standard, Apr 2026: 22 crore feature-phone users", "business-standard.com"],
      ["S9", "BMJ Global Health: Kilkari reach and answer rates", "gh.bmj.com"],
      ["S10", "Chakravorty et al., J-PAL: job information → retention 62% → 73%", "povertyactionlab.org"],
    ];
    const colB = [
      ["S11", "Sarvam: Saaras v3, 19.31% WER on IndicVoices", "sarvam.ai"],
      ["S12", "AI4Bharat: IndicConformer, IndicVoices, Indic Parler-TTS", "huggingface.co/ai4bharat"],
      ["S13", "Sarvam-30B open weights, Apache 2.0", "huggingface.co/sarvamai"],
      ["S14", "E2E Networks GPU prices: L4 ₹49/h, L40S ₹102/h", "e2enetworks.com"],
      ["S15", "Sarvam API pricing; carrier rate cards (team research)", "docs.sarvam.ai"],
      ["S16", "DPDP Rules 2025, notified 14 Nov 2025", "meity.gov.in"],
      ["S17", "TRAI: 1600 series for government-to-citizen calls", "trai.gov.in"],
      ["S18", "Our work: prototype, MODELS.md, cost_model.py, measure.py", "GitHub"],
    ];
    const list = (items, x, w) => T(s, items.flatMap(([tag, t, site], i) => [
      { text: tag + "  ", options: { bold: true, color: MARI_D } },
      { text: t, options: { color: INK } },
      { text: "  " + site, options: { color: MUTED, fontSize: 7, breakLine: i < items.length - 1 } },
    ]), { x, y: 1.32, w, h: 2.75, fontSize: 9, paraSpaceAfter: 6 });
    heading(s, "Government and research", 0.4, 0.98, 4);
    list(colA, 0.4, 4.5);
    heading(s, "Technology, policy and our work", 5.15, 0.98, 4);
    list(colB, 5.15, 4.55);

    s.addShape("roundRect", { x: 0.4, y: 4.18, w: 9.3, h: 0.98, fill: { color: SOFT }, line: { color: SOFT, width: 0 }, rectRadius: 0.1 });
    const repo = "https://github.com/sakshamagrawalcode-cpu/hunarvaani";
    const qr = "image/png;base64," + (await QRCode.toBuffer(repo, { margin: 1, width: 300, color: { dark: "#26215C", light: "#FFFFFF" } })).toString("base64");
    const more = [["GitHub", "code + docs/MODELS.md", qr, fa.FaGithub], ["Prototype", "number + PIN (add)", null, fa.FaPhoneVolume], ["Demo video", "a real call (add link)", null, fa.FaVideo], ["Calculations", "scripts/cost_model.py", qr, fa.FaCalculator]];
    for (let i = 0; i < more.length; i++) {
      const [t, d, q, Ic] = more[i];
      const x = 0.6 + i * 2.3;
      if (q) s.addImage({ data: q, x, y: 4.3, w: 0.74, h: 0.74 });
      else {
        s.addShape("roundRect", { x, y: 4.3, w: 0.74, h: 0.74, fill: { color: WHITE }, line: { color: "B7B3D9", width: 0.75, dashType: "dash" }, rectRadius: 0.05 });
        s.addImage({ data: await png(Ic, "9C97CF"), x: x + 0.21, y: 4.51, w: 0.32, h: 0.32 });
      }
      T(s, [{ text: t, options: { bold: true, color: IND, fontSize: 10, breakLine: true } }, { text: d, options: { color: MUTED, fontSize: 8 } }],
        { x: x + 0.84, y: 4.3, w: 1.35, h: 0.74, valign: "middle" });
    }
    T(s, "Ideas credited to other SIH26097 teams: SkillCall, VoicePath, Kaushal Saathi, Sahayak, Saksham, MSOL",
      { x: 2.5, y: 5.3, w: 5.7, h: 0.2, fontSize: 7, italic: true, color: MUTED, align: "center", valign: "middle" });
    s.addNotes("Make the GitHub repository public before submitting (both QR codes open it). Add the prototype number and the demo video link, and put their QR codes in the two dashed boxes.");
  }

  await pres.writeFile({ fileName: OUT });
  console.log("written", OUT);
}
main().catch((e) => { console.error(e); process.exit(1); });
