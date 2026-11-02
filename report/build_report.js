// Builds the CP3209/UROP project report (.docx) in the required format:
// Times New Roman >= 11pt, 1.5 line spacing in the main report, A4, roman front matter,
// main pages numbered from 1, appendix pages A-1, B-1, ...  Run: node build_report.js
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Footer, PageNumber,
  NumberFormat, Table, TableRow, TableCell, WidthType, BorderStyle, ShadingType, ImageRun,
  PageBreak, LevelFormat, TabStopType, TabStopPosition, LeaderType,
} = require('docx');
const TOCPAGES = fs.existsSync(path.join(__dirname, 'toc_pages.json')) ? JSON.parse(fs.readFileSync(path.join(__dirname, 'toc_pages.json'))) : {};
const headings = [];

const ROOT = path.resolve(__dirname, '..');
const FONT = 'Times New Roman';
const BODY = 24;        // 12pt in half-points
const SMALL = 20;       // 10pt for appendices
const TABLE = 22;       // 11pt table text
const LINE15 = 360;     // 1.5 line spacing
const PAGE_W = 11906, MARGIN = 1440, TEXT_W = PAGE_W - 2 * MARGIN;  // A4, 1" margins

// ---------- inline markup: **bold**, *italic*, [[PENDING ...]] highlighted ----------
function runs(text, size = BODY) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\[\[[^\]]+\]\]|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, size }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, size }));
    else if (t.startsWith('[[')) out.push(new TextRun({ text: t.slice(2, -2), highlight: 'yellow', bold: true, font: FONT, size }));
    else if (t.startsWith('`')) out.push(new TextRun({ text: t.slice(1, -1), font: 'Courier New', size: size - 2 }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, size }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, size }));
  return out;
}

let compact = false;  // appendices: single spacing, smaller font
const sz = () => (compact ? SMALL + 2 : BODY);
const spacing = () => (compact ? { line: 240, after: 100 } : { line: LINE15, after: 120 });
const P = (t, o = {}) => new Paragraph({ children: runs(t, sz()), spacing: spacing(), alignment: AlignmentType.JUSTIFIED, ...o });
const B = (t, level = 0) => new Paragraph({ children: runs(t, sz()), numbering: { reference: 'bullets', level }, spacing: spacing() });
let listInstance = 0;
const NewList = () => { listInstance += 1; };
const N = (t) => new Paragraph({ children: runs(t, sz()), numbering: { reference: 'numbers', level: 0, instance: listInstance }, spacing: spacing() });
const H1 = (t) => (headings.push([1, t]), new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT, size: 32, bold: true, color: '000000' })], spacing: { before: 240, after: 240 } }));
const H2 = (t) => (headings.push([2, t]), new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT, size: 28, bold: true, color: '000000' })], spacing: { before: 240, after: 120 }, keepNext: true }));
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: FONT, size: 24, bold: true, italics: true, color: '000000' })], spacing: { before: 180, after: 80 }, keepNext: true });
const Center = (t, size, bold = false, after = 200) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after }, children: [new TextRun({ text: t, font: FONT, size, bold })] });
const Break = () => new Paragraph({ children: [new PageBreak()] });

let figN = 0, tabN = 0;
const figures = [], tables = [];
function Caption(kind, text) {
  const n = kind === 'Figure' ? ++figN : ++tabN;
  (kind === 'Figure' ? figures : tables).push(`${kind} ${n}. ${text}`);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 }, keepNext: kind === 'Table',
    children: [new TextRun({ text: `${kind} ${n}. `, bold: true, font: FONT, size: 22 }), ...runs(text, 22)] });
}

function Figure(rel, widthIn, caption) {
  const file = path.join(ROOT, rel);
  const buf = fs.readFileSync(file);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);  // PNG IHDR
  const width = Math.round(widthIn * 96), height = Math.round(width * h / w);
  return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120 },
    children: [new ImageRun({ type: 'png', data: buf, transformation: { width, height }, altText: { title: caption, description: caption, name: path.basename(rel) } })] }),
  Caption('Figure', caption)];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: '999999' };
function Tbl(caption, headers, rows, fracs) {
  const total = TEXT_W;
  const widths = fracs.map(f => Math.round(f * total));
  widths[widths.length - 1] = total - widths.slice(0, -1).reduce((a, b) => a + b, 0);
  const together = rows.length <= 6;
  const cell = (t, i, head, keep = false) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, margins: { top: 40, bottom: 40, left: 60, right: 60 },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: head ? { type: ShadingType.CLEAR, fill: 'E8E8E8', color: 'auto' } : undefined,
    children: [new Paragraph({ keepNext: keep, alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER, children: head ? [new TextRun({ text: t, bold: true, font: FONT, size: TABLE })] : runs(String(t), TABLE) })],
  });
  return [Caption('Table', caption), new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true, together)) }),
      ...rows.map((r, k) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, together && k < rows.length - 1)) }))] }),
  new Paragraph({ spacing: { after: 120 }, children: [] })];
}

const footer = (prefix) => ({ default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: prefix ? [prefix, PageNumber.CURRENT] : [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) });

// ======================================================================================
// CONTENT
// ======================================================================================
const TITLE = 'From Social Signals to Market Reactions: Novel Information versus Social Amplification in Polymarket';
const SUBTITLE = 'Auditable Prediction of Short-Horizon Quote Activity: Contract History, Market State and News Baselines';
const STUDENT = 'Zhu Rong';
const ADVISOR = 'Lu Yao';
const YEAR = '2026/2027';

const cover = [
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  Center('UNDERGRADUATE RESEARCH OPPORTUNITY PROGRAM', 28, true, 80),
  Center('(UROP) PROJECT REPORT', 28, true, 1200),
  Center(TITLE, 36, true, 240),
  Center(SUBTITLE, 26, false, 1000),
  Center('By', 24, false, 120),
  Center(STUDENT, 28, true, 1600),
  Center('[Department of Computer Science]', 24, false, 80),
  Center('School of Computing', 24, false, 80),
  Center('National University of Singapore', 24, false, 600),
  Center(YEAR, 24, false, 0),
];

const titlePage = [
  new Paragraph({ pageBreakBefore: true, spacing: { before: 1200 }, children: [] }),
  Center('UNDERGRADUATE RESEARCH OPPORTUNITY PROGRAM', 26, true, 80),
  Center('(UROP) PROJECT REPORT', 26, true, 800),
  Center(TITLE, 30, true, 200),
  Center(SUBTITLE, 24, false, 600),
  Center('By', 24, false, 120),
  Center(STUDENT, 26, true, 800),
  Center('[Department of Computer Science]', 24, false, 80),
  Center('School of Computing', 24, false, 80),
  Center('National University of Singapore', 24, false, 80),
  Center(YEAR, 24, false, 900),
  new Paragraph({ children: runs('Project No: U398070'), spacing: { after: 80 } }),
  new Paragraph({ children: runs(`Advisor: ${ADVISOR}`), spacing: { after: 240 } }),
  new Paragraph({ children: runs('**Deliverables:**'), spacing: { after: 80 } }),
  new Paragraph({ children: runs('Report: 1 Volume'), spacing: { after: 40 } }),
  new Paragraph({ children: runs('Program: EventX source repository (Python), frozen release manifests and evaluation scripts'), spacing: { after: 40 } }),
  new Paragraph({ children: runs('Data: hash-locked evaluation outputs and receipts (data/ directory)'), spacing: { after: 40 } }),
];

const abstract = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Abstract', font: FONT, size: 32, bold: true, color: '000000' })], spacing: { after: 240 } }),
  P('EventX asks whether information available at a decision time predicts short-horizon repricing in prediction markets, under strict point-in-time and evaluate-once rules. In a frozen study of 4,651 Kalshi and Polymarket markets, counts of conservatively available news articles did not improve a market-history model, and a prospective test of richer news features also failed. We then forecast whether a contract’s quoted midpoint changes within 30 minutes. A frozen gradient-boosted classifier on 18 quote features reduced log loss against a logistic baseline by 9.2–16.8% on three unopened blocks. Once-only tests on 181 further new contracts showed that combining it with each contract’s own outcome rate beat the rate by 10.5–13.3%, that its gain is concentrated after quote moves and at wide spreads, and that a stack using these states improved further (log loss 0.3006 against 0.3083). Recent tabular learners with default settings did not beat the booster; the Sundial time-series model improved on the online rate but not on the stack. A three-day live test issued 68.4% of scheduled forecasts on time, with log loss 16.7% below the logistic baseline on known outcomes. Short-horizon quote activity was predictable from market state; news features did not help.'),
  new Paragraph({ spacing: { before: 240, after: 80 }, children: runs('**Subject Descriptors:**') }),
  ...['G.3 Probability and Statistics', 'I.2.6 Learning', 'H.2.8 Database Applications (Data mining)', 'J.4 Social and Behavioral Sciences (Economics)']
    .map(t => new Paragraph({ children: runs(t), spacing: { after: 20 }, indent: { left: 720 } })),
  new Paragraph({ spacing: { before: 200, after: 80 }, children: runs('**Keywords:**') }),
  new Paragraph({ indent: { left: 720 }, children: runs('Prediction markets, probabilistic forecasting, market microstructure, gradient boosting, leakage-safe evaluation') }),
  new Paragraph({ spacing: { before: 200, after: 80 }, children: runs('**Implementation Software and Hardware:**') }),
  new Paragraph({ indent: { left: 720 }, children: runs('Python 3.12, scikit-learn, PyTorch, PyArrow, NumPy, httpx; Polymarket CLOB WebSocket and Gamma API; pmxt hourly order-book archive; Lumid FinData; Apple macOS laptop (17 GB RAM)') }),
];

const ack = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Acknowledgement', font: FONT, size: 32, bold: true, color: '000000' })], spacing: { after: 240 } }),
  new Paragraph({ spacing: { line: 480 }, alignment: AlignmentType.JUSTIFIED, children: runs(`I thank my advisor, ${ADVISOR}, for guidance on research design and for insisting on honest, preregistered evaluation. I also thank the providers of the data used in this project: Lumid FinData for historical trades and news, the pmxt project for the public Polymarket order-book archive, and Polymarket for its public market-data interfaces.`) }),
];

// Static contents: page labels come from toc_pages.json, written by paginate.py after a first render.
const tocEntry = (level, t) => new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: TEXT_W, leader: LeaderType.DOT }],
  indent: { left: level === 2 ? 480 : 0 }, spacing: { line: 300, after: level === 1 ? 60 : 20, before: level === 1 ? 100 : 0 },
  children: [new TextRun({ text: t, font: FONT, size: 24, bold: level === 1 }), new TextRun({ text: '\t' + (TOCPAGES[t] || '?'), font: FONT, size: 24 })] });
const tocPage = () => [
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Table of Contents', font: FONT, size: 32, bold: true, color: '000000' })], spacing: { after: 240 } }),
  ...['Abstract', 'Acknowledgement', 'List of Figures', 'List of Tables'].map(t => tocEntry(1, t)),
  ...headings.map(([l, t]) => tocEntry(l, t)),
];

// ---------------------------------- main report ----------------------------------------
const main = [];
const add = (...xs) => xs.flat().forEach(x => main.push(x));

add(H1('1 Introduction'));
add(H2('1.1 Background and motivation'));
add(P('Prediction markets let traders buy contracts that pay one dollar if an event happens, so a contract’s price can be read as a crowd probability of that event (Wolfers and Zitzewitz, 2004; Arrow et al, 2008). Platforms such as Polymarket and Kalshi list thousands of such contracts. Prices move when new information arrives, but they also move for mechanical reasons: liquidity providers re-quote, the order book thins out overnight, and contracts become quiet as their resolution approaches.'));
add(P('The original goal of EventX was a benchmark for whether outside information (news articles, and later posts by influential social-media accounts) carries **incremental, point-in-time** predictive information about these price moves beyond market history. Such results are easy to overstate: a single look-ahead leak, a reused test period or a weak baseline can produce an apparent gain. The project therefore treats evaluation discipline as a research output in its own right. Every test set and model is frozen before it is opened, and each held-out period is evaluated once; the exceptions are disclosed in Appendix B.'));
add(H2('1.2 Research questions'));
NewList();
add(N('**RQ1 (news increment).** Does news that was demonstrably available at decision time improve a forecast of the next 30-minute price jump beyond a market-history baseline?'));
add(N('**RQ2 (forecastable target).** Is there a short-horizon market quantity that can be forecast reliably better than strong baselines, and does that advantage survive new time periods and never-seen contracts?'));
add(N('**RQ3 (live operation).** Can such a forecaster run prospectively on live data, under the same frozen rules, with every decision auditable after the fact?'));
add(H2('1.3 Summary of contributions'));
add(B('A frozen, preregistered test of news value over 4,651 markets (a development out-of-fold comparison; the holdout scored only the market model), with a negative answer to RQ1; a post hoc bootstrap bounds the effect below every positive effect size registered in advance (Chapter 4).'));
add(B('A leakage-safe, evaluate-once framework: frozen protocols and cohorts, consumption receipts, hash-locked releases, failures and deviations kept on record (Appendix B), and a checker that ties each headline number to its artifact (Appendix C).'));
add(B('A quote-change forecaster whose advantage over logistic and rate baselines replicates on three unopened June blocks, two of them with never-used contracts (Chapters 5 and 6).'));
add(B('Three further once-only tests on new contracts. Combining the forecaster with each contract’s online rate beat the rate by 13.3% and 10.5%; its gain over the rate is concentrated after quote moves and at wide spreads (Holm-adjusted p = 0.0004); and a stack that uses these states improved on the plain stack (Sections 6.6–6.9).'));
add(B('A comparison with recent ICML, NeurIPS and ICLR baselines (TabM, RealMLP, TabICL, Moirai-MoE, Sundial, Time-MoE), where the default tabular learners did not beat the booster and Sundial improved on the online rate but not on the stack, and a development study that identifies the next candidate (Sections 6.10 and 6.11).'));
add(B('A prospective runtime with a validated clock, hash-chained journals and evaluate-once scoring; a three-day live test issued 68.4% of scheduled forecasts on time (Chapter 7).'));
add(H2('1.4 Organisation of the report'));
add(P('Chapter 2 reviews related work. Chapter 3 describes the data and the leakage safeguards shared by all studies. Chapter 4 reports the news-increment study (Track A). Chapters 5 and 6 present the quote-change forecaster and its historical evaluations (Track B), and Chapter 7 the prospective live test. Chapter 8 discusses validity, and Chapter 9 concludes with limitations and recommendations. Appendices give features, deviations and reproduction steps.'));

add(H1('2 Background and Related Work'));
add(H2('2.1 Prediction markets as forecasts'));
add(P('Prediction-market prices aggregate dispersed beliefs and often forecast at least as well as polls or experts (Wolfers and Zitzewitz, 2004; Arrow et al, 2008). Calibration is good on average but imperfect for long shots and distant events (Page and Clemen, 2013). This project does not forecast final outcomes but the behaviour of the market’s *own price* over the next half hour.'));
add(H2('2.2 News, attention and asset prices'));
add(P('Media content has measurable, short-lived associations with stock returns and trading volume (Tetlock, 2007). The difficulty is timing: a news record helps only if it was available *before* the price moved, so EventX uses the most conservative availability timestamp and treats missing feed intervals as unknown rather than as zero news.'));
add(P('Prediction-market and betting prices respond quickly to identified news (Snowberg, Wolfers and Zitzewitz, 2007; Croxson and Reade, 2014), and Kalshi macroeconomic markets track macroeconomic news at high frequency (Diercks, Katz and Wright, 2026). Track A asks a harder question: whether routinely available news counts, measured before the decision time, improve a forecast beyond what market history already contains.'));
add(H2('2.3 Market microstructure'));
add(P('Short-horizon price behaviour is driven largely by microstructure: the bid–ask spread, quote updates by liquidity providers, and the arrival of orders (O’Hara, 1995; Hasbrouck, 2007). The midpoint of the best bid and ask is the standard high-frequency price proxy, and quote activity is persistent, which makes a quote-change target forecastable in principle. Duration models capture the clustering of updates (Engle and Russell, 1998), but an update within a window does not guarantee that the midpoint differs at its end.'));
add(P('Machine-learning work on limit order books mostly forecasts the *direction* of the next mid-price move in liquid equity markets (Ntakaris, Magris, Kanniainen, Gabbouj and Iosifidis, 2018; Zhang, Zohren and Roberts, 2019). Sirignano and Cont (2019) show that a model pooled across stocks transfers to stocks outside its training sample, and Kolm, Turiel and Westray (2023) find that input representation matters more than network depth. EventX differs in target, market and protocol: it forecasts whether the midpoint of a thin, expiring prediction-market contract differs after 30 minutes, with models frozen before the data were retrieved and tested once on contracts never used before.'));
add(H2('2.4 Forecast evaluation and leakage'));
add(P('Probabilistic forecasts are evaluated with strictly proper scoring rules, here log loss and the Brier score (Brier, 1950; Gneiting and Raftery, 2007); boosted trees can distort probabilities (Niculescu-Mizil and Caruana, 2005), so calibration is checked separately. Leakage, meaning information from the future or from the test set entering model building, is a common cause of false results in data mining (Kaufman, Rosset, Perlich and Stitelman, 2012), and a survey of machine-learning-based science found it in published work across 17 fields (Kapoor and Narayanan, 2023). In financial time series it also arises from overlapping label windows, which requires purged, embargoed cross-validation (López de Prado, 2018). Observations within one market are dependent, so uncertainty is estimated by resampling whole blocks or whole contracts rather than individual rows (Künsch, 1989; Cameron, Gelbach and Miller, 2008).'));
add(H2('2.5 Learning method'));
add(P('The forecasters use histogram-based gradient boosting (Friedman, 2001; Ke et al, 2017), as implemented in scikit-learn (Pedregosa et al, 2011). EventX makes no claim of algorithmic novelty; its contribution is the target, the point-in-time features and the evaluation protocol. Tree ensembles remain highly competitive on medium-sized tabular data (Grinsztajn, Oyallon and Varoquaux, 2022), so boosting is a reasonable default.'));

add(H2('2.6 Recent state-of-the-art learners used as baselines'));
add(P('Older sequence networks (recurrent and convolutional models such as DeepLOB) and plain multilayer perceptrons are no longer state-of-the-art references, so the baselines in Section 6.10 come from ICML, NeurIPS and ICLR papers of the last two years, each run with its published defaults on matched inputs. TabM (Gorishniy, Kotelnikov and Babenko, 2025) is a parameter-efficient ensemble of multilayer perceptrons; RealMLP (Holzmüller, Grinsztajn and Steinwart, 2024) is a multilayer perceptron with tuned defaults; and TabICL (Qu, Holzmüller, Varoquaux and Le Morvan, 2025) is a tabular foundation model that predicts by in-context learning. The TabArena benchmark (Erickson et al, 2025) finds boosted trees still strong on practical tabular data, with tuned deep models and foundation models competitive, the latter especially on small training sets. For a contract’s own outcome history the modern reference is a pretrained time-series foundation model used zero-shot: Moirai-MoE (Liu et al, 2025), Sundial (Liu et al, 2025b) and Time-MoE (Shi et al, 2025). These forecast real-valued series, so applying them to a binary series is an adaptation, and a poor score evaluates that adaptation rather than the models. Language models that forecast the final outcomes of prediction-market questions (Halawi, Zhang, Yueh-Han and Steinhardt, 2024; Karger et al, 2025) address a different target.'));
add(H1('3 Data and Leakage Safeguards'));
add(H2('3.1 Data sources'));
add(B('**Lumid FinData** supplies historical executed trades for Kalshi and Polymarket, and a news feed with publication and ingestion timestamps. Analysis uses frozen, content-hashed extracts rather than live API calls.'));
add(B('**The pmxt Polymarket archive** publishes one Parquet file of order-book events per hour with venue and receive timestamps; only the row groups of selected contracts are downloaded.'));
add(B('**Polymarket’s Gamma metadata API and CLOB WebSocket** supply contract metadata and live book updates (Polymarket, 2026).'));
add(H2('3.2 Safeguards common to all studies'));
add(P('The following rules govern the studies in this report and are enforced in code rather than by convention. The quote freshness and validity rule applies to Track B only.'));
add(B('**Point in time.** Every feature for a decision at time *t* uses only records received at or before *t*. In Track B, a forecast is issued only when the latest quote is fresh (at most 120 seconds old on both the venue and the receive clocks), valid (0 < bid ≤ ask < 1, spread at most 0.05) and unambiguous.'));
add(B('**Frozen, hash-locked releases.** Protocols, cohorts, model files and evaluation code are frozen as SHA-256 manifests *before* the data they will be judged on is retrieved. A changed file means a new version, never an edit in place.'));
add(B('**Evaluate once.** Each frozen confirmatory test window is consumed by a single evaluation run, which writes a consumption receipt first and refuses to run again. Results are reported whether favourable or not.'));
add(B('**Protected identifiers and windows.** 1,231 market identifiers and three time windows used by earlier confirmatory studies are filtered out at decode time; the one exception, an authorized reuse of a calendar period, is disclosed in Section 6.9 and Appendix B.'));
add(B('**Outcome-blind cohort selection.** New cohorts are chosen from identifiers, clocks and metadata before any price of the test period is read; unknown outcomes are never imputed.'));

add(H2('3.3 Study overview'));
add(P('The project ran a sequence of versioned studies. Table 1 lists each one with its data, model, comparator and status, so that the version names used in later chapters can be looked up in one place. Training periods are those of the frozen model being scored; evaluation periods are the data that model had not been fitted on.'));
add(Tbl('Overview of the studies reported here. Known / missing counts are matched forecasts with an observed endpoint and issued forecasts without one.',
  ['Study', 'Training data', 'Evaluation data', 'Model vs comparator', 'Contracts; known / missing', 'Pass rule', 'Status'],
  [['V3.1 development (Track A)', 'Purged expanding folds', '17 May–22 Jul 2026, out-of-fold', 'B1 (news counts) vs B0 (market history)', '2,290 of 4,651 markets; 1,460,454 rows', 'All five gates', '0 of 5 gates'],
   ['V3.1 holdout', '17 May–22 Jul', '22 Jul–8 Aug', 'B0 only (absolute benchmark)', '300 markets; 211,718 rows', 'None', 'Consumed once; deviation disclosed'],
   ['V4 confirmatory', '17 May–22 Jul (discovery)', '6 Sep–30 Oct, collected prospectively', 'B3 (richer news) vs B0', '470 contracts', 'LL gain ≥ 0.001 nats, lower bound > 0, guards', 'Fail'],
   ['May 13–19 replication (Track B)', '7–9 May, 50 development contracts', '13–19 May', 'row_hgb7 vs activity logistic', '30; 27,924 / 4,553', 'None (fixed-model replication)', 'Complete'],
   ['June 1–7', '7–9 May', '1–7 June, unopened', 'row_hgb7 vs activity logistic', '18 (development); 16,453 / 2,851', 'Lower LL, Brier no higher', 'Pass'],
   ['June 8–14', '7–9 May', '8–14 June, unopened, new contracts', 'row_hgb7 vs activity logistic', '35; 35,218 / 4,438', 'As 1–7 June, plus lower bound > 0', 'Pass'],
   ['June 8–14, V03 secondary', '7–9 May (14 features)', '8–14 June', 'V03 hgb7 vs its full logistic', '35; 35,749 / 4,268', 'Secondary', 'Complete'],
   ['June 15–28', '7–9 May', '15–28 June, unopened, new contracts', 'row_hgb7 vs activity logistic; V03 secondary', '21 selected', 'As 8–14 June', 'Pass'],
   ['History stack (new cycle)', 'Four opened blocks, 13 May–28 June', '29 June–12 July, unopened, new contracts', 'stack_lin vs online contract rate', '53 selected, 51 contribute; 65,458 / 8,739', 'Lower LL, Brier no higher, lower bound > 0', 'Pass'],
   ['Segment confirmation (new cycle)', 'Five opened blocks, 13 May–12 July', '13–21 July, unopened, new contracts', 'row_hgb7 gain over online rate by segment (H1, H2); stack vs rate (H3)', '80 selected, 78 contribute; 159,283 / 4,535', 'Holm-adjusted one-sided p; H3 as above', 'Pass (all three)'],
   ['Segment-aware stack (new cycle)', 'Six opened blocks, 13 May–21 July', '22 July–8 August, new contracts (disclosed deviation)', 'seg_hgb vs stack_lin', '54 selected, 52 contribute; 134,341 / 6,632', 'Lower LL, Brier no higher, lower bound > 0', 'Pass'],
   ['Recent baselines (post hoc)', 'As each reference model', 'Seven opened blocks, 13 May–8 August', 'Recent learners vs row_hgb7, online rate and seg_hgb', '268 contracts (285 contract–blocks); 506,723 known outcomes', 'None (descriptive)', 'Complete'],
   ['Development study v8', 'Leave-one-block-out', 'Held-out blocks', 'New boosters vs seg_hgb design', '268 contracts (285 contract–blocks); 506,723 known outcomes', 'None (development)', 'Complete'],
   ['Live V02b', '7–9 May (V03)', '27 Oct 06:35–29 Oct 23:25 UTC, prospective', 'V03 hgb7 vs full logistic and global rate', '30; 22,650 scheduled decisions', 'None (reporting floor)', 'Descriptive']],
  [0.145, 0.144, 0.149, 0.14, 0.167, 0.13, 0.125]));
add(H2('3.4 Scores, uncertainty and missing outcomes'));
add(P('All forecasts are probabilities *p* of a binary outcome *y*. They are scored with two strictly proper scoring rules, for which lower is better:'));
add(B('**log loss**, the mean of −[*y* ln *p* + (1 − *y*) ln(1 − *p*)] over forecasts, in nats;'));
add(B('**Brier score**, the mean of (*p* − *y*)².'));
add(P('Average precision (AP) and the area under the ROC curve (AUC) summarise ranking. A **gain** is the comparator’s score minus the candidate’s, so a positive gain favours the candidate (for AP, candidate minus comparator), and a **relative reduction** is the log-loss gain divided by the comparator’s log loss. Every comparison is **matched**: all models are scored on the same forecasts.'));
add(P('**Uncertainty.** Forecasts from one contract are dependent, so 95% intervals come from a **cluster bootstrap** that resamples whole contracts (in Track A, whole markets) 5,000 times (2,000 in Section 4.3) and takes percentiles of the row-weighted mean gain; date-clustered and contract × date versions resample days as well.'));
add(P('**Missing outcomes.** A forecast’s outcome is known only if a valid endpoint quote exists 30 minutes later; otherwise it is scored as unknown, never imputed. The **missing-outcome bounds** are deterministic, not confidence intervals: each unknown outcome is set to whichever value is worst (lower bound) or best (upper bound) for the candidate, and the mean gain is recomputed over all issued forecasts. A lower bound above zero means no assignment of the unknown outcomes could reverse the sign of the gain.'));

add(H1('4 Track A: Incremental Value of News'));
add(H2('4.1 Design of the historical primary study (V3.1)'));
add(P('The cohort contains 4,651 markets (3,832 Kalshi and 819 Polymarket) with enough trading activity. Development covers 17 May to 22 July 2026, and a separate holdout covers 22 July to 8 August 2026. At each five-minute decision time the price is the latest executed YES trade. The binary target asks whether the absolute log-odds change over the next 30 minutes exceeds four times the trailing one-minute volatility.'));
add(P('**B0** is a 12-feature market-history logistic ensemble: price log-odds, 5/30/120-minute momentum, 30/240-minute realised volatility, 60/240-minute trade counts and notional, time since last trade, and venue. **B1** adds rolling counts of conservatively available, lexically associated news articles over 60, 360 and 1,440 minutes. Both are trained on identical rows across five purged, expanding-time folds. B1 would be promoted only if all five gates held: positive aggregate average-precision (AP) and Brier changes, positive changes in at least four folds, a positive lower bound on a 5,000-replicate paired block-bootstrap Brier interval, and no venue-level deterioration.'));
add(H2('4.2 Results'));
add(Tbl('V3.1 development comparison of news-augmented (B1) and market-only (B0) models on 1,460,454 matched out-of-fold rows.',
  ['Quantity', 'Value', 'Interpretation'],
  [['AP change (B1 − B0)', '−0.001916', 'news worse'], ['Brier improvement, Brier(B0) − Brier(B1)', '−0.000284', 'news worse'],
   ['Paired block-bootstrap Brier interval', '[−0.000341, −0.000230]', 'excludes zero, against news'],
   ['Folds improving (AP / Brier)', '0 of 5', 'gate failed'], ['Promotion gates passed', '0 of 5', 'B0 selected']],
  [0.42, 0.30, 0.28]));
add(P('All five gates failed, so, as preregistered, only B0 was evaluated on the holdout: AP 0.171628 and Brier 0.107107 on 211,718 rows from 300 markets. That number is an absolute market-only benchmark, not an estimate of news value. One protocol deviation affects it: the holdout builder printed the positive-label count before the consumption receipt was written. Weights and formulas were already frozen, and the deviation is recorded (Appendix B).'));
add(H2('4.3 How large a news effect is ruled out'));
add(P('A failed gate shows only that no gain was found. To bound the gain the data still allow, the 2,290 markets that contribute out-of-fold rows were resampled as clusters, 2,000 times, over the frozen out-of-fold predictions; this post hoc analysis reads no holdout and refits nothing.'));
add(Tbl('Market-clustered bootstrap of the news increment on 1,460,454 development out-of-fold rows from 2,290 markets. Improvements are B0 minus B1 for Brier and log loss; the AP change is B1 minus B0. Positive values would favour news.',
  ['Quantity', 'Point', '95% interval', 'One-sided 95% upper bound'],
  [['Brier improvement', '−0.000284', '[−0.000395, −0.000179]', '−0.000196'],
   ['Average-precision change', '−0.00192', '[−0.00333, −0.00052]', '−0.00075'],
   ['Log-loss improvement (nats)', '−0.00098', '[−0.00137, −0.00059]', '−0.00066']],
  [0.34, 0.16, 0.28, 0.22]));
add(P('The one-sided 95% upper bound of the Brier improvement is below zero, conditional on this cohort and resampling design; markets sharing events or dates may be dependent, so the interval may be somewhat narrow. For scale, B0’s Brier skill over climatology is 0.00210, and the bound is about 9% of that skill. Before any label was read, a frozen simulation estimated how often a true effect would pass all five gates: 7% for a “very small” effect (Brier +0.0001), 33% for “small”, 86% for “moderate” (Brier +0.0005) and 99.8% for “clear”. Every registered scenario lies above the observed upper bounds (Figure 1), so the null is informative about the effect sizes the study was designed to detect, for lexically associated article counts over 60–1,440 minutes; it does not show that news has no value in general.'));
add(Figure('docs/figures/fig4_news_bound.png', 6.0, 'Observed news effect on Brier score with its 95% market-clustered interval, against the effect sizes registered before labels were read and their simulated probabilities of passing all five gates.'));
add(H2('4.4 Richer news features (V4) and diagnostics (V5, V6)'));
add(P('V4 tested a nested ladder of richer news features, news volume (B1), relevance and seven-day novelty (B2), and publisher diversity with cross-publisher headline diffusion (B3), prospectively on 470 Polymarket contracts from 6 September to 30 October 2026. Success required at least 0.001 nats of log-loss improvement for B3 over B0, with a positive bootstrap lower bound and Brier and venue guards. At close-out the frozen label-blind audit stopped: it required every article’s ingestion status to be `ok`, but only 40% of the 186,753 sealed article rows had that status, the same mix on which the frozen models had been trained. Before any V4 outcome was read, a versioned audit (v2) accepting any recorded status was hash-locked, a disclosed deviation (Appendix B). It passed, and the frozen chain ran once on 31 October on 47,279 rows from 470 contracts (Table 4).'));
add(P('Richer news did not help: B3’s log loss was 0.0008 nats worse than B0’s, with a 95% event-clustered interval of [−0.0052, 0.0012]. Every model in the ladder transferred poorly to this period (AUC about 0.40, mean forecast 0.17 against an observed rate of 0.085), so the test shows that richer news did not rescue a market-history model that failed to transfer, rather than giving a clean estimate of the value of news.'));
add(Tbl('V4 confirmatory result, primary population (price age at most 30 minutes). Improvements are B0 minus B3, so positive favours B3. 47,279 rows from 470 contracts; evaluated once on 31 October after the disclosed audit revision.',
  ['Quantity', 'Value', 'Frozen condition', 'Met?'],
  [['Log-loss improvement, B0 − B3 (nats per row)', '−0.00078', 'at least 0.001', 'No'],
   ['95% bootstrap interval of the improvement', '[−0.0052, 0.0012]', 'lower bound above zero', 'No'],
   ['Brier improvement, B0 − B3', '−0.00014', 'at least −0.0005', 'Yes'],
   ['Venue-level estimates (Polymarket)', '−0.00078', 'non-negative where at least 30 clusters', 'No'],
   ['Positive claim supported', 'No', 'all four conditions', '—']],
  [0.40, 0.20, 0.28, 0.12]));
add(P('Exploratory work on opened data (V5) traced the apparent benefit of a residual-news model to its controls: adding the news mechanism itself changed log loss by −0.000871 nats [−0.001457, −0.000208]. A contract-aware news-linking effort (V6) failed its strict link audit. Under strict availability rules the answer to RQ1 is therefore **no**: simple news representations did not add value beyond market history.'));

add(H1('5 Track B: Quote-Change Forecasting Method'));
add(H2('5.1 Why the target changed'));
add(P('The project first tried to forecast the *exact* midpoint 30 minutes ahead. Because most midpoints do not change, the persistence forecast is very hard to beat on mean absolute error. In the live run a ridge model was 30.9% worse than persistence on 257 observed outcomes. The project therefore switched to a binary target, **whether** the midpoint 30 minutes later will differ from the current one, which is forecast as a probability and scored with proper scoring rules.'));
add(H2('5.2 Target and eligibility'));
add(P('At each five-minute grid time *t*, the target is 1 if the recorded YES midpoint at *t* + 30 minutes differs from the midpoint at *t* by more than 10⁻¹², and 0 otherwise. Forecasts and targets are issued only when the current and endpoint quotes pass the freshness and validity rules of Section 3.2.'));
add(P('**Why forecast quote activity.** The target resolves every 30 minutes, so a frozen model can be tested on tens of thousands of outcomes within days, a practical testbed for evaluate-once protocols. A calibrated activity forecast could help schedule monitoring or data collection, and a study of external information must first control for the predictable, mechanical part of price movement. These are motivations, not demonstrated benefits.'));
add(P('**What the target misses.** A one-tick move and a large repricing both count as 1, and a move that reverses before the endpoint counts as 0. The target says nothing about direction, event resolution or profit after spreads and fees.'));
add(H2('5.3 Features'));
add(P('The primary model (**row_hgb7**) uses 18 features computed from quotes received by decision time (Appendix A):'));
add(B('the midpoint and its log-odds, and the spread;'));
add(B('the source and receive ages of the quote;'));
add(B('the hour of day, encoded as sine and cosine;'));
add(B('the number and fraction of valid quote states in the last 30 minutes;'));
add(B('signed and absolute midpoint changes over 5, 15 and 30 minutes, each with an explicit missing flag.'));
add(P('The live-runtime model (**V03 hgb7**) drops the four age and activity-count features, which depend on archive receive clocks a live system cannot reproduce. No news, order-depth or contract-identity features are used.'));
add(H2('5.4 Models and baselines'));
add(P('The forecaster is a histogram gradient-boosting classifier (100 iterations, learning rate 0.05, at most 7 leaves, minimum leaf 100, L2 penalty 10). The fixed baselines were fitted on the same training rows:'));
add(B('a smoothed global event rate;'));
add(B('a per-contract rate shrunk toward the global rate with 20 pseudo-observations;'));
add(B('an **activity logistic regression** on nine features (midpoint, spread, log valid-update count, and absolute 5-, 15- and 30-minute changes with their missing flags), the primary comparator;'));
add(B('the earlier frozen booster (**legacy HGB**), loaded from its own earlier bundle rather than refit;'));
add(B('for the V03 live model only, its own full-feature logistic regression on the V03 features.'));
add(P('row_hgb7 was selected and refit on 7–9 May 2026 data from 50 development contracts before any later block was retrieved. Nothing has been refit, recalibrated or re-thresholded since.'));
add(P('The primary comparison is between two complete systems: row_hgb7 uses 18 inputs and activity logistic regression nine of them, so it shows that the booster forecasts better than the specified reference, but not whether the gain comes from nonlinearity or from the extra inputs. The V03 comparison on matched inputs is better controlled but is a separate model.'));
add(H2('5.5 Evaluation protocol'));
add(P('Each evaluation block follows the same sequence. First the protocol is frozen, including the primary comparison and the pass rule. Then the cohort is selected outcome-blind, the hourly archive files are captured (with one permitted retry for transport failures), and finally the block is evaluated exactly once. The primary metric is matched, row-weighted log loss of row_hgb7 against activity logistic regression. Each block’s pass rule was frozen with its protocol, and the two June rules differ:'));
add(B('**1–7 June:** on the development cohort, the booster’s log loss is below both activity logistic regression and the global rate, and its Brier score is no higher than logistic regression’s. A contract-clustered bootstrap interval was added before evaluation as an analysis-only secondary result, not a pass condition;'));
add(B('**8–14 June:** the same conditions, and in addition the 95% contract-clustered bootstrap interval for the log-loss gain over activity logistic regression must have a lower bound above zero (5,000 resamples of whole contracts).'));
add(P('Date-clustered intervals, win counts, nonoverlapping and strict-path subsets, and missing-outcome bounds are secondary results.'));

add(H1('6 Track B: Historical Results'));
add(H2('6.1 Development and early replications'));
add(P('An earlier frozen booster cut log loss by 18.1% against activity logistic regression on 28–30 April. On the seven-day replication of 13–19 May, row_hgb7 achieved 0.3583 against 0.4524 (20.8%), but for six training-excluded contracts the gain was only 3.5%, which motivated the test on new contracts in Section 6.3.'));
add(H2('6.2 Unopened week, same cohort: 1–7 June'));
add(P('No earlier study had read any June quote data. All 168 hourly files were captured; only 20 of the 60 fixed contracts were still quoting, and they were kept unchanged rather than replaced.'));
add(Tbl('Matched results, 1–7 June, development cohort (18 contributing contracts, 16,453 known outcomes, 2,068 positives). Lower log loss and Brier are better.',
  ['Model', 'Log loss', 'Brier', 'AUC', 'Booster log-loss reduction'],
  [['**row_hgb7**', '**0.2931**', '**0.0848**', '0.835', '—'], ['Activity logistic', '0.3523', '0.1003', '—', '16.8%'],
   ['Legacy HGB', '0.3285', '—', '—', '10.8%'], ['Global rate', '0.3854', '—', '0.500', '24.0%']],
  [0.28, 0.16, 0.16, 0.14, 0.26]));
add(P('All registered pass conditions held. The secondary contract-clustered interval for the gain over activity logistic regression is [0.039, 0.080] nats. With all 20 contributing contracts (log loss 0.2948 against 0.3527) the booster won on 7 of 7 dates and 17 of 20 contracts, and the nonoverlapping and strict subsets agree. Over 19,304 issued forecasts the worst-case missing-outcome bounds are [−0.001, +0.100] nats, slightly negative at the lower end under the most adverse assignment of the 2,851 unknown endpoints.'));
add(H2('6.3 Never-used contracts: 8–14 June'));
add(P('To test transfer to new identities, 40 contracts were selected by metadata only from an identifier range disjoint from every earlier cohort: binary, at most one per event, open all week, and spanning sports, politics, finance, technology and geopolitics. A local DNS outage failed 74 hourly downloads on both permitted attempts; before any evaluation they were refetched outcome-blind into a separate directory, leaving 165 of 168 hours. This exceeds the single-retry rule and is recorded as a deviation.'));
add(Tbl('Matched results, 8–14 June, never-used contracts (35 contributing contracts, 35,218 known outcomes, 8,830 positives).',
  ['Model', 'Log loss', 'Brier', 'AUC', 'Booster log-loss reduction'],
  [['**row_hgb7**', '**0.4208**', '**0.1335**', '0.827', '—'], ['Activity logistic', '0.4943', '0.1584', '0.756', '14.9%'],
   ['Legacy HGB', '0.4873', '0.1547', '0.785', '13.6%'], ['Global / contract rate', '0.5843', '0.1945', '0.500', '28.0%'],
   ['V03 hgb7 (live model)', '0.4270', '0.1358', '0.825', '19.7% vs its full logistic'] ],
  [0.28, 0.16, 0.16, 0.14, 0.26]));
add(P('All registered pass conditions held, including the positive bootstrap lower bound (Figure 2). The contract-clustered interval for the gain over logistic regression is [0.033, 0.119] nats, the booster won on 7 of 7 dates and 27 of 35 contracts, and the worst-case missing-outcome bounds over all 39,656 issued forecasts, [+0.009, +0.114] nats, stay positive. The registered secondary analysis of the V03 live model gave a 19.7% reduction ([0.066, 0.147]), which cleared it for the live test in Chapter 7.'));
add(Figure('docs/figures/fig1_evidence_ladder.png', 6.0, 'Log-loss gain of the frozen booster over logistic regression on the two unopened June blocks, with 95% contract-clustered bootstrap intervals. Contributing contracts are given in parentheses.'));
add(H2('6.4 Calibration, drivers and category breakdown'));
add(P('Figure 3 shows that on 8–14 June both models are close to the diagonal below a forecast of 0.2, where most forecasts lie, and both under-predict somewhat in the upper deciles. On 1–7 June both over-forecast (expected calibration error 0.046 for the booster and 0.052 for logistic regression), consistent with a lower change rate in June than in May. The booster’s forecasts are sharper, with decile means from 0.02 to 0.59 against 0.08 to 0.44. No recalibration was applied, since that would need a new frozen version and a new block.'));
add(Figure('docs/figures/fig2_calibration_june8_14.png', 3.6, 'Reliability diagram for the booster and logistic regression on 8–14 June (decile bins of forecast probability).'));
add(P('**What the booster relies on.** The frozen booster was re-applied to the 1–7 June ledger and each feature group permuted jointly, ten times (Figure 4). Recent midpoint moves dominate: permuting the 30-, 5- and 15-minute groups raises log loss by 0.021, 0.019 and 0.018 nats, followed by price level (0.015), update activity (0.008) and spread (0.006); quote freshness and time of day contribute almost nothing. Jointly permuting the nine inputs that only the booster sees raises its log loss by 0.013 nats, 21% of its 0.059-nat advantage over logistic regression. This is a sensitivity analysis of a fitted model, not a decomposition of the gap into extra inputs and nonlinearity.'));
add(Figure('docs/figures/fig5_booster_drivers.png', 6.0, 'Permutation importance of feature groups for the frozen booster on 1–7 June (16,453 forecasts). Labels give each increase as a share of the booster’s log-loss gap over logistic regression.'));
add(P('A keyword rule fixed before scores were joined assigned contracts to categories. The booster has lower log loss than logistic regression in every observed category in both weeks (Table 7), but most categories hold two to twelve contracts, so these are descriptions, not tests.'));
add(Tbl('Booster log-loss reduction against activity logistic regression by category (descriptive, post hoc keyword rule).',
  ['Block / category', 'Contracts', 'Known', 'Reduction', 'Contracts won', '95% contract CI (nats)'],
  [['June 1–7 sports', '5', '5,670', '22.1%', '5/5', '[0.038, 0.103]'], ['June 1–7 finance/crypto', '6', '3,670', '17.5%', '5/6', '[0.033, 0.101]'],
   ['June 1–7 politics', '5', '5,425', '11.8%', '4/5', '[0.001, 0.075]'], ['June 1–7 entertainment', '2', '1,688', '15.9%', '2/2', 'too few'],
   ['June 8–14 sports', '12', '11,498', '10.3%', '9/12', '[0.001, 0.096]'], ['June 8–14 finance/crypto', '8', '7,167', '12.1%', '6/8', '[−0.028, 0.248]'],
   ['June 8–14 politics', '6', '6,927', '14.3%', '5/6', '[−0.016, 0.116]'], ['June 8–14 geopolitics', '4', '6,335', '28.8%', '4/4', '[0.044, 0.241]'],
   ['June 8–14 tech/science', '3', '2,680', '14.7%', '2/3', '[−0.038, 0.273]'], ['June 8–14 entertainment', '2', '611', '1.7%', '1/2', 'too few']],
  [0.27, 0.12, 0.11, 0.13, 0.14, 0.23]));
add(P('**Post hoc robustness checks.** Four further checks used the stored June forecasts, with definitions fixed before the first run; no frozen model was refit or its forecasts regenerated (Appendix C).'));
add(P('*Joint dependence.* A two-way bootstrap that resamples contracts and dates independently (Owen, 2007) keeps the gain over activity logistic regression above zero: [0.031, 0.092] nats on 1–7 June and [0.022, 0.126] on 8–14 June. The gain over the legacy booster on 1–7 June does not survive ([−0.007, 0.092]).'));
add(P('*Coverage.* Of the 96,600 scheduled decisions on 1–7 June, 48.0% fell after the contract’s listed end date and most of the rest in contract-days with no issued forecast; on 8–14 June the main loss was contract-days without valid quotes. The gain does not shrink on poorly covered contract-days (0.071 and 0.088 nats in the lowest coverage third, against 0.058 and 0.069 in the highest), so the issued-row diagnostics show no attenuation with lower coverage; performance on decisions that were never issued is unidentified.'));
add(P('*An online contract rate.* None of the fixed baselines learns from a contract’s own outcomes. An online reference does: at each decision it takes the share of changes among the contract’s matured outcomes (decisions at least 35 minutes earlier), shrunk toward the stored global rate with 20 pseudo-observations, with no fitting or tuning (Table 8).'));
add(Tbl('Post hoc comparison of the frozen booster with an online contract rate built from matured outcomes. Gains are rate minus booster; positive values favour the booster. The May and 1–7 June blocks use contracts from the booster’s training cohort.',
  ['Block', 'Booster LL', 'Online rate LL', 'LL gain (nats)', '95% contract CI', '95% contract × date CI', 'Brier gain [95% CI]', 'AUC booster / rate', 'Won: contracts; dates'],
  [['13–19 May', '0.3583', '0.3922', '0.034 (8.6%)', '[0.008, 0.060]', '[0.002, 0.071]', '0.0170 [0.0075, 0.0275]', '0.837 / 0.807', '18/30; 7/7'],
   ['1–7 June', '0.2931', '0.3143', '0.021 (6.7%)', '[−0.006, 0.057]', '[−0.018, 0.073]', '0.0094 [0.0007, 0.0231]', '0.835 / 0.790', '11/18; 7/7'],
   ['8–14 June', '0.4208', '0.4231', '0.002 (0.5%)', '[−0.028, 0.033]', '[−0.040, 0.041]', '0.0080 [−0.0016, 0.0178]', '0.827 / 0.824', '17/35; 3/7']],
  [0.09, 0.10, 0.09, 0.09, 0.11, 0.12, 0.15, 0.11, 0.14]));
add(P('On the 35 new contracts the online rate nearly matches the booster’s log loss and AUC, and both intervals include zero; on the development contracts, also used to train the booster, the booster is ahead, clearly so on 13–19 May. Intervals this wide show that the block cannot separate the two forecasts, not that they are equivalent.'));
add(P('*Outcome history.* With fewer than 12 matured outcomes the booster beats the online rate by 0.07–0.14 nats in all three blocks; with 12 or more on the new contracts the difference is about zero. These early decisions are under 2% of forecasts but carry about 82% of the small aggregate gain on the new contracts.'));
add(P('These post hoc results suggest that quote features matter most when little contract history is available, and that the booster beats the specified fixed baselines but not every simple reference. Whether pooled information adds value beyond each contract’s own history needed new data (Section 6.6).'));
add(H2('6.5 A further unopened fortnight: 15–28 June'));
add(P('A third test on 15–28 June used 21 further never-used contracts, frozen from metadata in a new identifier range before any price was read, and scored both frozen models once under the June 8–14 rule (Table 9).'));
add(Tbl('Matched results, 15–28 June, never-used contracts. Gains are comparator minus booster log loss.',
  ['Model vs comparator', 'Log loss', 'Reduction', '95% contract CI (nats)', 'Known / missing', 'Contracts won', 'Frozen rule'],
  [['row_hgb7 vs activity logistic', '0.3859 / 0.4249', '9.2%', '[0.022, 0.058]', '68,046 / 1,639', '17/21', 'Pass'],
   ['V03 hgb7 vs its full logistic', '0.3883 / 0.4411', '12.0%', '[0.023, 0.085]', '68,700 / 1,336', '16/21', 'Pass']],
  [0.21, 0.13, 0.13, 0.16, 0.14, 0.12, 0.11]));
add(P('Both frozen rules were met. row_hgb7 had log loss 0.3859 against 0.4249 (9.2% lower), was better on 17 of 21 contracts and all 14 dates, and had missing-outcome bounds of [0.029, 0.058] nats. V03 hgb7 had 0.3883 against 0.4411 for its full logistic regression. Two results temper this: both boosters had lower AUC than their logistic comparators (0.744 against 0.783 for row_hgb7), so the gain reflects better probability levels rather than ranking, and the gain over the legacy booster, 0.025 nats, has an interval that includes zero.'));
add(H2('6.6 Confirmatory test: pooled information beyond a contract’s own history'));
add(P('Section 6.4 left open whether information pooled across contracts adds value beyond each contract’s own outcome history. A new cycle developed candidates on the four opened blocks only, combining the frozen booster, the online rate and the number of matured outcomes, and selected by leave-one-block-out log loss the simplest: a logistic regression on the logit of the booster, the logit of the rate and log(1 + matured outcomes) (stack_lin). Held out, it beat both components on every block.'));
add(P('The protocol, model, code and cohort rule were hash-locked before any test contract was chosen. The test used 29 June–12 July, a period no study had read, and 53 contracts from a new identifier range, selected from metadata alone. The pass rule required lower log loss than the online rate, a Brier score no higher, and a contract × date bootstrap lower bound above zero (Table 10).'));
add(Tbl('Confirmatory history-stack test, 29 June–12 July, 51 contributing new contracts, 65,458 known outcomes. Gains are comparator minus candidate log loss.',
  ['Candidate vs comparator', 'Log loss', 'Reduction', '95% contract × date CI (nats)', '95% contract CI (nats)', 'AUC', 'Role'],
  [['stack vs online rate', '0.3348 / 0.3863', '13.3%', '[0.034, 0.071]', '[0.037, 0.066]', '0.859 / 0.794', 'Primary: pass'],
   ['stack vs row_hgb7', '0.3348 / 0.3649', '8.3%', '[0.011, 0.052]', '[0.013, 0.049]', '0.859 / 0.799', 'Secondary'],
   ['row_hgb7 vs online rate', '0.3649 / 0.3863', '5.5%', '[−0.014, 0.057]', '[−0.008, 0.050]', '0.799 / 0.794', 'Secondary'],
   ['stack vs activity logistic', '0.3348 / 0.4255', '21.3%', '[0.068, 0.116]', '[0.072, 0.111]', '0.859 / 0.781', 'Secondary']],
  [0.19, 0.14, 0.13, 0.16, 0.14, 0.12, 0.12]));
add(P('The frozen rule was met: log loss 0.3348 against 0.3863 for the rate, lower on 42 of 51 contracts and on all 14 dates. The gain was positive even with 48 or more matured outcomes (0.052 nats), so the stack kept improving on the rate after a contract’s history had accumulated. The stack also beat the booster alone, whose own gain over the rate had intervals that include zero: the two components are comparable but not redundant.'));
add(P('Two qualifications apply. The frozen capture limit of 32 MiB per hour was exceeded in 134 of 336 hours, mostly busy ones, so the result describes the remaining 60% of hours; and the worst-case missing-outcome bounds, [−0.003, 0.083] nats, include zero.'));

add(H2('6.7 Where the gain comes from: segment discovery and replication'));
add(P('A post hoc analysis asked whether the booster’s advantage is concentrated in particular markets or states. Thirty segments (category, hour, price level, spread, recent activity, a midpoint move in the last 30 minutes, outcome history and time to end) were fixed before any score. A segment was flagged if its interaction, the gain in the segment minus the gain elsewhere, excluded zero on the three earlier blocks pooled, and was then checked on two later blocks with a Holm correction. All blocks had been opened, so this is descriptive.'));
add(Tbl('Booster gain over each comparator by recent quote movement, pooled 15–28 June and 29 June–12 July (133,504 known outcomes, 72 contracts). Gains are comparator minus booster log loss; intervals resample contracts.',
  ['Segment', 'Share of rows', 'Change rate', 'vs online rate (nats)', 'vs activity logistic (nats)'],
  [['Midpoint moved in last 30 min', '16.9%', '0.551', '+0.088 [0.042, 0.133]', '+0.239 [0.192, 0.291]'],
   ['No move in last 30 min', '83.1%', '0.109', '−0.025 [−0.048, −0.001]', '+0.011 [−0.003, 0.025]']],
  [0.30, 0.13, 0.13, 0.22, 0.22]));
add(P('Ten segments were flagged and eight replicated (Holm-adjusted p = 0.005 each), describing two patterns. The booster’s advantage over the online rate is concentrated just after a quote move, where it was positive in all five blocks (0.06 to 0.27 nats), while on quiet rows the rate was as good or slightly better (Table 11). It also grows with the spread: +0.091 nats [0.044, 0.149] where the spread exceeded 0.03, against −0.024 at spreads of 0.01 or less. No category or time of day was flagged.'));
add(H2('6.8 Confirmatory segment test, 13–21 July'));
add(P('Both patterns and the history-stack result were then tested together on new data. A hash-locked protocol stated two primary hypotheses: the booster’s gain over the online rate is larger on rows whose midpoint moved in the previous 30 minutes (H1) and where the spread exceeds 0.03 (H2), each judged by a one-sided contract-clustered bootstrap p-value with a Holm correction. A third hypothesis (H3) re-applied the history-stack rule. The test used 13–21 July and 80 contracts from a new identifier range. Two disclosed changes made before any economic data were read raised the capture and selection read limits (Appendix B). All 216 hours were captured and the evaluation ran once (Table 12).'));
add(Tbl('Confirmatory segment test, 13–21 July, 78 contributing new contracts, 159,283 known outcomes. Gains are online-rate minus candidate log loss (nats); the interaction is the gain in the segment minus the gain on the remaining rows.',
  ['Hypothesis', 'Segment rows (contracts)', 'Gain in segment', 'Gain elsewhere', 'Interaction or gain [95% CI]', 'Holm p', 'Result'],
  [['H1: booster, midpoint moved in last 30 min', '28,289 (72)', '+0.091', '−0.021', '0.113 [0.070, 0.162]', '0.0004', 'Confirmed'],
   ['H2: booster, spread above 0.03', '9,331 (40)', '+0.084', '−0.007', '0.091 [0.040, 0.141]', '0.0004', 'Confirmed'],
   ['H3: stack vs online rate, all rows', '159,283 (78)', '+0.039', '—', '0.039 [0.028, 0.051] (contract × date)', '—', 'Pass']],
  [0.22, 0.13, 0.11, 0.12, 0.19, 0.10, 0.13]));
add(P('Both segment hypotheses were confirmed: after a recent move the booster beat the rate by 0.091 nats, against −0.021 on quiet rows, and where the spread exceeded 0.03 by 0.084 against −0.007. The history stack passed again, with log loss 0.3339 against 0.3730 for the rate (10.5% lower) and missing-outcome bounds of [0.028, 0.045] nats, which exclude zero. A routing rule that switches between booster and rate was worse than the stack by 0.022 nats, so a learned combination dominates a hard switch.'));
add(P('By market state (Table 13), active rows, with a recent move or a spread above 0.03, made up 21.4% of the test. There the booster’s log loss was 11.0% below the contract’s rate and the stack’s 15.7% below it, 28.6% below activity logistic regression. In quiet rows the rate was the better single forecaster, but the stack was still 6.7% better. Pooled quote information helps most when a market is moving, which motivates, but does not yet demonstrate, use for monitoring.'));
add(Tbl('Log loss by market state, 13–21 July (descriptive breakdown of the test in Table 12; states may overlap). Reductions are relative to the online contract rate.',
  ['State', 'Share of rows', 'Change rate', 'Online rate', 'Booster', 'Stack', 'Booster vs rate', 'Stack vs rate'],
  [['Active: moved or spread above 0.03', '21.4%', '0.502', '0.7273', '0.6473', '0.6130', '11.0%', '15.7%'],
   ['Moved in last 30 min', '17.8%', '0.553', '0.7641', '0.6728', '0.6362', '11.9%', '16.7%'],
   ['Spread above 0.03', '5.9%', '0.419', '0.6595', '0.5753', '0.5523', '12.8%', '16.2%'],
   ['Quiet: neither', '78.6%', '0.096', '0.2766', '0.3002', '0.2581', '−8.5%', '6.7%'],
   ['All rows', '100%', '0.183', '0.3730', '0.3744', '0.3339', '−0.4%', '10.5%']],
  [0.22, 0.10, 0.10, 0.10, 0.10, 0.10, 0.14, 0.14]));
add(H2('6.9 A segment-aware stack, 22 July–8 August'));
add(P('The confirmed segments suggest letting the combination depend on market state. A new cycle, developed on opened data, compared three such stacks and selected a shallow gradient-boosted combiner (seg_hgb) on the booster, the rate, history length, activity logistic regression, the move indicator, the spread and the size of the last move; its held-out log loss was 0.0059 nats below stack_lin, above the go threshold of 0.001.'));
add(P('The archive ends on 10 August, and the only unused multi-day window, 22 July–8 August, is the calendar period of the consumed V3.1 holdout. The user authorized it as a disclosed deviation (Appendix B); V3.1, v1 and V4 markets stay excluded and no V3.1 file was read. Protocol and model were hash-locked before 54 new contracts were chosen from metadata. The pass rule required lower log loss than the frozen stack, a Brier score no higher and a contract × date lower bound above zero. All 432 hours were captured and the evaluation ran once (Table 14).'));
add(Tbl('Segment-aware stack test, 22 July–8 August, 52 contributing new contracts, 134,341 known outcomes. Gains are comparator minus candidate log loss.',
  ['Candidate vs comparator', 'Log loss', 'Reduction', '95% contract × date CI (nats)', 'After a move (nats)', 'No recent move (nats)', 'Role'],
  [['seg_hgb vs stack_lin', '0.3006 / 0.3083', '2.5%', '[0.002, 0.014]', '+0.023', '+0.005', 'Primary: pass'],
   ['seg_hgb vs online rate', '0.3006 / 0.3497', '14.0%', '[0.028, 0.076]', '+0.186', '+0.022', 'Secondary'],
   ['stack_lin vs online rate', '0.3083 / 0.3497', '11.9%', '[0.024, 0.064]', '+0.162', '+0.017', 'Secondary'],
   ['row_hgb7 vs online rate', '0.3417 / 0.3497', '2.3%', '[−0.022, 0.045]', '+0.135', '−0.017', 'Secondary']],
  [0.19, 0.14, 0.13, 0.16, 0.13, 0.13, 0.12]));
add(P('The frozen rule was met: seg_hgb had log loss 0.3006 against 0.3083, a gain of 0.0076 nats, and was better on 17 of 18 dates. The stack beat the rate for a third time (interval [0.024, 0.064] nats), and the booster’s gain over the rate was again concentrated after moves (interaction 0.152 nats). Only 52.5% of scheduled decisions were issued, and the worst-case missing-outcome bounds, [−0.001, 0.017] nats, include zero. The improvement is clear but small; most of the value had already come from combining the booster with the rate.'));
add(H2('6.10 Recent state-of-the-art learners as baselines'));
add(P('To check that these gains are not an artefact of weak references, the recent learners of Section 2.6 were run on the seven opened blocks under a protocol frozen before any baseline was scored (compute-only amendments in Appendix B). It is a descriptive benchmark, scored once after a label-free completeness check. Tier A replaces row_hgb7 with TabM, RealMLP, TabICL and CatBoost (Prokhorenkova, Gusev, Vorobev, Dorogush and Gulin, 2018) on the same 9,212 training rows and 18 features. Tier B forecasts each contract’s outcome series zero-shot from the information the online rate uses; the slower Sundial and Time-MoE are scored on the half-hour grid (84,044 rows). Tier C trains TabM and RealMLP end-to-end on six blocks and compares them with seg_hgb on 22 July–8 August (Table 15).'));
add(Tbl('Recent baselines on the seven opened blocks (descriptive; scored once). Log losses are means over blocks; blocks better counts blocks in which the baseline’s log loss is below the reference’s.',
  ['Tier and model', 'Venue', 'Reference', 'Log loss (model / reference)', 'AUC (model / reference)', 'Blocks better'],
  [['A: TabM', 'ICLR 2025', 'row_hgb7', '0.8229 / 0.3627', '0.652 / 0.807', '0 of 7'],
   ['A: RealMLP', 'NeurIPS 2024', 'row_hgb7', '0.4563 / 0.3627', '0.718 / 0.807', '0 of 7'],
   ['A: TabICL', 'ICML 2025', 'row_hgb7', '0.4331 / 0.3627', '0.760 / 0.807', '0 of 7'],
   ['A: CatBoost (default)', 'NeurIPS 2018', 'row_hgb7', '0.4174 / 0.3627', '0.769 / 0.807', '0 of 7'],
   ['B: Moirai-MoE, all rows', 'ICML 2025', 'Online rate', '0.5599 / 0.3703', '–', '0 of 7'],
   ['B: Sundial, half-hour grid', 'ICML 2025', 'Online rate', '0.3526 / 0.3691', '0.862 / 0.814', '7 of 7'],
   ['B: Time-MoE, half-hour grid', 'ICLR 2025', 'Online rate', '0.3908 / 0.3691', '0.835 / 0.814', '1 of 7'],
   ['B: Moirai-MoE, half-hour grid', 'ICML 2025', 'Online rate', '0.5517 / 0.3691', '0.797 / 0.814', '0 of 7'],
   ['C: TabM end-to-end', 'ICLR 2025', 'seg_hgb', '0.3411 / 0.3006', '0.849 / 0.885', '22 Jul–8 Aug only'],
   ['C: RealMLP end-to-end', 'NeurIPS 2024', 'seg_hgb', '0.3241 / 0.3006', '0.869 / 0.885', '22 Jul–8 Aug only']],
  [0.24, 0.12, 0.12, 0.19, 0.17, 0.16]));
add(P('No tabular baseline beat row_hgb7 on any block; every interval lay below zero and AUC was lower too. End-to-end, both networks were worse than seg_hgb, RealMLP by 0.0234 nats [−0.040, −0.011] and TabM by 0.0405 [−0.054, −0.029]. The competitive result was Sundial, which beat the online rate on every block with higher AUC, though the stack was better still (0.3068 against 0.3270 on 22 July–8 August). Time-MoE ranked rows well but was poorly calibrated, and Moirai-MoE was worse on both counts.'));
add(P('Three limits apply: no baseline was tuned and Tier A used random rather than chronological internal validation; Tier C trained on a 100,000-row subsample while seg_hgb used all rows; and Tier B tests one adaptation of real-valued forecasters to a binary series. Under these default configurations the four tabular learners did not beat row_hgb7, and Sundial improved the history-only reference while the stack remained better on their three shared blocks; none of this shows superiority over tuned alternatives, and whether Sundial would help inside a stack was not tested.'));
add(H2('6.11 A development study: more training data and change-history features'));
add(P('A final development cycle, on the seven opened blocks only and with code committed before any score (Appendix C), examined three ideas: a single booster trained end-to-end on the known outcomes of the six training blocks of each fold; five change-history inputs (log time since the last 5-minute change, decayed change counts with half-lives of 30 minutes, 2 hours and 12 hours, and changes in the previous 24 hours) in the spirit of self-exciting processes (Hawkes, 1971) but not a fitted Hawkes model, plus two market-wide activity inputs; and a per-contract logit offset updated online by a one-step Laplace approximation, as in dynamic generalised linear models (West, Harrison and Migon, 1985; McCormick, Raftery, Madigan and Burd, 2012). Hyperparameters were fixed, and candidates were scored by leave-one-block-out log loss over the five new-contract blocks (Table 16).'));
add(Tbl('Development study (opened blocks only): leave-one-block-out log loss, mean over the five new-contract blocks. Gains are seg_ref minus candidate log loss.',
  ['Candidate', 'Inputs', 'Mean log loss', 'Gain vs seg_ref (nats)', 'Blocks better than seg_ref'],
  [['Online rate', 'Contract’s matured outcomes', '0.3771', '−0.0489', '–'],
   ['row_hgb7 (frozen)', '18 quote features', '0.3775', '−0.0494', '–'],
   ['seg_ref', 'seg_hgb design, refit per fold', '0.3282', 'reference', '–'],
   ['e2e', '18 features, rate, history', '0.3270', '+0.0011', '3 of 5'],
   ['e2e_hx', 'e2e + change history', '0.3150', '+0.0132', '5 of 5'],
   ['e2e_hx_mkt', 'e2e_hx + market activity', '0.3159', '+0.0122', '5 of 5'],
   ['pp_cp', 'e2e_hx_mkt + online contract offset', '0.3229', '+0.0052', '4 of 5'],
   ['pp_cp_seg', 'seg_ref + online contract offset', '0.3234', '+0.0047', '4 of 5']],
  [0.15, 0.31, 0.14, 0.20, 0.20]));
add(P('More data alone (e2e) roughly matched seg_ref. The change-history inputs gave the clear gain: e2e_hx scored 4.0% below seg_ref and was better on all seven folds, with intervals above zero (gains 0.0075 to 0.0173 nats), including 0.0124 nats [0.0066, 0.0186] on the only fold trained solely on earlier blocks. The online offset helped seg_ref but hurt its own base model. This is retrospective development evidence on opened blocks, so e2e_hx is a candidate for a new test (Section 9.3), not a confirmed improvement.'));
add(H1('7 Prospective Live Test'));
add(H2('7.1 Design'));
add(P('Historical replay cannot rule out hindsight, such as metadata known only today or reconstructed receive clocks; a prospective test removes both. The live runtime is split into a **source** process and an **emitter** process:'));
add(B('the **source** subscribes to the Polymarket WebSocket for the cohort and polls metadata. It writes every message to an append-only journal in which each record carries the hash of the previous one;'));
add(B('the **emitter** reads that journal and, at each five-minute grid time, issues a forecast from the frozen V03 model or records an abstention with reasons, at least 250 ms before the grid time.'));
add(P('An evaluator scores the forecasts once, after the window closes, against endpoints from the same journal. The cohort is 30 active, binary contracts with at least $10k of 24-hour volume, chosen by metadata only, one per event and disjoint from every earlier cohort.'));
add(H2('7.2 Engineering problems and their solutions'));
add(B('**Unreliable host clock.** The first version failed its readiness rehearsal: the laptop’s time client returned empty packets and the OS stepped the clock back by 110 ms. The runtime now uses its own SNTP client (Mills, Martin, Burbank and Kasch, 2010), accepts an estimate only when at least two servers agree within 50 ms of uncertainty, and carries corrected time on the monotonic clock.'));
add(B('**Memory and latency growth.** Keeping the whole journal in memory (about 317 MB per hour) was replaced by a bounded three-hour store, which matched the unbounded version in 510 of 510 comparisons and cut decision time from 370 ms to 11 ms.'));
add(B('**A thread race in the hash chain.** A clock-probe thread wrote to the journal concurrently and forked the chain, and the emitter’s check stopped the run. Only the event loop now writes, enforced by a test.'));
add(P('A fresh 60-minute rehearsal then passed, with 156 of 180 decisions ready and no chain breaks. The test was activated on 26 October for grids from 27 to 29 October, shortened from seven days to three before any prospective decision to meet this report’s deadline.'));
add(H2('7.3 Operation'));
add(P('Operating losses were recorded rather than repaired:'));
add(B('**First grid and host stall.** All 30 first-grid decisions abstained because inputs were handed over without a final refresh, and a concurrent job pushed the laptop into swapping, so four grids were missed.'));
add(B('**Sleep and reboot.** On 27 October the laptop slept with its lid closed and rebooted, ending the run (V02); the frozen protocol forbids restarting the source. With the user’s authorisation, a separately versioned continuation (**V02b**) reusing every frozen file, the model and the cohort was activated before any V02 outcome was read, for 22,650 scheduled decisions from 27 October 06:35 to 29 October 23:25 UTC. A second lid-closed sleep cost nine grids before sleep was disabled system-wide.'));
add(B('**Venue disconnects.** The venue WebSocket disconnected every three to six hours, each time costing 30 minutes of abstentions under the frozen warmup rule.'));
add(P('These losses reduce coverage but cannot leak information: every failure ended in a recorded abstention or miss rather than a confident wrong forecast, and nothing was backfilled. A forecaster that abstains honestly can be measured, whereas one that silently fills gaps cannot.'));
add(H2('7.4 Results'));
add(P('The live test has no pass rule. Its registered comparison is matched log loss of V03 hgb7 against its full logistic regression and the global rate, reported if at least 100 outcomes, 20 of each class, are known. It ran once, on 30 October (Table 17).'));
add(Tbl('Live V02b test: coverage and matched scores. Gains are comparator minus V03 hgb7 log loss.',
  ['Quantity', 'Value'],
  [['Scheduled decisions', '22,650'], ['Issued on time (coverage)', '15,485 (68.4%)'], ['Abstained, missed or uncommitted', '7,165'],
   ['Known / unknown outcomes (positives)', '12,943 / 2,542 (2,709)'], ['Reporting floor met', 'Yes (27 contracts)'],
   ['Log loss: V03 hgb7 / full logistic / global rate', '0.4470 / 0.5368 / 0.5163'], ['Brier: V03 hgb7 / full logistic / global rate', '0.1403 / 0.1547 / 0.1665'],
   ['AUC: V03 hgb7 / full logistic', '0.745 / 0.726'], ['Relative log-loss reduction vs full logistic', '16.7%'],
   ['95% contract-clustered interval of the gain (nats)', '[0.049, 0.136]'], ['Missing-outcome bounds over all issued forecasts (nats)', '[−0.011, 0.150]']],
  [0.60, 0.40]));
add(P('The reporting floor was met, with 27 of 30 contracts contributing. On 12,943 known outcomes V03 hgb7 had log loss 0.4470 against 0.5368 for its full logistic regression (16.7% lower) and 0.5163 for the global rate, and the best Brier score and AUC. But 16.4% of issued forecasts have no known outcome, and the missing-outcome bounds, [−0.011, 0.150] nats, include zero. With three days, one venue and 68.4% coverage, this is a descriptive prospective result, consistent in direction with the historical blocks.'));

add(H1('8 Discussion'));
add(H2('8.1 What the evidence supports'));
add(P('The answers to RQ1 and RQ2 differ sharply. Simple news counts did not improve a market-history forecaster under strict availability rules, while quote activity was forecast better than the specified baselines on three unopened blocks and, descriptively, live. This is consistent with a market in which public news is quickly priced or too weakly linked to individual contracts to be detected by counts, whereas quote activity is persistent and well summarised by recent changes, spread and price level. A post hoc online contract rate came close to the booster on new contracts (Table 8), but a frozen combination of the quote forecast, the online rate and history length then beat the rate by 13.3% on new contracts and dates, even after many outcomes had matured (Section 6.6). Because the stack also adds fitted calibration and history length, a fitted history-only control is still needed to attribute this gain to the quote input. Later tests located that value just after quote moves and at wide spreads, and a stack that uses these states improved further (Sections 6.8 and 6.9). Default recent tabular learners did not beat the booster, while Sundial improved on the online rate but not on the stack (Section 6.10), and a development study suggests that a contract’s recent change history carries further signal (Section 6.11). Segmenting by market state turned an apparent tie between a pooled model and a contract’s own history into a repeatedly confirmed gain in active states.'));
add(H2('8.2 Threats to validity'));
add(B('**Dependence.** Forecasts from one contract are correlated, so intervals resample whole contracts and the effective sample size is nearer the number of contracts than of rows. A two-way bootstrap over contracts and dates leaves the June gains above zero, but with 7–18 dates per block the date dimension is imprecise.'));
add(B('**Comparator strength.** The June primary comparator uses nine of the booster’s 18 inputs, so the June results show improvement over the specified baselines, not over the strongest reasonable one, and do not attribute the gain to nonlinearity. Later tests used the online rate and the stack as comparators, and Section 6.10 adds untuned recent learners.'));
add(B('**Coverage and selection.** Forecasts were issued for 19,304 of 96,600 scheduled decisions on 1–7 June and 39,656 of 77,280 on 8–14 June, mostly after a contract’s listed end date or on contract-days with no issued forecast. Scores describe the issued, active part of the market, and the missing-outcome bounds do not cover decisions that were never issued. The 29 June–12 July test lost 134 of 336 hours, mostly busy ones, to a capture limit.'));
add(B('**Breadth.** All Track B evidence comes from one venue in 2026, from convenience cohorts that require quotes, and from current metadata; transfer to new event families or another venue has not been tested.'));
add(B('**Protocol deviations.** The DNS refetch, the V3.1 prevalence exposure, the V4 audit revision and the reused calendar period of Section 6.9 are real departures. Each was outcome-blind or made before any metric was computed, and all are disclosed in Appendix B.'));
add(B('**Causal language.** None of the results is causal. Track A estimates predictive value conditional on observable news; information that surfaces first on unobserved channels (private chats, livestreams) remains a confounder.'));

add(H1('9 Conclusions'));
add(H2('9.1 Summary'));
add(P('EventX built a leakage-safe, evaluate-once framework for prediction-market forecasting and applied it to two questions. Simple and richer news features did not improve market-history forecasts. A frozen gradient-boosted quote-change classifier beat activity logistic regression on three unopened blocks, two with never-used contracts (9.2–16.8% lower log loss, intervals above zero). Once-only tests on 181 further new contracts then showed that combining it with each contract’s online rate beats the rate (by 13.3% and 10.5%), that its gain is concentrated after quote moves and at wide spreads, and that a stack using these states improves further (0.3006 against 0.3083). Default recent tabular learners did not beat the booster, and Sundial improved on the online rate but not on the stack. A live test on a laptop issued 68.4% of scheduled forecasts on time, with log loss 16.7% below its logistic baseline on known outcomes, a descriptive result.'));
add(H2('9.2 Limitations'));
add(B('The quote-change target measures activity, not direction, size or profit. A good score does not imply a trading edge.'));
add(B('The June primary comparator is weaker than a matched-input baseline. Of the confirmatory stack tests, one had partial capture and missing-outcome bounds including zero, and the segment-aware test reused the V3.1 holdout calendar period by authorized deviation.'));
add(B('Track A tested count-based and richer news representations, and V4’s base model transferred poorly to its period. The negative results apply to those representations, not to public news in general, and social-media signals were not evaluated within the frozen protocols.'));
add(B('The live test ran on a laptop whose memory pressure, sleeps and network drops reduced coverage. A disciplined server would give a cleaner prospective estimate.'));
add(B('All post hoc analyses are descriptive; none was used to change a frozen model.'));
add(H2('9.3 Recommendations for further work'));
NewList();
add(N('Test the stacks of Sections 6.6 and 6.9 live, where no archive limit or reused calendar period applies, capturing busy hours in full and adding a stronger prespecified history-only comparator; an equivalence test could bound warm-period differences (Lakens, 2017).'));
add(N('Freeze e2e_hx, the change-history booster of Section 6.11, and test it once, prospectively, against seg_hgb under the same pass rule.'));
add(N('Test whether the forecasts help allocate a fixed monitoring budget against uniform, recent-activity and online-rate rankings at equal cost, without assuming free access to fresh quotes.'));
add(N('Compare logistic regression, a GAM and boosting on matched inputs with matched tuning on purged forward folds, to separate nonlinearity from extra inputs, and tune the learners of Section 6.10 the same way.'));
add(N('Test recalibration on a dedicated development split.'));
add(N('Run the live runtime on a dedicated host with a disciplined clock and enough memory, for at least seven days, on a larger metadata-selected cohort.'));
add(N('Extend the target to signed and size-graded quote moves, which are closer to economically meaningful questions, keeping the same once-only protocol.'));
add(N('Re-test news only after contract–event links and first-availability times are independently evidenced, restricted to active market states and with the quote-change model as the market-only baseline.'));
add(N('Widen the evidence to more event families, longer periods and Kalshi, with the number of contracts set by cluster-level power planning; a preliminary estimate is several hundred.'));

// ---------------------------------- references ----------------------------------------
const refs = [
  'Arrow, K.J., Forsythe, R., Gorham, M., Hahn, R., Hanson, R., Ledyard, J.O., Levmore, S., Litan, R., Milgrom, P., Nelson, F.D., Neumann, G.R., Ottaviani, M., Schelling, T.C., Shiller, R.J., Smith, V.L., Snowberg, E., Sunstein, C.R., Tetlock, P.C., Tetlock, P.E., Varian, H.R., Wolfers, J. and Zitzewitz, E. (2008). The Promise of Prediction Markets. *Science*, Vol. 320, No. 5878, pp. 877 – 878.',
  'Brier, G.W. (1950). Verification of Forecasts Expressed in Terms of Probability. *Monthly Weather Review*, Vol. 78, No. 1, pp. 1 – 3.',
  'Cameron, A.C., Gelbach, J.B. and Miller, D.L. (2008). Bootstrap-Based Improvements for Inference with Clustered Errors. *Review of Economics and Statistics*, Vol. 90, No. 3, pp. 414 – 427.',
  'Croxson, K. and Reade, J.J. (2014). Information and Efficiency: Goal Arrival in Soccer Betting. *The Economic Journal*, Vol. 124, No. 575, pp. 62 – 91.',
  'Diercks, A.M., Katz, J.D. and Wright, J.H. (2026). Kalshi and the Rise of Macro Markets. NBER Working Paper No. 34702, National Bureau of Economic Research, Cambridge, Massachusetts.',
  'Engle, R.F. and Russell, J.R. (1998). Autoregressive Conditional Duration: A New Model for Irregularly Spaced Transaction Data. *Econometrica*, Vol. 66, No. 5, pp. 1127 – 1162.',
  'Erickson, N., Purucker, L., Tschalzev, A., Holzmüller, D., Desai, P.M., Salinas, D. and Hutter, F. (2025). TabArena: A Living Benchmark for Machine Learning on Tabular Data. In *Advances in Neural Information Processing Systems 38* (Datasets and Benchmarks Track, San Diego, California, December 2025).',
  'Friedman, J.H. (2001). Greedy Function Approximation: A Gradient Boosting Machine. *Annals of Statistics*, Vol. 29, No. 5, pp. 1189 – 1232.',
  'Gneiting, T. and Raftery, A.E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. *Journal of the American Statistical Association*, Vol. 102, No. 477, pp. 359 – 378.',
  'Gorishniy, Y., Kotelnikov, A. and Babenko, A. (2025). TabM: Advancing Tabular Deep Learning with Parameter-Efficient Ensembling. In *Proceedings of the Thirteenth International Conference on Learning Representations* (ICLR 2025, Singapore, April 24 – 28, 2025).',
  'Grinsztajn, L., Oyallon, E. and Varoquaux, G. (2022). Why Do Tree-Based Models Still Outperform Deep Learning on Typical Tabular Data? *Advances in Neural Information Processing Systems 35* (Datasets and Benchmarks Track), pp. 507 – 520.',
  'Halawi, D., Zhang, F., Yueh-Han, C. and Steinhardt, J. (2024). Approaching Human-Level Forecasting with Language Models. In *Advances in Neural Information Processing Systems 37* (Vancouver, Canada, December 10 – 15, 2024).',
  'Hasbrouck, J. (2007). *Empirical Market Microstructure: The Institutions, Economics, and Econometrics of Securities Trading.* Oxford University Press, New York, 2007.',
  'Hawkes, A.G. (1971). Spectra of Some Self-Exciting and Mutually Exciting Point Processes. *Biometrika*, Vol. 58, No. 1, pp. 83 – 90.',
  'Holzmüller, D., Grinsztajn, L. and Steinwart, I. (2024). Better by Default: Strong Pre-Tuned MLPs and Boosted Trees on Tabular Data. In *Advances in Neural Information Processing Systems 37* (Vancouver, Canada, December 10 – 15, 2024).',
  'Kapoor, S. and Narayanan, A. (2023). Leakage and the Reproducibility Crisis in Machine-Learning-Based Science. *Patterns*, Vol. 4, No. 9, Article 100804.',
  'Karger, E., Bastani, H., Yueh-Han, C., Jacobs, Z., Halawi, D., Zhang, F. and Tetlock, P.E. (2025). ForecastBench: A Dynamic Benchmark of AI Forecasting Capabilities. In *Proceedings of the Thirteenth International Conference on Learning Representations* (ICLR 2025, Singapore, April 24 – 28, 2025).',
  'Kaufman, S., Rosset, S., Perlich, C. and Stitelman, O. (2012). Leakage in Data Mining: Formulation, Detection, and Avoidance. *ACM Transactions on Knowledge Discovery from Data*, Vol. 6, No. 4, Article 15.',
  'Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q. and Liu, T.-Y. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. In *Advances in Neural Information Processing Systems 30* (Long Beach, California, December 4 – 9, 2017), pp. 3146 – 3154.',
  'Kolm, P.N., Turiel, J. and Westray, N. (2023). Deep Order Flow Imbalance: Extracting Alpha at Multiple Horizons from the Limit Order Book. *Mathematical Finance*, Vol. 33, No. 4, pp. 1044 – 1081.',
  'Künsch, H.R. (1989). The Jackknife and the Bootstrap for General Stationary Observations. *Annals of Statistics*, Vol. 17, No. 3, pp. 1217 – 1241.',
  'Lakens, D. (2017). Equivalence Tests: A Practical Primer for t Tests, Correlations, and Meta-Analyses. *Social Psychological and Personality Science*, Vol. 8, No. 4, pp. 355 – 362.',
  'Liu, X., Liu, J., Woo, G., Aksu, T., Liang, Y., Zimmermann, R., Liu, C., Li, J., Savarese, S., Xiong, C. and Sahoo, D. (2025). Moirai-MoE: Empowering Time Series Foundation Models with Sparse Mixture of Experts. In *Proceedings of the 42nd International Conference on Machine Learning* (Vancouver, Canada, July 13 – 19, 2025). PMLR, Vol. 267, pp. 38940 – 38962.',
  'Liu, Y., Qin, G., Shi, Z., Chen, Z., Yang, C., Huang, X., Wang, J. and Long, M. (2025b). Sundial: A Family of Highly Capable Time Series Foundation Models. In *Proceedings of the 42nd International Conference on Machine Learning* (Vancouver, Canada, July 13 – 19, 2025). PMLR, Vol. 267, pp. 39295 – 39317.',
  'López de Prado, M. (2018). *Advances in Financial Machine Learning.* John Wiley & Sons, Hoboken, New Jersey, 2018.',
  'McCormick, T.H., Raftery, A.E., Madigan, D. and Burd, R.S. (2012). Dynamic Logistic Regression and Dynamic Model Averaging for Binary Classification. *Biometrics*, Vol. 68, No. 1, pp. 23 – 30.',
  'Mills, D., Martin, J. (Ed.), Burbank, J. and Kasch, W. (2010). Network Time Protocol Version 4: Protocol and Algorithms Specification. RFC 5905, Internet Engineering Task Force, June 2010.',
  'Niculescu-Mizil, A. and Caruana, R. (2005). Predicting Good Probabilities with Supervised Learning. In *Proceedings of the 22nd International Conference on Machine Learning* (Bonn, Germany, August 7 – 11, 2005). ACM, New York, 2005, pp. 625 – 632.',
  'Ntakaris, A., Magris, M., Kanniainen, J., Gabbouj, M. and Iosifidis, A. (2018). Benchmark Dataset for Mid-Price Forecasting of Limit Order Book Data with Machine Learning Methods. *Journal of Forecasting*, Vol. 37, No. 8, pp. 852 – 866.',
  'Owen, A.B. (2007). The Pigeonhole Bootstrap. *The Annals of Applied Statistics*, Vol. 1, No. 2, pp. 386 – 411.',
  'O’Hara, M. (1995). *Market Microstructure Theory.* Blackwell Publishers, Cambridge, Massachusetts, 1995.',
  'Page, L. and Clemen, R.T. (2013). Do Prediction Markets Produce Well-Calibrated Probability Forecasts? *The Economic Journal*, Vol. 123, No. 568, pp. 491 – 513.',
  'Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M. and Duchesnay, E. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*, Vol. 12, pp. 2825 – 2830.',
  'Polymarket. (2026). Polymarket CLOB and Gamma API Documentation. Online documentation, accessed October 2026.',
  'Prokhorenkova, L., Gusev, G., Vorobev, A., Dorogush, A.V. and Gulin, A. (2018). CatBoost: Unbiased Boosting with Categorical Features. In *Advances in Neural Information Processing Systems 31* (Montréal, Canada, December 3 – 8, 2018), pp. 6638 – 6648.',
  'Qu, J., Holzmüller, D., Varoquaux, G. and Le Morvan, M. (2025). TabICL: A Tabular Foundation Model for In-Context Learning on Large Data. In *Proceedings of the 42nd International Conference on Machine Learning* (Vancouver, Canada, July 13 – 19, 2025). PMLR, Vol. 267, pp. 50817 – 50847.',
  'Shi, X., Wang, S., Nie, Y., Li, D., Ye, Z., Wen, Q. and Jin, M. (2025). Time-MoE: Billion-Scale Time Series Foundation Models with Mixture of Experts. In *Proceedings of the Thirteenth International Conference on Learning Representations* (ICLR 2025, Singapore, April 24 – 28, 2025).',
  'Sirignano, J. and Cont, R. (2019). Universal Features of Price Formation in Financial Markets: Perspectives from Deep Learning. *Quantitative Finance*, Vol. 19, No. 9, pp. 1449 – 1459.',
  'Snowberg, E., Wolfers, J. and Zitzewitz, E. (2007). Partisan Impacts on the Economy: Evidence from Prediction Markets and Close Elections. *Quarterly Journal of Economics*, Vol. 122, No. 2, pp. 807 – 829.',
  'Tetlock, P.C. (2007). Giving Content to Investor Sentiment: The Role of Media in the Stock Market. *Journal of Finance*, Vol. 62, No. 3, pp. 1139 – 1168.',
  'West, M., Harrison, P.J. and Migon, H.S. (1985). Dynamic Generalized Linear Models and Bayesian Forecasting. *Journal of the American Statistical Association*, Vol. 80, No. 389, pp. 73 – 83.',
  'Wolfers, J. and Zitzewitz, E. (2004). Prediction Markets. *Journal of Economic Perspectives*, Vol. 18, No. 2, pp. 107 – 126.',
  'Zhang, Z., Zohren, S. and Roberts, S. (2019). DeepLOB: Deep Convolutional Neural Networks for Limit Order Books. *IEEE Transactions on Signal Processing*, Vol. 67, No. 11, pp. 3001 – 3012.',
];
const references = [H1('References'), ...refs.map(r => new Paragraph({ children: runs(r), spacing: { line: 240, after: 100 }, indent: { left: 567, hanging: 567 }, alignment: AlignmentType.LEFT }))];

// ---------------------------------- appendices ----------------------------------------
compact = true;
const AH = (t) => (headings.push([1, t]), new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT, size: 28, bold: true, color: '000000' })], spacing: { after: 200 } }));
const appA = [AH('Appendix A – Feature Definitions'),
  P('All features are computed from YES-token quotes received at or before the decision time *t*. A quote state is valid when 0 < bid ≤ ask < 1 (locked quotes are allowed) and the spread is at most 0.05. Missing lag values are encoded as zero together with a missing flag.'),
  ...Tbl('The 18 features of row_hgb7. Features marked * are also used by the 14-feature V03 live model.',
    ['Feature', 'Definition'],
    [['midpoint*', '(best bid + best ask) / 2 of the current valid quote'], ['logit_midpoint*', 'ln(m / (1 − m)) of the midpoint'], ['spread*', 'best ask − best bid'],
     ['source_age', 'seconds since the venue timestamp of the current quote'], ['receive_age', 'seconds since the receive timestamp of the current quote'],
     ['hour_sin*, hour_cos*', 'UTC hour of day on the unit circle'], ['log_valid_updates30', 'log(1 + number of valid quote states in the last 30 min)'],
     ['valid_state_fraction30', 'number of valid quote states divided by the number of recorded quote states in the last 30 min'],
     ['delta5*, abs_delta5*, missing5*', 'signed and absolute midpoint change since t − 5 min; flag if unavailable'],
     ['delta15*, abs_delta15*, missing15*', 'same over 15 minutes'], ['delta30*, abs_delta30*, missing30*', 'same over 30 minutes']],
    [0.36, 0.64]),
  P('The activity logistic baseline uses midpoint, spread, log_valid_updates30, abs_delta5, missing5, abs_delta15, missing15, abs_delta30 and missing30. The activity and full-feature logistic baselines standardise inputs and use L2 regularisation with C = 0.1. stack_lin is an unstandardised logistic regression (C = 1.0) on logit(row_hgb7), logit(online rate) and log(1 + matured outcomes); seg_hgb and the v8 candidates are histogram gradient-boosting models with the fixed settings given in their committed scripts. All lag groups marked * contribute their delta, absolute delta and missing flag.'),
];
const appB = [AH('Appendix B – Protocol Deviations and Failed Attempts'),
  P('Every item below is preserved in the repository with its original outputs. None was rescued by changing a threshold after outcomes were seen.'),
  ...Tbl('Deviations, failures and superseded versions, in chronological order.',
    ['Item', 'What happened', 'Handling'],
    [['V3 activity gate', '204,069 zero-count Kalshi rows; 19 markets missed activity minimum', 'V3.1 removed exactly those 19, label-blind; V3 failure kept'],
     ['V3.1 holdout', 'Builder printed positive count (26,381) before consumption receipt', 'Disclosed; weights and formulas already frozen'],
     ['Exact-price forecasting', 'Ridge 30.9% worse than persistence on MAE in a live audit', 'Reported as negative; target changed'],
     ['V01 live runtime', 'Readiness 0/16: host clock faults', 'Frozen as failed; V02 built'],
     ['June 8–14 capture', 'DNS outage failed 74 hours on both attempts', 'Outcome-blind refetch to separate directory; disclosed'],
     ['V02 rehearsal 1, 2', 'Startup crash; WebSocket logged before clock was valid', 'Fixed with regression tests; archived'],
     ['V02 activation 1', 'Memory about 317 MB/h and full rescans; 0 forecasts', 'Superseded by bounded inputs (510/510 equivalent)'],
     ['V02 activation 2', 'Thread race forked hash chain; 0 forecasts', 'Single-writer journal; readiness re-run and passed'],
     ['V02 live, first grid', 'Pre-loaded inputs not refreshed; 30 abstentions', 'Fail-closed; not patched during the test'],
     ['V02 live, host stall', 'Concurrent job caused swapping; 4 grids missed', 'Heavy jobs deferred until close'],
     ['V02 live, sleep/reboot', 'Lid-closed battery sleep 04:42 UTC, reboot 05:16 UTC, 27 Oct; source and emitter lost', 'Not restarted into the same run; not evaluable; continued as V02b (same frozen files, new run directory)'],
     ['V02b live, sleep gap', 'Lid closed on AC 07:40–08:26 UTC, 27 Oct, before system-wide sleep disable', '9 grids (270 decisions) scored as missed; processes survived; no restart, no backfill'],
     ['V4 collector, same outage', 'Collector stopped by the reboot; checkpoint clean', 'Restarted from checkpoint with restart receipt; label-blind audit passed'],
     ['Report rounding', 'June 1–7 interval printed as [0.039, 0.081]; artifact value 0.0805 rounds to 0.080', 'Caught by the reproducibility check; corrected'],
     ['June 15–28 cohort v1', 'Only 15/60 contracts passed the end-date rule', 'Superseded before any price read by v2 (21 contracts)'],
     ['V4 close-out audit', 'Frozen audit required run status ok; only 40% of 186,753 news rows had it, unlike the training data', 'Chain stopped. Disclosed v2 audit (any recorded status) hash-locked before consumption; chain then run once on 31 Oct'],
     ['History-stack cohort', 'Frozen eligibility rules admitted 53 of a 150-contract target', 'Not loosened; smaller cohort reported'],
     ['History-stack capture', 'Frozen 32 MiB per-hour range limit exceeded in 134 of 336 hours (one timeout was retried and succeeded)', 'Not retried or recaptured; no forecasts issued in those hours; disclosed'],
     ['History-stack evaluation', 'Panel built in chunks of 15 contracts to bound memory', 'Fixed in the frozen runner before capture; contracts are independent tapes'],
     ['Segment confirmation selection', 'First selection attempt stopped when identifier and clock reads exceeded their frozen 64 MiB limit, before any economic column was read or any contract chosen', 'Attempt archived; a disclosed v2 runner with a 256 MiB limit selected the cohort'],
     ['Segment confirmation capture', 'Versioned fetcher with a 192 MiB per-hour range limit (32 MiB in the history-stack test), frozen before selection', 'Disclosed; all 216 hours captured'],
     ['Segment-aware stack window', 'Test period 22 July–8 August is the calendar period of the consumed V3.1 holdout; the archive ends on 10 August', 'User-authorized deviation, frozen before selection; V3.1, v1 and V4 markets excluded; no V3.1 data read'],
     ['Segment-aware stack capture', 'One hour (31 July 20:00) timed out on the first attempt', 'Retried once under the frozen rule; all 432 hours captured'],
     ['Baseline benchmark, TabICL', 'Its key–value cache ran at about 66 ms per row against 17 ms without it (timed on training rows)', 'Compute-only v2 amendment before any score: cache off; model, checkpoint and seed unchanged'],
     ['Baseline benchmark, Sundial and Time-MoE', 'Added at the user’s request after the protocol was frozen; model-hub code had first been refused by the sandbox', 'v3 amendment before any score: code read and hashed; scored on the nonoverlapping half-hour grid for inference cost; missing context values imputed'],
     ['Baseline benchmark, end-to-end tier', 'TabM needed about 800 s for 9,212 rows on this host’s CPU', 'v3 amendment: trained on a seeded 100,000-row subsample of the six blocks (seg_hgb used all rows; favours seg_hgb)'],
     ['Baseline benchmark, TabICL prediction', 'Predicting 20,000 rows at once failed on the GPU (an 8.02 GiB buffer error); no output was written', 'Compute-only v4 amendment before any score: prediction in 1,000-row chunks; failed log kept'],
     ['Development study v8', 'A further candidate (the online contract offset on seg_ref) was added at the user’s request after the first run had started', 'The run was stopped before any fold finished, its log kept, and the candidate committed before the rerun']],
    [0.22, 0.42, 0.36]),
];
const appC = [AH('Appendix C – Reproducibility'),
  P('**Consistency check.** verify_report_reproducibility_20261027 re-hashes the files locked by the cited release and data manifests (1,293 files in 94 manifests; two earlier locks pass only through their documented successor manifests) and fails if any is missing or changed. It checks the 105 headline claims listed in report/claims.json (each with its artifact, cohort, model and comparator) against their artifact values, and confirms that each claim’s printed value still appears in the report source. It re-renders the figures from frozen outputs and checks that the PNGs are byte-identical, and with --recompute reruns the post hoc analyses. Numbers not listed in the claims file are not checked. It reads only completed result files, opens no unused holdout and starts no evaluation, and it checks the listed numbers, not every statement or table label. Its first run, on 27 October, caught one rounding error in this report, now corrected. It was run again after close-out on 30 October and after the V4 and history-stack evaluations on 31 October and the segment and segment-aware stack evaluations on 1 November, and after the baseline benchmark and development study on 2 November, with and without --recompute, and passed each time.'),
  P('All code is in the EventX repository. Frozen releases live under eventx/release/, and results with their hash manifests under data/. The principal entry points are listed below (run from the repository root with the project virtual environment). Commands marked once-only consume their block and refuse to run again; they are listed for audit, not for re-running.'),
  ...Tbl('Principal scripts and outputs.', ['Purpose', 'Command or path'],
    [['June 1–7 test (consumed, once-only)', 'python -m eventx.tasks.run_v7_june_replication_20261026'], ['June 8–14 test (consumed, once-only)', 'python -m eventx.tasks.run_v7_new_identity_test_20261026 {select,capture,evaluate}'],
     ['V03 secondary (consumed, once-only)', 'python -m eventx.tasks.evaluate_v7_new_identity_v03_20261026'], ['June 15–28 test (once-only)', 'python -m eventx.tasks.run_v7_late_june_test_20261027_v2 {capture,evaluate}'],
     ['Category breakdown', 'python -m eventx.tasks.analyze_v7_category_breakdown_20261027'], ['Figures', 'python -m eventx.tasks.plot_v7_report_figures_20261027'],
     ['Live runtime health (V02b)', 'python -m eventx.tasks.status_v7_forecast_runtime_20261026_v02b'], ['Live evaluation (V02b, once-only)', 'python -m eventx.tasks.evaluate_v7_forecast_runtime_20261026_v02b'],
     ['Close-out sequence (once-only)', 'zsh scripts/close_out_20261030.sh'],
     ['V4 close-out (once-only, in order)', 'audit_v4_confirmatory_collection (stopped), then zsh scripts/run_v4_chain_v2_20261031.sh: audit v2, consume, prepare, build, evaluate'],
     ['History stack: development', 'python -m eventx.tasks.develop_v7_history_stack_20261031'],
     ['History stack: test (once-only)', 'python -m eventx.tasks.run_v7_history_stack_test_20261031 {select,capture,evaluate}'],
     ['Segment discovery and replication (post hoc)', 'python -m eventx.tasks.analyze_v7_segment_replication_20261101 [features]'],
     ['Segment confirmation test (once-only)', 'python -m eventx.tasks.run_v7_segment_confirm_test_20261101_v2 {select,capture,evaluate}'],
     ['Market-state breakdown (descriptive)', 'python -m eventx.tasks.analyze_v7_segment_state_table_20261101'],
     ['Segment-aware stack: development', 'python -m eventx.tasks.develop_v7_segment_stack_20261101'],
     ['Segment-aware stack: test (once-only)', 'python -m eventx.tasks.run_v7_segment_stack_test_20261101 {select,capture,evaluate}'],
     ['State-of-the-art baselines: feature rebuild (read-only)', 'python -m eventx.tasks.rebuild_v7_sota_features_20261101 {jul_13_21,jul22_aug8}'],
     ['State-of-the-art baselines (post hoc, scored once)', 'python -m eventx.tasks.benchmark_v7_sota_baselines_20261101_v2 {tier_a,tier_b_inputs}; .venv-ts: benchmark_v7_sota_baselines_20261101 tier_b_forecast and _v3 tier_b2; _v3 {tier_c,evaluate}'],
     ['State-of-the-art baselines: label-free preflight', 'python -m eventx.tasks.preflight_v7_sota_baselines_20261102 (must pass before the single evaluate)'],
     ['Development study v8 (Section 6.11)', 'python -m eventx.tasks.develop_v8_hawkes_posterior_20261102'],
     ['Frozen Track B releases', 'eventx/release/v7/{history_stack_20261031, segment_confirm_20261101, segment_stack_20261101, sota_baselines_20261101}/'],
     ['V4 audit revision (disclosed)', 'eventx/release/v4/AUDIT_REVISION_V2_20261031.md'],
     ['Runtime tests', 'python -m eventx.tasks.check_v7_forecast_runtime_20261026_v02 (32 tests; V02 code, reused unchanged by V02b)'],
     ['News bound (Section 4.3)', 'python -m eventx.tasks.analyze_v3_1_news_mde_20261027'],
     ['Booster drivers (Section 6.4)', 'python -m eventx.tasks.analyze_v7_booster_drivers_20261027'],
     ['One-command check', 'python -m eventx.tasks.verify_report_reproducibility_20261027 [--recompute]'],
     ['Claim-to-evidence map', 'report/claims.json'],
     ['Result formatter (read-only)', 'python report/fill_pending_20261030.py'],
     ['Post close-out checks and hash manifest', 'zsh scripts/post_close_out_20261030.sh']],
    [0.28, 0.72]),
];

// ---------------------------------- lists of figures/tables (filled after content built) ----
const listPage = (title, items) => [
  new Paragraph({ pageBreakBefore: true, alignment: AlignmentType.CENTER, children: [new TextRun({ text: title, font: FONT, size: 32, bold: true, color: '000000' })], spacing: { after: 240 } }),
  ...items.map(t => new Paragraph({ children: runs(t), spacing: { line: LINE15, after: 60 } })),
];

const doc = new Document({
  creator: STUDENT, title: TITLE,
  features: { updateFields: true },
  styles: { default: { document: { run: { font: FONT, size: BODY } } } },
  numbering: { config: [
    { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 283 } } } },
                                      { level: 1, format: LevelFormat.BULLET, text: '–', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1134, hanging: 283 } } } }] },
    { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 340 } } } }] },
  ] },
  sections: [
    { properties: { page: { margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } }, children: [...cover, ...titlePage] },
    { properties: { page: { margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN }, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } } },
      footers: footer(), children: [...abstract, ...ack, ...tocPage(), ...listPage('List of Figures', figures), ...listPage('List of Tables', tables)] },
    { properties: { page: { margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN }, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } },
      footers: footer(), children: [...main, ...references] },
    ...[['A-', appA], ['B-', appB], ['C-', appC]].map(([prefix, kids]) => ({
      properties: { page: { margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN }, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } } },
      footers: footer(prefix), children: kids })),
  ],
});

Packer.toBuffer(doc).then(buf => {
  const out = path.join(__dirname, 'EventX_UROP_Report.docx');
  fs.writeFileSync(out, buf);
  fs.writeFileSync(path.join(__dirname, 'headings.json'), JSON.stringify(['Abstract', 'Acknowledgement', 'List of Figures', 'List of Tables', ...headings.map(h => h[1])]));
  console.log('wrote', out, 'figures', figN, 'tables', tabN);
});
