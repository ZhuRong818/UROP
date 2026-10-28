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
const SMALL = 20;       // 10pt for appendices / tables
const LINE15 = 360;     // 1.5 line spacing
const PAGE_W = 11906, MARGIN = 1440, TEXT_W = PAGE_W - 2 * MARGIN;  // A4, 1" margins

// ---------- inline markup: **bold**, *italic*, [[PENDING ...]] highlighted ----------
function runs(text, size = BODY) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|\[\[[^\]]+\]\])/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, size }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, size }));
    else if (t.startsWith('[[')) out.push(new TextRun({ text: t.slice(2, -2), highlight: 'yellow', bold: true, font: FONT, size }));
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
  const cell = (t, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, margins: { top: 40, bottom: 40, left: 80, right: 80 },
    borders: { top: border, bottom: border, left: border, right: border },
    shading: head ? { type: ShadingType.CLEAR, fill: 'E8E8E8', color: 'auto' } : undefined,
    children: [new Paragraph({ alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER, children: head ? [new TextRun({ text: t, bold: true, font: FONT, size: SMALL })] : runs(String(t), SMALL) })],
  });
  return [Caption('Table', caption), new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map(r => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) }))] }),
  new Paragraph({ spacing: { after: 120 }, children: [] })];
}

const footer = (prefix) => ({ default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: prefix ? [prefix, PageNumber.CURRENT] : [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) });

// ======================================================================================
// CONTENT
// ======================================================================================
const TITLE = 'Leakage-Safe Forecasting of Prediction-Market Repricing: News Signals and a Replicated Quote-Change Forecaster';
const STUDENT = 'Zhu Rong';
const ADVISOR = 'Lu Yao';
const YEAR = '2026/2027';

const cover = [
  new Paragraph({ spacing: { before: 2400 }, children: [] }),
  Center('UNDERGRADUATE RESEARCH OPPORTUNITY PROGRAMME', 28, true, 80),
  Center('(UROP) PROJECT REPORT', 28, true, 1200),
  Center(TITLE, 36, true, 1200),
  Center('By', 24, false, 120),
  Center(STUDENT, 28, true, 1600),
  Center('[Department of Computer Science]', 24, false, 80),
  Center('School of Computing', 24, false, 80),
  Center('National University of Singapore', 24, false, 600),
  Center(YEAR, 24, false, 0),
];

const titlePage = [
  new Paragraph({ pageBreakBefore: true, spacing: { before: 1200 }, children: [] }),
  Center('UNDERGRADUATE RESEARCH OPPORTUNITY PROGRAMME', 26, true, 80),
  Center('(UROP) PROJECT REPORT', 26, true, 800),
  Center(TITLE, 30, true, 800),
  Center('By', 24, false, 120),
  Center(STUDENT, 26, true, 800),
  Center('[Department of Computer Science]', 24, false, 80),
  Center('School of Computing', 24, false, 80),
  Center('National University of Singapore', 24, false, 80),
  Center(YEAR, 24, false, 900),
  new Paragraph({ children: runs('Project No: [[project number]]'), spacing: { after: 80 } }),
  new Paragraph({ children: runs(`Advisor: ${ADVISOR}`), spacing: { after: 240 } }),
  new Paragraph({ children: runs('**Deliverables:**'), spacing: { after: 80 } }),
  new Paragraph({ children: runs('Report: 1 Volume'), spacing: { after: 40 } }),
  new Paragraph({ children: runs('Program: EventX source repository (Python), frozen release manifests and evaluation scripts'), spacing: { after: 40 } }),
  new Paragraph({ children: runs('Data: hash-locked evaluation outputs and receipts (data/ directory)'), spacing: { after: 40 } }),
];

const abstract = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Abstract', font: FONT, size: 32, bold: true, color: '000000' })], spacing: { after: 240 } }),
  P('EventX asks whether information available at a decision time predicts short-horizon repricing in prediction markets, under strict point-in-time and evaluate-once rules. In a frozen historical study of 4,651 Kalshi and Polymarket markets, adding counts of conservatively available news articles to a market-history model lowered average precision and worsened the Brier score on 1.46 million out-of-fold rows, failing all five prespecified promotion gates. We then defined a narrower target: the probability that a contract’s quoted midpoint 30 minutes later differs from its current value. A gradient-boosted classifier on 18 point-in-time quote features, frozen before testing, reduced log loss against a logistic baseline by 16.8% on an unopened week and by 14.9% on 35 never-used contracts. Contract-clustered bootstrap intervals for both gains lay above zero, and in a descriptive breakdown the booster had lower log loss in every market category. A post hoc online reference that tracks each contract’s own matured outcomes came close to the booster on the new contracts (log loss 0.4231 against 0.4208), so the advantage is over the specified fixed baselines rather than over every simple reference. We also built a live forecasting runtime with validated network-time correction and tamper-evident journals, and started a three-day prospective test on 30 new contracts, scheduled to close on 29 October. [[PENDING: one-sentence live result.]] In these data, short-horizon quote activity was predictable from market state, while simple news counts failed the prespecified promotion gates.'),
  new Paragraph({ spacing: { before: 240, after: 80 }, children: runs('**Subject Descriptors:**') }),
  ...['G.3 Probability and Statistics', 'I.2.6 Learning', 'H.2.8 Database Applications (Data mining)', 'J.4 Social and Behavioral Sciences (Economics)']
    .map(t => new Paragraph({ children: runs(t), spacing: { after: 20 }, indent: { left: 720 } })),
  new Paragraph({ spacing: { before: 200, after: 80 }, children: runs('**Keywords:**') }),
  new Paragraph({ indent: { left: 720 }, children: runs('Prediction markets, probabilistic forecasting, market microstructure, gradient boosting, leakage-safe evaluation') }),
  new Paragraph({ spacing: { before: 200, after: 80 }, children: runs('**Implementation Software and Hardware:**') }),
  new Paragraph({ indent: { left: 720 }, children: runs('Python 3.12, scikit-learn, PyArrow, NumPy, httpx; Polymarket CLOB WebSocket and Gamma API; pmxt hourly order-book archive; Lumid FinData; Apple macOS laptop (17 GB RAM)') }),
];

const ack = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Acknowledgement', font: FONT, size: 32, bold: true, color: '000000' })], spacing: { after: 240 } }),
  new Paragraph({ spacing: { line: 480 }, alignment: AlignmentType.JUSTIFIED, children: runs(`I thank my advisor, ${ADVISOR}, for guidance on research design and for insisting on honest, preregistered evaluation. I also thank the providers of the data used in this project: Lumid FinData for historical trades and news, the pmxt project for the public Polymarket order-book archive, and Polymarket for its public market-data interfaces. [[Add further acknowledgements if any.]]`) }),
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
add(P('Prediction markets let traders buy contracts that pay one dollar if an event happens, so a contract’s price can be read as a crowd probability of that event (Wolfers and Zitzewitz, 2004; Arrow et al, 2008). Platforms such as Polymarket and Kalshi now list thousands of contracts on elections, sports, macroeconomic releases, technology and geopolitics. Prices move when new information arrives, but they also move for mechanical reasons: liquidity providers re-quote, the order book thins out overnight, and contracts become quiet as their resolution approaches.'));
add(P('The original goal of EventX was a benchmark for whether outside information (news articles, and later posts by influential social-media accounts) carries **incremental, point-in-time** predictive information about these price moves, beyond what market history already reveals. Results in this area are easy to overstate. A single look-ahead leak, a reused test period or a weak baseline can produce an apparent gain without any error showing up. The project therefore treats evaluation discipline as a first-class research output. The intended protocol is that every test set is frozen before it is opened, every model is frozen before it is scored, and each held-out period is evaluated exactly once; the exceptions that occurred are disclosed in Appendix B.'));
add(H2('1.2 Research questions'));
NewList();
add(N('**RQ1 (news increment).** Does news that was demonstrably available at decision time improve a forecast of the next 30-minute price jump beyond a market-history baseline?'));
add(N('**RQ2 (forecastable target).** Is there a short-horizon market quantity that can be forecast reliably better than strong baselines, and does that advantage survive new time periods and never-seen contracts?'));
add(N('**RQ3 (live operation).** Can such a forecaster run prospectively on live data, under the same frozen rules, with every decision auditable after the fact?'));
add(H2('1.3 Summary of contributions'));
add(B('A frozen, preregistered historical test of news value over 4,651 markets, with a negative answer to RQ1. Under the frozen design, news counts made forecasts slightly worse and failed every promotion gate. A post hoc market-clustered bootstrap places the upper bound of the effect below every positive effect size registered before labels were seen (Chapter 4).'));
add(B('A quote-change forecaster whose advantage over logistic, rate-based and earlier boosted baselines replicates on two unopened June weeks, including 35 contracts never used before. A post hoc online contract rate scores close to it on the new contracts, which is consistent with, but does not establish, persistent contract-level activity explaining much of the advantage. In a descriptive breakdown its log loss is lower in every market category (Chapters 5 and 6).'));
add(B('A prospective runtime that validates its own clock against network time servers, writes hash-chained journals, and refuses to evaluate more than once. A three-day live test on 30 newly selected contracts was scheduled to close on 29 October (Chapter 7).'));
add(B('A full record of failed attempts and protocol deviations, kept rather than hidden (Appendix B).'));
add(H2('1.4 Organisation of the report'));
add(P('Chapter 2 reviews related work. Chapter 3 describes the data and the leakage safeguards shared by all studies. Chapter 4 reports the news-increment study (Track A). Chapters 5 and 6 present the quote-change forecaster and its historical evaluations (Track B), and Chapter 7 the prospective live test. Chapter 8 discusses validity, and Chapter 9 concludes with limitations and recommendations. Appendices give feature definitions, the deviation log and reproduction instructions.'));

add(H1('2 Background and Related Work'));
add(H2('2.1 Prediction markets as forecasts'));
add(P('Prediction-market prices aggregate dispersed beliefs and often forecast at least as well as polls or experts (Wolfers and Zitzewitz, 2004; Arrow et al, 2008). Calibration is good on average but imperfect, especially for long-shot outcomes and far-off events (Page and Clemen, 2013). This project does not try to beat the market’s forecast of the final outcome. It forecasts the behaviour of the market’s *own price* over the next half hour.'));
add(H2('2.2 News, attention and asset prices'));
add(P('Media content has measurable, short-lived associations with stock returns and trading volume (Tetlock, 2007), so news is a natural candidate signal for prediction markets as well. The difficulty is timing. A news record is only useful if it was available to a trader *before* the price moved, so timestamps must reflect availability (publication, ingestion and feed-delivery times) rather than event time. EventX therefore uses the most conservative available timestamp, and treats missing feed intervals as unknown rather than as zero news.'));
add(P('Prediction-market and betting prices are known to respond to news quickly. Snowberg, Wolfers and Zitzewitz (2007) use intraday moves in election-night prediction-market prices to measure how expected election outcomes moved financial markets. Croxson and Reade (2014) find that soccer betting prices incorporate goals scored just before half-time quickly and fully. Diercks, Katz and Wright (2026) study Kalshi macroeconomic markets as a high-frequency benchmark of expectations and examine how they respond to macroeconomic and financial news. These studies concern prices reacting to identified events. Track A asks a different, harder question: whether routinely available news counts, measured before the decision time, improve a forecast beyond what market history already contains.'));
add(H2('2.3 Market microstructure'));
add(P('Short-horizon price behaviour is driven largely by microstructure: the bid–ask spread, quote updates by liquidity providers, and the arrival of orders (O’Hara, 1995; Hasbrouck, 2007). The midpoint of the best bid and ask is the standard high-frequency price proxy. Whether a midpoint changes over a short window depends heavily on how active the book has recently been. Activity is persistent, which makes a quote-change target forecastable in principle. Engle and Russell (1998) model the clustering of durations between transactions. A duration model predicts whether at least one update arrives within a window, which is related to but not the same as the target here: a midpoint can move and return, so an update does not guarantee that the endpoint differs.'));
add(P('Machine-learning work on limit order books mostly forecasts the *direction* of the next mid-price move in liquid equity markets. Ntakaris et al (2018) provide a benchmark dataset with a day-based anchored cross-validation protocol; Zhang, Zohren and Roberts (2019) apply convolutional and recurrent networks to order-book data; and Sirignano and Cont (2019) report that a model pooled across stocks predicts the direction of price moves out of sample, including for stocks outside its training sample. EventX differs in target, market and protocol. It forecasts whether a prediction-market midpoint differs after a fixed 30-minute horizon, a coarser activity target, in thin markets whose contracts expire; and it tests a model frozen before the data were retrieved, once, on contracts never used before. Its closest analogue to the cross-stock result of Sirignano and Cont is the 8–14 June test on new contracts, so transfer to unseen instruments is not itself new. Kolm, Turiel and Westray (2023) find, across 115 stocks and several horizons, that the choice of input representation (order-flow imbalance rather than raw book levels) matters more than network depth. This suggests that input representation and horizon, rather than model size, are the natural next variables for EventX.'));
add(H2('2.4 Forecast evaluation and leakage'));
add(P('Probabilistic forecasts are evaluated with strictly proper scoring rules, which reward honest probabilities: here, log loss and the Brier score (Brier, 1950; Gneiting and Raftery, 2007). Boosted trees can produce systematically distorted probability estimates (Niculescu-Mizil and Caruana, 2005), so calibration is checked separately. Leakage, meaning information from the future or from the test set entering model building, is a common cause of false results in data mining (Kaufman et al, 2012), and a survey of machine-learning-based science found it in published work across 17 fields (Kapoor and Narayanan, 2023). In financial time series it also arises from overlapping label windows, which requires purged, embargoed cross-validation (López de Prado, 2018). Observations within one market are dependent, so uncertainty is estimated by resampling whole blocks or whole contracts rather than individual rows (Künsch, 1989; Cameron, Gelbach and Miller, 2008).'));
add(H2('2.5 Learning method'));
add(P('The forecasters use histogram-based gradient boosting (Friedman, 2001; Ke et al, 2017), as implemented in scikit-learn (Pedregosa et al, 2011). EventX makes no claim of algorithmic novelty. Its contribution is the target definition, the point-in-time feature construction, and the evaluation protocol around a standard learner. Tree ensembles remain highly competitive on medium-sized tabular data when the comparison accounts for tuning (Grinsztajn, Oyallon and Varoquaux, 2022), so boosting is a reasonable default. The same benchmark shows why a fair comparison needs matched inputs and tuning budgets, which the primary comparison here does not provide (Section 5.4).'));

add(H1('3 Data and Leakage Safeguards'));
add(H2('3.1 Data sources'));
add(B('**Lumid FinData** supplies historical executed trades for Kalshi and Polymarket, and a news feed with publication and ingestion timestamps. All ingestion runs as resumable, checkpointed batch jobs under the provider’s rate limit, and analysis uses frozen, content-hashed extracts rather than live API calls.'));
add(B('**The pmxt Polymarket archive** publishes one Parquet file of order-book events per hour (book snapshots, price changes, trades), each with venue and receive timestamps. Files are sorted by market identifier, so the project can download only the row groups that contain the selected contracts.'));
add(B('**Polymarket’s Gamma metadata API and CLOB WebSocket** supply contract metadata (question, outcomes, token identifiers, start and end dates), and live book updates for the prospective test (Polymarket, 2026).'));
add(H2('3.2 Safeguards common to all studies'));
add(P('The following rules govern the studies in this report and are enforced in code rather than by convention. The quote freshness and validity rule applies to Track B only.'));
add(B('**Point in time.** Every feature for a decision at time *t* uses only records received at or before *t*. In Track B, a forecast is issued only when the latest quote is fresh (at most 120 seconds old on both the venue and the receive clocks), valid (bid below ask, spread at most 0.05) and unambiguous.'));
add(B('**Frozen, hash-locked releases.** Protocols, cohorts, model files and evaluation code are frozen as SHA-256 manifests *before* the data they will be judged on is retrieved. A changed file means a new version, never an edit in place.'));
add(B('**Evaluate once.** Each test window is consumed by a single evaluation run, which writes a consumption receipt first and refuses to run again. Results are reported whether favourable or not.'));
add(B('**Protected identifiers and windows.** 1,231 market identifiers and three time windows used by earlier confirmatory studies are filtered out at decode time, so no Track B experiment can read them.'));
add(B('**Outcome-blind cohort selection.** New contract cohorts are chosen from identity, event-type and clock columns plus metadata only, before any price or quote column of the test period is read.'));
add(B('**Missing outcomes stay missing.** If the 30-minute endpoint quote is unavailable, the forecast is scored as unknown. Deterministic worst-case bounds over all issued forecasts are reported alongside the scored results.'));

add(H2('3.3 Study overview'));
add(P('The project ran a sequence of versioned studies. Table 1 lists each one with its data, model, comparator and status, so that the version names used in later chapters can be looked up in one place. Training periods are those of the frozen model being scored; evaluation periods are the data that model had not been fitted on.'));
add(Tbl('Overview of the studies reported here. Known / missing counts are matched forecasts with an observed endpoint and issued forecasts without one.',
  ['Study', 'Training data', 'Evaluation data', 'Model vs comparator', 'Contracts; known / missing', 'Pass rule', 'Status'],
  [['V3.1 development (Track A)', 'Purged expanding folds', '17 May–22 Jul 2026, out-of-fold', 'B1 (news counts) vs B0 (market history)', '2,290 of 4,651 markets contribute; 1,460,454 rows', 'All five gates (Section 4.1)', 'Complete: 0 of 5 gates; B1 not promoted'],
   ['V3.1 holdout', '17 May–22 Jul', '22 Jul–8 Aug', 'B0 only (absolute benchmark)', '300 markets; 211,718 rows', 'None', 'Consumed once; deviation disclosed'],
   ['V4 confirmatory', '17 May–22 Jul (discovery)', '6 Sep–30 Oct, collected prospectively', 'B3 (richer news) vs B0', '470 contracts', 'LL gain ≥ 0.001 nats; bootstrap lower bound > 0; Brier and venue guards', 'Pending'],
   ['May 13–19 replication (Track B)', '7–9 May, 50 development contracts', '13–19 May', 'row_hgb7 vs activity logistic', '30; 27,924 / 4,553', 'None (fixed-model replication)', 'Complete'],
   ['June 1–7', '7–9 May', '1–7 June, unopened', 'row_hgb7 vs activity logistic', '18 (development); 16,453 / 2,851', 'Lower LL than activity logistic and global rate; Brier no higher', 'Complete: passed'],
   ['June 8–14', '7–9 May', '8–14 June, unopened, new contracts', 'row_hgb7 vs activity logistic', '35; 35,218 / 4,438', 'As June 1–7, plus contract-clustered lower bound > 0', 'Complete: passed; DNS refetch deviation'],
   ['June 8–14, V03 secondary', '7–9 May (14 features)', '8–14 June', 'V03 hgb7 vs its full logistic', '35; 35,749 / 4,268', 'Registered secondary analysis', 'Complete'],
   ['June 15–28', '7–9 May', '15–28 June, unopened, new contracts', 'row_hgb7 vs activity logistic; V03 secondary', '21 selected', 'As June 8–14, for both models', 'Pending'],
   ['Live V02b', '7–9 May (V03)', '27 Oct 06:35–29 Oct 23:25 UTC, prospective', 'V03 hgb7 vs full logistic and global rate', '30; 22,650 scheduled decisions', 'None; reporting floor of 100 known outcomes and 20 of each class', 'Pending']],
  [0.13, 0.12, 0.15, 0.16, 0.16, 0.16, 0.12]));
add(H2('3.4 Scores, uncertainty and missing outcomes'));
add(P('All forecasts are probabilities *p* of a binary outcome *y*. They are scored with two strictly proper scoring rules, for which lower is better:'));
add(B('**log loss**, the mean of −[*y* ln *p* + (1 − *y*) ln(1 − *p*)] over forecasts, in nats;'));
add(B('**Brier score**, the mean of (*p* − *y*)².'));
add(P('Average precision (AP) and the area under the ROC curve (AUC) are reported as ranking summaries. A **gain** is always the comparator’s score minus the candidate’s score, so a positive gain favours the candidate; for AP, which is higher-is-better, the change is candidate minus comparator. A **relative reduction** is the log-loss gain divided by the comparator’s log loss: a 16.8% reduction means the booster’s log loss is 16.8% below the comparator’s. Comparisons are **matched**: every model is scored on exactly the same forecasts.'));
add(P('**Uncertainty.** Forecasts from the same contract are dependent, so intervals come from a **cluster bootstrap**. Whole contracts (or, in Track A, whole markets) are resampled with replacement, the row-weighted mean gain is recomputed for each resample, and the 2.5th and 97.5th percentiles of 5,000 resamples (2,000 in Section 4.3) form the 95% interval. A date-clustered version resamples whole days instead. The one-sided 95% upper bound used in Section 4.3 is the 95th percentile.'));
add(P('**Missing outcomes.** A forecast is issued from the quote at time *t*, but its outcome is known only if a valid endpoint quote exists at *t* + 30 minutes. Forecasts without one are scored as unknown, never imputed. The **missing-outcome bounds** are deterministic, not confidence intervals: each unknown outcome is set to whichever value is worst (lower bound) or best (upper bound) for the candidate relative to the comparator, and the mean gain is recomputed over all issued forecasts. A lower bound above zero means that no assignment of the unknown outcomes could reverse the sign of the gain.'));

add(H1('4 Track A: Incremental Value of News'));
add(H2('4.1 Design of the historical primary study (V3.1)'));
add(P('The cohort contains 4,651 markets (3,832 Kalshi and 819 Polymarket) with a unique canonical YES outcome, at least 100 positive-notional executions and at least ten active days. Development covers 17 May to 22 July 2026, and a separate holdout covers 22 July to 8 August 2026. At each five-minute decision time the price is the latest executed YES trade. The binary target asks whether the absolute log-odds change over the next 30 minutes exceeds four times the trailing one-minute volatility.'));
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
add(P('A failed gate shows only that no gain was found. To say how large a gain the data still allow, the 2,290 markets that contribute out-of-fold rows (of the 4,651 in the cohort) were resampled as clusters, 2,000 times, over the frozen five-fold out-of-fold predictions. This is a post hoc, descriptive analysis of already-opened development data: the consumed holdout is not read, nothing is refit, and the point estimates reproduce the stored ones exactly.'));
add(Tbl('Market-clustered bootstrap of the news increment on 1,460,454 development out-of-fold rows from 2,290 markets. Improvements are B0 minus B1 for Brier and log loss; the AP change is B1 minus B0. Positive values would favour news.',
  ['Quantity', 'Point', '95% interval', 'One-sided 95% upper bound'],
  [['Brier improvement', '−0.000284', '[−0.000395, −0.000179]', '−0.000196'],
   ['Average-precision change', '−0.00192', '[−0.00333, −0.00052]', '−0.00075'],
   ['Log-loss improvement (nats)', '−0.00098', '[−0.00137, −0.00059]', '−0.00066']],
  [0.34, 0.16, 0.28, 0.22]));
add(P('The one-sided 95% upper bound of the Brier improvement is below zero, conditional on this cohort and resampling design. Markets that share events or dates may be dependent, so the interval may be somewhat too narrow. For scale, B0’s Brier skill over climatology is 0.00210 (base rate 14.1%), and the upper bound corresponds to about 9% of that skill; this is a scale comparison, not a confidence interval for the ratio. Before any label was read, a frozen design-sensitivity simulation estimated how often a true effect would pass all five gates: 7% for a “very small” effect (Brier +0.0001, AP +0.0005), 33% for “small”, 86% for “moderate” (Brier +0.0005, AP +0.0025) and 99.8% for “clear”. Every registered scenario, down to “very small”, lies above the observed upper bounds (Figure 1). The null is therefore informative about the effect sizes the study was designed to detect, although it does not show that news has no value in general. The bound applies to lexically associated article counts over 60–1,440 minutes. Richer representations are the subject of V4.'));
add(Figure('docs/figures/fig4_news_bound.png', 6.0, 'Observed news effect on Brier score with its 95% market-clustered interval, against the effect sizes registered before labels were read and their simulated probabilities of passing all five gates.'));
add(H2('4.4 Richer news features (V4) and diagnostics (V5, V6)'));
add(P('V4 freezes a nested ladder of richer news features: news volume (B1); relevance and seven-day novelty (B2); and publisher diversity with cross-publisher headline diffusion (B3). It tests them prospectively on 470 Polymarket contracts from 6 September to 30 October 2026. Success requires at least 0.001 nats of log-loss improvement for B3 over B0, with a positive bootstrap lower bound and Brier and venue guards. The sealed collection passed a label-blind health check on 27 October: 58 of 58 news days and 51 of 51 trade days had receipts, nothing was pending, and all 15 frozen hashes matched. The result is evaluated once after the collection closes on 30 October (Table 4).'));
add(Tbl('V4 confirmatory result, primary population (price age at most 30 minutes). Improvements are B0 minus B3, so positive favours B3.',
  ['Quantity', 'Value', 'Frozen condition', 'Met?'],
  [['B3 − B0 log-loss improvement (nats per row)', '[[PENDING]]', 'at least 0.001', '[[PENDING]]'],
   ['95% bootstrap interval of the improvement', '[[PENDING]]', 'lower bound above zero', '[[PENDING]]'],
   ['B3 − B0 Brier improvement', '[[PENDING]]', 'at least −0.0005', '[[PENDING]]'],
   ['Venue-level estimates', '[[PENDING]]', 'non-negative where at least 30 clusters', '[[PENDING]]'],
   ['Positive claim supported', '[[PENDING]]', 'all four conditions', '—']],
  [0.40, 0.20, 0.28, 0.12]));
add(P('Exploratory work on already-opened data (V5) traced the apparent benefit of a residual-news model to controls. A context-only gate improved more than the full news correction did, and a nonlinear market-only model beat the full news model by 0.0085 nats. The log-loss improvement from adding the news mechanism itself was −0.000871 nats, with interval [−0.001457, −0.000208]; that is, it made log loss slightly worse. A contract-aware news-linking effort (V6) failed its strict link audit, and certified predictive support was 0 of 8,844 contract-days. Taken together, the answer to RQ1 so far is **no**: under strict availability rules, simple news representations did not add value beyond market history.'));

add(H1('5 Track B: Quote-Change Forecasting Method'));
add(H2('5.1 Why the target changed'));
add(P('Before settling on the current target, the project tried to forecast the *exact* midpoint 30 minutes ahead, both historically and in a live audited run on 25 October. Because most midpoints do not change over 30 minutes, the persistence forecast ("no change") is very hard to beat on mean absolute error. In the live run a ridge model was 30.9% worse than persistence on 257 observed outcomes. This does not show that point forecasting is inherently unpromising, only that these point models did not beat persistence. The project therefore switched to a binary target, **whether** the midpoint 30 minutes later will differ from the current one, which is forecast as a probability and scored with proper scoring rules.'));
add(H2('5.2 Target and eligibility'));
add(P('At each five-minute grid time *t*, the target is 1 if the recorded YES midpoint at *t* + 30 minutes differs from the midpoint at *t* by more than 10⁻¹², and 0 otherwise. The tolerance removes floating-point noise only; it is not an economic threshold. A forecast is issued only when the current quote passes the freshness and validity rules of Section 3.2. A target is assigned only when the endpoint quote passes the same rules. The target measures quote activity. It carries no information about direction, size, final resolution or profit.'));
add(P('**Why forecast quote activity.** The target is a measure of near-term market activity, not of direction. It is studied here for three reasons, which are motivations rather than demonstrated benefits. First, it resolves every 30 minutes, so a frozen model can be tested on tens of thousands of outcomes within days; this makes it a practical testbed for leakage-safe, evaluate-once protocols. Second, a calibrated activity forecast could plausibly help schedule monitoring, quote refreshes or data collection, and it provides a strong market-only baseline against which news or social signals can be judged. Third, much short-horizon price movement is mechanical, and a study of external information has to control for that predictable component first.'));
add(P('**What the target misses.** A one-tick move and a large repricing both count as 1, and a move that reverses before the endpoint counts as 0. The target says nothing about the direction of the next move, the resolution of the underlying event, or profit after spreads and fees. Directional forecasting would need a different target and different baselines, and any economic value would need evidence this project does not provide.'));
add(H2('5.3 Features'));
add(P('The primary model (**row_hgb7**) uses 18 features computed from quotes received by decision time (Appendix A):'));
add(B('the midpoint and its log-odds, and the spread;'));
add(B('the source and receive ages of the quote;'));
add(B('the hour of day, encoded as sine and cosine;'));
add(B('the number and fraction of valid quote states in the last 30 minutes;'));
add(B('signed and absolute midpoint changes over 5, 15 and 30 minutes, each with an explicit missing flag.'));
add(P('The live-runtime model (**V03 hgb7**) uses a 14-feature subset that drops the age and activity-count features. Those four depend on archive receive clocks that a live system cannot reproduce exactly. No news, order-depth or contract-identity features are used, so the models are contract-agnostic.'));
add(H2('5.4 Models and baselines'));
add(P('The forecaster is a histogram gradient-boosting classifier (100 iterations, learning rate 0.05, at most 7 leaves, minimum leaf size 100, L2 penalty 10, no early stopping and no class reweighting). Every comparison is against fixed baselines. The rate and logistic baselines were fitted on the same training rows as row_hgb7; the legacy booster was loaded unchanged from an earlier frozen bundle:'));
add(B('a smoothed global event rate;'));
add(B('a per-contract rate shrunk toward the global rate with 20 pseudo-observations;'));
add(B('an **activity logistic regression** on nine features (midpoint, spread, log valid-update count, and absolute 5-, 15- and 30-minute changes with their missing flags), the primary comparator;'));
add(B('the earlier frozen booster (**legacy HGB**), loaded from its own earlier bundle rather than refit;'));
add(B('for the V03 live model only, its own full-feature logistic regression on the V03 features.'));
add(P('row_hgb7 was selected and refit on 7–9 May 2026 data from 50 development contracts before any later block was retrieved. Nothing has been refit, recalibrated or re-thresholded since.'));
add(P('The primary comparison is between two complete forecasting systems: row_hgb7 uses 18 inputs and activity logistic regression uses nine of them. It therefore shows that the booster forecasts better than the specified reference, but not why. The gain could come from nonlinearity, from the nine extra inputs, or from both. The V03 comparison against a logistic regression on the same 14 inputs is better controlled, but it is a separate model with its own result and does not repair the primary comparison retroactively.'));
add(H2('5.5 Evaluation protocol'));
add(P('Each evaluation block follows the same sequence. First the protocol is frozen, including the primary comparison and the pass rule. Then the cohort is selected outcome-blind, the hourly archive files are captured (with one permitted retry for transport failures), and finally the block is evaluated exactly once. The primary metric is matched, row-weighted log loss of row_hgb7 against activity logistic regression. Each block’s pass rule was frozen with its protocol, and the two June rules differ:'));
add(B('**1–7 June:** on the development cohort, the booster’s log loss is below both activity logistic regression and the global rate, and its Brier score is no higher than logistic regression’s. A contract-clustered bootstrap interval was added before evaluation as an analysis-only secondary result, not a pass condition;'));
add(B('**8–14 June:** the same conditions, and in addition the 95% contract-clustered bootstrap interval for the log-loss gain over activity logistic regression must have a lower bound above zero (5,000 resamples of whole contracts).'));
add(P('In both blocks, date-clustered intervals, per-date and per-contract win counts, a nonoverlapping 30-minute subset, a strict continuous-path subset, and worst-case missing-outcome bounds are secondary results. A log-loss or Brier **gain** is always the baseline’s score minus the booster’s, so positive values favour the booster.'));

add(H1('6 Track B: Historical Results'));
add(H2('6.1 Development and early replications'));
add(P('An earlier frozen booster cut log loss by 18.1% against activity logistic regression on a new time block, 28–30 April (3,729 rows, 11 markets). The broader-trained row_hgb7 reduced log loss by 22.7% on 10–12 May for the development cohort and by 9.6% for ten reserved contracts. On the seven-day replication of 13–19 May, row_hgb7 achieved 0.3583 against logistic regression’s 0.4524 (20.8%). For six training-excluded contracts the gain was only 3.5%, and their worst-case missing-outcome bounds crossed zero. That gap motivated the dedicated test on new contracts in Section 6.3.'));
add(H2('6.2 Unopened week, same cohort: 1–7 June'));
add(P('No earlier study had read any June quote data. All 168 hourly files were captured, with 0 protected rows read. Only 20 of the 60 fixed contracts were still quoting, because the rest had expired or gone inactive. These were kept unchanged rather than replaced.'));
add(Tbl('Matched results, 1–7 June, development cohort (18 contributing contracts, 16,453 known outcomes, 2,068 positives). Lower log loss and Brier are better.',
  ['Model', 'Log loss', 'Brier', 'AUC', 'Booster log-loss reduction'],
  [['**row_hgb7**', '**0.2931**', '**0.0848**', '0.835', '—'], ['Activity logistic', '0.3523', '0.1003', '—', '16.8%'],
   ['Legacy HGB', '0.3285', '—', '—', '10.8%'], ['Global rate', '0.3854', '—', '0.500', '24.0%']],
  [0.28, 0.16, 0.16, 0.14, 0.26]));
add(P('All registered pass conditions held. In the secondary, analysis-only bootstrap, the 95% contract-clustered interval for the gain over activity logistic regression is [0.039, 0.080] nats (18 contracts) and the date-clustered interval is [0.047, 0.073]. The robustness results below use all 20 contributing contracts (18,677 known outcomes; log loss 0.2948 against 0.3527): the booster won on 7 of 7 dates and 17 of 20 contracts, and the nonoverlapping subset (0.2922 against 0.3471) and the strict subset (0.1554 against 0.2270) agree. For the development cohort, the worst-case missing-outcome bounds over 19,304 issued forecasts are [−0.001, +0.100] nats: the lower end is slightly negative under the most adverse assignment of the 2,851 unknown endpoints.'));
add(H2('6.3 Never-used contracts: 8–14 June'));
add(P('To test transfer to new identities, 40 contracts were selected by metadata only. Their identifiers lie in a hexadecimal range disjoint from every earlier cohort, they are binary Yes/No, at most one is taken per event and none shares an event with earlier cohorts, and they were open across the whole week. They span sports, politics, finance, technology and geopolitics. A local DNS outage failed 74 hourly downloads on both permitted attempts. Before any evaluation, those hours were refetched outcome-blind into a separate directory, and 165 of 168 hours were then available. This exceeds the single-retry rule, so it is recorded as a protocol deviation. The original source is preserved unevaluated.'));
add(Tbl('Matched results, 8–14 June, never-used contracts (35 contributing contracts, 35,218 known outcomes, 8,830 positives).',
  ['Model', 'Log loss', 'Brier', 'AUC', 'Booster log-loss reduction'],
  [['**row_hgb7**', '**0.4208**', '**0.1335**', '0.827', '—'], ['Activity logistic', '0.4943', '0.1584', '0.756', '14.9%'],
   ['Legacy HGB', '0.4873', '0.1547', '0.785', '13.6%'], ['Global / contract rate', '0.5843', '0.1945', '0.500', '28.0%'],
   ['V03 hgb7 (live model)', '0.4270', '0.1358', '0.825', '19.7% vs its full logistic'] ],
  [0.28, 0.16, 0.16, 0.14, 0.26]));
add(P('All registered pass conditions held, including the positive bootstrap lower bound. The contract-clustered interval for the gain over logistic regression is [0.033, 0.119] nats from 35 clusters. The booster won on 7 of 7 dates and 27 of 35 contracts, and its equal-contract-weighted log loss is 0.4222 against 0.5134. The worst-case missing-outcome bounds over all 39,656 issued forecasts are [+0.009, +0.114] nats, positive even if every unknown endpoint had gone against the booster. A secondary analysis of the V03 live model, registered before evaluation, gave a 19.7% reduction with interval [0.066, 0.147] and wins on 31 of 35 contracts. That cleared V03 for the live test in Chapter 7.'));
add(Figure('docs/figures/fig1_evidence_ladder.png', 6.0, 'Log-loss gain of the frozen booster over logistic regression on the two unopened June blocks, with 95% contract-clustered bootstrap intervals. Contributing contracts are given in parentheses.'));
add(H2('6.4 Calibration, drivers and category breakdown'));
add(P('Figure 3 shows that on 8–14 June both models are close to the diagonal below a forecast probability of 0.2, where most forecasts lie. Both under-predict somewhat in the upper deciles, the booster slightly less at the top. Because the evaluation must not change the frozen model, no recalibration was applied.'));
add(Figure('docs/figures/fig2_calibration_june8_14.png', 3.6, 'Reliability diagram for the booster and logistic regression on 8–14 June (decile bins of forecast probability).'));
add(P('On 1–7 June (Figure 4) both models over-forecast, which is consistent with a lower change rate in June than in the May training data. The expected calibration error is 0.046 for the booster and 0.052 for logistic regression. This differs from 8–14 June, where both models under-predicted in the upper deciles. The booster’s forecasts are also sharper: its decile forecasts span 0.02 to 0.59, against 0.08 to 0.44 for logistic regression. These descriptions do not decompose the score gain into calibration and resolution components. Recalibration could improve both models, but it would need a new frozen version and a new unopened block, since these blocks are consumed.'));
add(Figure('docs/figures/fig6_calibration_june1_7.png', 3.6, 'Reliability diagram on 1–7 June, development cohort (decile bins), with equal-frequency expected calibration error.'));
add(P('**What the booster relies on.** To describe which inputs the fitted booster uses, the frozen booster was re-applied to the consumed 1–7 June grid ledger (reproducing the stored forecasts exactly). Each feature group was then permuted jointly across rows, ten times, and the resulting increase in log loss was recorded (Figure 5). Recent midpoint moves dominate: permuting the 30-, 5- and 15-minute groups raises log loss by 0.021, 0.019 and 0.018 nats. Price level (0.015), update activity (0.008) and spread (0.006) follow. Quote freshness and time of day contribute almost nothing (at most 0.0004). The low weight of the age features is consistent with the V03 live model dropping them. It does not reduce the need for an accurate clock, which still governs input selection, eligibility and emission deadlines. Jointly permuting the nine inputs that only the booster sees raises its log loss by 0.013 nats, 21% of its 0.059-nat advantage over logistic regression, and the perturbed booster still beats logistic regression. This is a sensitivity analysis of a fitted model, not a decomposition of the gap into extra inputs and nonlinearity: permutation also breaks deterministic links between features, such as midpoint and its log-odds, or signed and absolute changes. Isolating the role of nonlinearity would need a separately designed comparison with matched features. Permutation importance is descriptive and correlated features share credit, which is why features are permuted in groups.'));
add(Figure('docs/figures/fig5_booster_drivers.png', 6.0, 'Permutation importance of feature groups for the frozen booster on 1–7 June (16,453 forecasts). Labels give each increase as a share of the booster’s log-loss gap over logistic regression.'));
add(P('As a descriptive check, contracts were assigned to categories by a fixed keyword rule on the question text, written before scores were joined. The booster has lower log loss than logistic regression in every observed category in both weeks (Table 7, Figure 6), so gains appear across all observed categories. This does not show how much each category contributes to the aggregate gain. Most categories contain only two to twelve contracts, so these are descriptions, not separate tests.'));
add(Tbl('Booster log-loss reduction against activity logistic regression by category (descriptive, post hoc keyword rule).',
  ['Block / category', 'Contracts', 'Known', 'Reduction', 'Contracts won', '95% contract CI (nats)'],
  [['June 1–7 sports', '5', '5,670', '22.1%', '5/5', '[0.038, 0.103]'], ['June 1–7 finance/crypto', '6', '3,670', '17.5%', '5/6', '[0.033, 0.101]'],
   ['June 1–7 politics', '5', '5,425', '11.8%', '4/5', '[0.001, 0.075]'], ['June 1–7 entertainment', '2', '1,688', '15.9%', '2/2', 'too few'],
   ['June 8–14 sports', '12', '11,498', '10.3%', '9/12', '[0.001, 0.096]'], ['June 8–14 finance/crypto', '8', '7,167', '12.1%', '6/8', '[−0.028, 0.248]'],
   ['June 8–14 politics', '6', '6,927', '14.3%', '5/6', '[−0.016, 0.116]'], ['June 8–14 geopolitics', '4', '6,335', '28.8%', '4/4', '[0.044, 0.241]'],
   ['June 8–14 tech/science', '3', '2,680', '14.7%', '2/3', '[−0.038, 0.273]'], ['June 8–14 entertainment', '2', '611', '1.7%', '1/2', 'too few']],
  [0.28, 0.12, 0.11, 0.12, 0.14, 0.23]));
add(Figure('docs/figures/fig3_category_breakdown.png', 6.0, 'Booster log-loss reduction by market category in each June block. Point labels give the number of contracts.'));
add(P('**Post hoc robustness checks.** After both June blocks had been consumed, three further checks were run on their stored forecasts (`eventx/tasks/analyze_v7_dependence_coverage_20261028.py`). Nothing was refit or regenerated, and the definitions were fixed in the script before its first run. Two diagnostics added after that run are labelled as such in the output.'));
add(P('*Joint dependence.* A two-way (pigeonhole) bootstrap resamples contracts and dates independently and weights each row by the product of its contract’s and date’s multiplicities (Owen, 2007). It assumes contract and date effects combine without a strong interaction, and with seven dates per block the date dimension is estimated imprecisely. The booster’s gain over activity logistic regression stays above zero: [0.031, 0.092] nats on 1–7 June and [0.022, 0.126] on 8–14 June, against [0.039, 0.080] and [0.033, 0.119] for contracts alone. Grouping contracts by event gives the same result, because no two contributing contracts share an event. The gain over the legacy booster on 1–7 June does not survive: its two-way interval is [−0.007, 0.092].'));
add(P('*Coverage.* Of the 96,600 scheduled decisions on 1–7 June, 48.0% fell after the contract’s listed end date (current metadata, so approximate), 21.1% in contract-days with no issued forecast and 10.9% within otherwise active contract-days; 32 of the 50 development contracts issued nothing. On 8–14 June the shares were 0.0%, 29.3% and 19.4%, and 5 of 40 contracts issued nothing. Within active contract-days, 64.8% and 72.6% of decisions were issued. The gain over activity logistic regression does not shrink on poorly covered contract-days: in the lowest third by coverage it is 0.071 and 0.088 nats, against 0.058 and 0.069 in the highest third. Across contracts, the Spearman correlation between coverage and gain is −0.11 (18 contracts) and −0.16 (35). Within the issued forecasts, selection therefore does not appear to favour the booster; nothing can be said about decisions that were never issued.'));
add(P('*An online contract rate.* None of the fixed baselines learns from a contract’s own outcomes. A simple online reference does: at each decision it takes the share of changes among the contract’s own earlier outcomes that had already matured (decisions at least 35 minutes earlier), shrunk toward the stored global rate with 20 pseudo-observations, as in the frozen per-contract baseline. It involves no additional offline fitting or tuning: its prior is the stored training-derived global rate, its pseudocount is fixed, and its contract estimate is updated online. Only this one variant was computed. Table 8 compares it with the booster.'));
add(Tbl('Post hoc comparison of the frozen booster with an online contract rate built from matured outcomes. Gains are rate minus booster; positive values favour the booster.',
  ['Block', 'Booster LL', 'Online rate LL', 'LL gain (nats)', '95% contract CI', '95% contract × date CI', 'Brier gain [95% CI]', 'AUC booster / rate', 'Won: contracts; dates'],
  [['1–7 June', '0.2931', '0.3143', '0.021 (6.7%)', '[−0.006, 0.057]', '[−0.018, 0.073]', '0.0094 [0.0007, 0.0231]', '0.835 / 0.790', '11/18; 7/7'],
   ['8–14 June', '0.4208', '0.4231', '0.002 (0.5%)', '[−0.028, 0.033]', '[−0.040, 0.041]', '0.0080 [−0.0016, 0.0178]', '0.827 / 0.824', '17/35; 3/7']],
  [0.09, 0.09, 0.09, 0.10, 0.11, 0.12, 0.15, 0.11, 0.14]));
add(P('On the 35 new contracts, the online rate reaches almost the booster’s log loss and AUC, and both the contract and the contract × date intervals include zero. On 1–7 June the booster is ahead on every date and on Brier, but both log-loss intervals again include zero. Intervals this wide do not show that the two forecasts are equivalent; they show that these blocks cannot separate them. The similar scores are consistent with much of the booster’s advantage over activity logistic regression coming from how persistent each contract’s activity level is, which the booster would infer from recent quotes and the online rate from realised outcomes, but they do not establish that mechanism. Both forecasts are available from a contract’s first decision: with no matured outcomes the online rate returns its global prior, and only its contract-specific part waits for outcomes. Whether the booster has an advantage early in a contract’s history was not tested. This comparison was made after the June results were known and does not change any frozen result or pass rule. It does change what those results show: the booster beats the specified fixed baselines, not every simple reference. Whether a booster that also sees the online rate improves on both is a question for new data (Section 9.3).'));
add(H2('6.5 A further unopened fortnight: 15–28 June'));
add(P('A third test on 15–28 June uses 21 further never-used contracts, frozen from metadata in a new identifier range before any price was read. An earlier selection with a stricter end-date rule found only 15 contracts. It was superseded before any data was read and is preserved. Both frozen models are scored in a single once-only evaluation under the June 8–14 rule, including the positive contract-clustered lower bound (Table 9). Capture was deferred until after the live window to avoid loading the live host.'));
add(Tbl('Matched results, 15–28 June, never-used contracts. Gains are comparator minus booster log loss.',
  ['Model vs comparator', 'Log loss', 'Reduction', '95% contract CI (nats)', 'Known / missing', 'Contracts won', 'Frozen rule'],
  [['row_hgb7 vs activity logistic', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]'],
   ['V03 hgb7 vs its full logistic', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]', '[[PENDING]]']],
  [0.24, 0.13, 0.11, 0.16, 0.14, 0.11, 0.11]));
add(P('[[PENDING]]'));

add(H1('7 Prospective Live Test'));
add(H2('7.1 Design'));
add(P('Historical replay cannot rule out subtle advantages from hindsight, such as metadata that is only known today or receive clocks that are reconstructed. A prospective test removes both. The live runtime is split into a **source** process and an **emitter** process:'));
add(B('the **source** subscribes to the Polymarket WebSocket for the cohort and polls metadata. It writes every message to an append-only journal in which each record carries the SHA-256 hash of the previous one;'));
add(B('the **emitter** reads that journal and, at each five-minute grid time, issues a forecast from the frozen V03 model or records an abstention with machine-readable reasons. Each forecast is committed at least 250 ms before its grid time.'));
add(P('An evaluator scores the forecasts once, after the window closes, against endpoints taken from the same journal. The cohort is 30 contracts, chosen by metadata only. They are active, binary, order-book enabled, at least seven days old, resolve no earlier than 10 November, have at least $10k of 24-hour volume (used as a floor only), are taken in salted-hash order with one contract per event, and are disjoint from every earlier cohort.'));
add(H2('7.2 Engineering problems and their solutions'));
add(P('Each problem below caused a rehearsal or activation to be stopped and archived, never patched in place.'));
add(B('**Unreliable host clock.** The first runtime version failed its readiness rehearsal with 0 of 16 decisions ready. The laptop’s built-in time client returned empty server packets while the clock was about 287 ms fast, and the operating system then stepped the clock back by 110 ms, which reset the transport warmup. The new version uses its own SNTP client (Mills et al, 2010). It keeps the raw packets and recomputes offsets from them. An estimate is accepted only if at least two servers agree, at least one round trip is short, and the residual uncertainty is at most 50 ms. Corrected time is then carried forward on the monotonic clock, so operating-system clock steps are logged but cannot move decision times.'));
add(B('**Memory and latency growth.** The first activation kept the whole journal in memory (about 317 MB per hour) and rescanned it at every decision. A bounded, incremental input store keeps three hours of history, more than every rule needs. It matched the unbounded version in 510 of 510 decision and endpoint comparisons, and cut decision time from 370 ms to 11 ms per grid.'));
add(B('**A thread race in the hash chain.** In the second activation, a clock-probe thread wrote to the journal at the same time as the main loop, which forked the hash chain. The emitter’s chain check detected this and stopped. Now only the event loop writes the journal, and a regression test enforces it.'));
add(P('After these fixes, a fresh 60-minute readiness rehearsal passed. 156 of 180 post-warmup decisions were ready, across 27 of 30 contracts; 58 of 61 clock estimates were valid; one OS clock step was absorbed; and there were 0 chain breaks, stamp errors or replay mismatches. The test was activated at 17:53:53 UTC on 26 October, with grids from 27 October 00:30 to 29 October 23:25 UTC (24,840 scheduled decisions). The window was shortened from seven days to three, before any prospective decision, so that it would finish before this report’s deadline.'));
add(H2('7.3 Operation'));
add(P('The test has known operating losses, all recorded rather than repaired:'));
add(B('**First grid.** All 30 decisions abstained, because the emitter’s pre-loaded inputs were handed over without one final refresh (0.12% of the schedule).'));
add(B('**Host stall.** A concurrent analysis job pushed the already memory-constrained laptop into heavy swapping, so four grids missed their emission deadlines and roughly an hour of warmup abstentions followed. Heavy jobs were then deferred until the window closed.'));
add(B('**Sleep and reboot.** On 27 October at 04:42 UTC the laptop, running on battery with its lid closed, entered clamshell sleep, which `caffeinate` cannot prevent. It then rebooted at 05:16 UTC. The source and emitter did not survive. The frozen protocol forbids restarting the source into the same run, so every later grid in that run counts as abstained or missed. At the 05:19 UTC status check the ledger held 725 ready decisions, 715 abstentions and 300 misses. The run could not be resumed, and its frozen evaluator cannot score it, because the source never wrote its closing capture manifest. With the user’s authorisation, a separately versioned continuation (**V02b**) was activated at 05:47 UTC before any V02 outcome was read. V02b reuses every frozen V02 file, the V03 model and the 30-contract cohort unchanged. Only the run directory and the window differ: grids from 27 October 06:35 to 29 October 23:25 UTC, 22,650 scheduled decisions. V02b is the live result reported in Section 7.5.'));
add(B('**Second sleep (V02b).** From 07:40 to 08:26 UTC on 27 October the lid was closed again. The laptop was on mains power, but sleep had not yet been disabled system-wide, so it slept. The V02b processes survived, but nine grids (270 decisions) passed their emission deadlines and count as missed. Sleep was then disabled at system level (`pmset disablesleep 1`).'));
add(B('**Venue disconnects.** Outside the stall and sleep episodes, the venue WebSocket disconnected about every three to six hours: three times in about 9.5 hours of V02, and three times in about 17 hours of V02b up to 28 October 01:40 UTC. Each reconnect costs 30 minutes of abstentions under the frozen warmup rule. Bursts of disconnects coincided with the host stall and the sleeps.'));
add(P('These losses reduce coverage but cannot leak information, since every failure leads to a recorded abstention or miss and nothing is backfilled.'));
add(H2('7.4 Lessons for operating a prospective forecaster'));
add(P('The live track produced engineering evidence of its own. Every incident below ended in an abstention rather than a confident wrong forecast, and every one is preserved. The common thread is that a forecaster that abstains honestly can be measured, whereas one that silently fills gaps cannot.'));
add(Tbl('Operational incidents and lessons.', ['Incident', 'Design response', 'Lesson'],
  [['Host clock: empty SNTP packets, −110 ms OS step', 'Packets rejected; warmup reset; readiness gate failed', 'Fix the clock, not the gate; own validated SNTP client'],
   ['Memory growth (317 MB/h)', 'Stopped before first grid; 0 forecasts', 'Load-test at full horizon before activation'],
   ['Thread race in hash chain', 'Chain check stopped the emitter', 'Single-writer journals, enforced by test'],
   ['DNS outage during capture', 'Outcome-blind refetch to a separate directory', 'Retry rules need an explicit outage clause'],
   ['First-grid handoff', '30 abstentions (0.12%)', 'Rehearse the activation handoff end to end'],
   ['Swap stall from a concurrent job', '4 grids missed; warmup abstentions', 'Separate production and research hosts'],
   ['Lid-closed sleep and reboot', 'Run ended; no backfill', 'Always-on host: AC power, sleep disabled, service restart'],
   ['Second lid-closed sleep (V02b, on AC)', '9 grids (270 decisions) missed; processes survived', 'Disable sleep system-wide before activation, not per process']],
  [0.32, 0.36, 0.32]));
add(H2('7.5 Results'));
add(P('The live test has no pass rule. Its registered primary comparison is matched log loss of V03 hgb7 against its full logistic regression, with the global rate as a second comparator, and scores are reported only if at least 100 outcomes are known, with at least 20 of each class. The evaluation runs once after 29 October 23:57:30 UTC and is reported whatever the sign (Table 11).'));
add(Tbl('Live V02b test: coverage and matched scores. Gains are comparator minus V03 hgb7 log loss.',
  ['Quantity', 'Value'],
  [['Scheduled decisions', '22,650'], ['Issued on time (coverage)', '[[PENDING]]'], ['Abstained, missed or uncommitted', '[[PENDING]]'],
   ['Known / unknown outcomes (positives)', '[[PENDING]]'], ['Reporting floor met', '[[PENDING]]'],
   ['Log loss: V03 hgb7 / full logistic / global rate', '[[PENDING]]'], ['Brier: V03 hgb7 / full logistic / global rate', '[[PENDING]]'],
   ['AUC: V03 hgb7 / full logistic', '[[PENDING]]'], ['Relative log-loss reduction vs full logistic', '[[PENDING]]'],
   ['95% contract-clustered interval of the gain (nats)', '[[PENDING]]'], ['Missing-outcome bounds over all issued forecasts (nats)', '[[PENDING]]']],
  [0.60, 0.40]));
add(P('[[PENDING]]'));

add(H1('8 Discussion'));
add(H2('8.1 What the evidence supports'));
add(P('The answers to RQ1 and RQ2 differ sharply. Simple news counts did not improve a market-history forecaster under strict availability rules, while a microstructure target was forecast better than the specified baselines on both evaluated unopened June blocks. This is consistent with a market in which public news is either quickly priced or too weakly linked to individual contracts to be detected by counts, whereas quote activity is persistent and well summarised by recent quote changes, spread and price level. Why the booster wins is not settled. Jointly permuting the inputs unavailable to logistic regression removed about a fifth of its advantage, but as a sensitivity analysis of a fitted model this does not attribute the advantage to either those inputs or nonlinearity. A post hoc online contract rate, which only tracks each contract’s own realised change rate, came close to the booster on the new contracts (Table 8). This is consistent with much of the advantage over activity logistic regression coming from persistent contract-level activity, which a fixed nine-input logistic model does not capture, but it does not establish that explanation.'));
add(H2('8.2 Threats to validity'));
add(B('**Dependence.** Forecasts from one contract are strongly correlated. This is why the headline intervals resample whole contracts, and why the effective sample size is closer to the number of contracts (18–35) than to the number of rows. Contracts also share calendar dates and therefore common information shocks. A post hoc two-way bootstrap over contracts and dates widens the intervals but leaves both June gains over activity logistic regression above zero (Section 6.4). With only seven dates per block, the date dimension is itself estimated imprecisely.'));
add(B('**Comparator strength.** The primary comparator uses nine of the booster’s 18 inputs (Section 5.4), and no full-feature logistic regression, smooth nonlinear model or comparably tuned alternative ensemble was fitted for the June blocks. A post hoc online contract rate came within 0.5% of the booster’s log loss on 8–14 June (Table 8). The June results show improvement over the specified baselines, not over the strongest reasonable baseline, and they do not attribute the gain to nonlinearity.'));
add(B('**Coverage and selection.** Forecasts were issued for 19,304 of 96,600 scheduled decisions in 1–7 June (20.0%) and 39,656 of 77,280 in 8–14 June (51.3%). On 1–7 June, 48.0% of scheduled decisions fell after the contract’s listed end, and on both blocks most of the rest fell in contract-days with no valid quote (Section 6.4), so the shortfall mainly reflects inactive or expired contracts and the frozen quote-validity gates rather than feed failures. Within the issued forecasts the gain does not shrink on poorly covered contract-days, but the scores still describe the issued, active part of the market. The missing-outcome bounds cover unknown endpoints among issued forecasts, not decisions that were never issued.'));
add(B('**Temporal breadth.** The historical evidence spans two June weeks, plus the pending late-June fortnight. Chronological transfer on familiar contracts and transfer to new contracts have been tested; transfer to new event families, sustained prospective issuance and transfer to another venue have not.'));
add(B('**Cohort and venue.** Cohorts are convenience samples that require quotes to be available, and all Track B evidence comes from one venue and one era (2026). The new-contract test reduces, but does not remove, the risk that results depend on contract identity.'));
add(B('**Metadata timing.** Historical cohorts use current metadata, so a contract’s present description may differ from what was known in June. Only the live test is free of this.'));
add(B('**Conditioning on observed endpoints.** Scores use only forecasts with observed endpoints. The worst-case bounds show that missing endpoints cannot reverse the June 8–14 conclusion, but in June 1–7 the lower bound falls just below zero.'));
add(B('**Protocol deviations.** The DNS refetch and the V3.1 prevalence exposure are real departures from the intended protocols. They were outcome-blind or happened before any metric was computed, but they are disclosed rather than argued away.'));
add(B('**Causal language.** None of the results is causal. Track A estimates predictive value conditional on observable news; information that surfaces first on unobserved channels (private chats, livestreams) remains a confounder.'));

add(H1('9 Conclusions'));
add(H2('9.1 Summary'));
add(P('EventX built a leakage-safe evaluation framework for prediction-market forecasting and applied it to two questions. In a frozen study of 4,651 markets, simple news-count augmentation failed the specified development promotion gates. A frozen gradient-boosted quote-change classifier improved matched historical scores against the specified baselines on two unopened June blocks, including a cohort of 35 never-used contracts: log loss fell by 16.8% and 14.9% against activity logistic regression, with contract-clustered intervals above zero. A post hoc online contract rate came within 0.5% of the booster’s log loss on the new contracts, so the gain is over the specified fixed baselines rather than over every simple reference. A prospective runtime with validated clock correction, bounded inputs and tamper-evident journals was built, and a three-day live test was started; prospective performance remains pending. [[PENDING: one-sentence live and V4 outcome.]]'));
add(H2('9.2 Limitations'));
add(B('The quote-change target measures activity, not direction, size or profit. A good score does not imply a trading edge.'));
add(B('Track B uses one venue and small numbers of contributing contracts, and historical cohorts rely on current metadata.'));
add(B('The primary comparator is weaker than a matched-input baseline, so the June gains are not attributed to nonlinearity. A post hoc online contract rate scored close to the booster on the new contracts; the blocks cannot separate the two, and quote features have not been shown to add value beyond a contract’s own recent outcomes. Scores describe issued forecasts, which covered 20.0% and 51.3% of scheduled decisions in the two June blocks.'));
add(B('Track A tested count-based news representations under conservative timestamps. The negative result applies to that representation; it does not show that public news carries no information. Contract–event links and first-availability times were not independently verified, and richer text models and social-media signals were not evaluated within the frozen protocols.'));
add(B('The live test ran on a laptop whose memory pressure, sleeps and network drops reduced coverage. A disciplined server would give a cleaner prospective estimate.'));
add(B('The news bound, permutation importance and category breakdown are post hoc descriptive analyses of already-opened data; none was used to change a frozen model.'));
add(H2('9.3 Recommendations for further work'));
NewList();
add(N('Include the online contract rate from Section 6.4 and its matured-outcome count as registered inputs and baselines. On new data only, compare logistic, GAM and boosting models given the rate with the rate alone, and test whether quote features add value beyond a contract’s own recent outcomes, including early in each contract’s history.'));
add(N('Compare learners and inputs factorially: logistic regression, a spline or GAM model and gradient boosting, each on the same nine activity inputs and on the same full input set, with regularisation and tuning budgets matched and selected on purged forward development folds. Add an adaptive activity-rate baseline that uses only outcomes already observed at each decision. This separates the contribution of nonlinearity from that of the extra inputs, which permutation importance cannot do.'));
add(N('Test calibration on a dedicated development calibration split, scoring log loss, Brier and reliability, since calibration can improve probability quality without changing AUC.'));
add(N('Run the live runtime on a dedicated host with a disciplined clock and enough memory, for at least seven days, on a larger metadata-selected cohort.'));
add(N('Extend the target to signed and size-graded quote moves, which are closer to economically meaningful questions, keeping the same once-only protocol.'));
add(N('Re-test news value only after contract–event links are independently reviewed and release and first-availability times are evidenced, comparing market-only, news-volume, context-only and content-based models on identical rows, with the quote-change model as the market-only baseline.'));
add(N('Widen the independent evidence: more event families, longer periods and different liquidity and expiry regimes, with the number of contracts set by cluster-level precision planning on development data rather than by row counts. As a preliminary guide only, scaling the 8–14 June contract-clustered interval against the online rate suggests several hundred contracts (roughly 660 for 80% power at 0.01 nats). That figure ignores date dependence, the length of the test period and the loss of inactive contracts, all of which must be planned jointly before a study is frozen.'));
add(N('Replicate on Kalshi, whose historical intraday data has a different coverage pattern, to test venue transfer.'));

// ---------------------------------- references ----------------------------------------
const refs = [
  'Arrow, K.J., Forsythe, R., Gorham, M., Hahn, R., Hanson, R., Ledyard, J.O., Levmore, S., Litan, R., Milgrom, P., Nelson, F.D., Neumann, G.R., Ottaviani, M., Schelling, T.C., Shiller, R.J., Smith, V.L., Snowberg, E., Sunstein, C.R., Tetlock, P.C., Tetlock, P.E., Varian, H.R., Wolfers, J. and Zitzewitz, E. (2008). The Promise of Prediction Markets. *Science*, Vol. 320, No. 5878, pp. 877 – 878.',
  'Brier, G.W. (1950). Verification of Forecasts Expressed in Terms of Probability. *Monthly Weather Review*, Vol. 78, No. 1, pp. 1 – 3.',
  'Cameron, A.C., Gelbach, J.B. and Miller, D.L. (2008). Bootstrap-Based Improvements for Inference with Clustered Errors. *Review of Economics and Statistics*, Vol. 90, No. 3, pp. 414 – 427.',
  'Croxson, K. and Reade, J.J. (2014). Information and Efficiency: Goal Arrival in Soccer Betting. *The Economic Journal*, Vol. 124, No. 575, pp. 62 – 91.',
  'Diercks, A.M., Katz, J.D. and Wright, J.H. (2026). Kalshi and the Rise of Macro Markets. NBER Working Paper No. 34702, National Bureau of Economic Research, Cambridge, Massachusetts.',
  'Engle, R.F. and Russell, J.R. (1998). Autoregressive Conditional Duration: A New Model for Irregularly Spaced Transaction Data. *Econometrica*, Vol. 66, No. 5, pp. 1127 – 1162.',
  'Friedman, J.H. (2001). Greedy Function Approximation: A Gradient Boosting Machine. *Annals of Statistics*, Vol. 29, No. 5, pp. 1189 – 1232.',
  'Gneiting, T. and Raftery, A.E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. *Journal of the American Statistical Association*, Vol. 102, No. 477, pp. 359 – 378.',
  'Grinsztajn, L., Oyallon, E. and Varoquaux, G. (2022). Why Do Tree-Based Models Still Outperform Deep Learning on Typical Tabular Data? *Advances in Neural Information Processing Systems 35* (Datasets and Benchmarks Track), pp. 507 – 520.',
  'Hasbrouck, J. (2007). *Empirical Market Microstructure: The Institutions, Economics, and Econometrics of Securities Trading.* Oxford University Press, New York, 2007.',
  'Kapoor, S. and Narayanan, A. (2023). Leakage and the Reproducibility Crisis in Machine-Learning-Based Science. *Patterns*, Vol. 4, No. 9, Article 100804.',
  'Kaufman, S., Rosset, S., Perlich, C. and Stitelman, O. (2012). Leakage in Data Mining: Formulation, Detection, and Avoidance. *ACM Transactions on Knowledge Discovery from Data*, Vol. 6, No. 4, Article 15.',
  'Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q. and Liu, T.-Y. (2017). LightGBM: A Highly Efficient Gradient Boosting Decision Tree. In *Advances in Neural Information Processing Systems 30* (Long Beach, California, December 4 – 9, 2017), pp. 3146 – 3154.',
  'Kolm, P.N., Turiel, J. and Westray, N. (2023). Deep Order Flow Imbalance: Extracting Alpha at Multiple Horizons from the Limit Order Book. *Mathematical Finance*, Vol. 33, No. 4, pp. 1044 – 1081.',
  'Künsch, H.R. (1989). The Jackknife and the Bootstrap for General Stationary Observations. *Annals of Statistics*, Vol. 17, No. 3, pp. 1217 – 1241.',
  'López de Prado, M. (2018). *Advances in Financial Machine Learning.* John Wiley & Sons, Hoboken, New Jersey, 2018.',
  'Mills, D., Martin, J. (Ed.), Burbank, J. and Kasch, W. (2010). Network Time Protocol Version 4: Protocol and Algorithms Specification. RFC 5905, Internet Engineering Task Force, June 2010.',
  'Niculescu-Mizil, A. and Caruana, R. (2005). Predicting Good Probabilities with Supervised Learning. In *Proceedings of the 22nd International Conference on Machine Learning* (Bonn, Germany, August 7 – 11, 2005). ACM, New York, 2005, pp. 625 – 632.',
  'Ntakaris, A., Magris, M., Kanniainen, J., Gabbouj, M. and Iosifidis, A. (2018). Benchmark Dataset for Mid-Price Forecasting of Limit Order Book Data with Machine Learning Methods. *Journal of Forecasting*, Vol. 37, No. 8, pp. 852 – 866.',
  'O’Hara, M. (1995). *Market Microstructure Theory.* Blackwell Publishers, Cambridge, Massachusetts, 1995.',
  'Owen, A.B. (2007). The Pigeonhole Bootstrap. *The Annals of Applied Statistics*, Vol. 1, No. 2, pp. 386 – 411.',
  'Page, L. and Clemen, R.T. (2013). Do Prediction Markets Produce Well-Calibrated Probability Forecasts? *The Economic Journal*, Vol. 123, No. 568, pp. 491 – 513.',
  'Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D., Brucher, M., Perrot, M. and Duchesnay, E. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*, Vol. 12, pp. 2825 – 2830.',
  'Polymarket. (2026). Polymarket CLOB and Gamma API Documentation. Online documentation, accessed October 2026.',
  'Sirignano, J. and Cont, R. (2019). Universal Features of Price Formation in Financial Markets: Perspectives from Deep Learning. *Quantitative Finance*, Vol. 19, No. 9, pp. 1449 – 1459.',
  'Snowberg, E., Wolfers, J. and Zitzewitz, E. (2007). Partisan Impacts on the Economy: Evidence from Prediction Markets and Close Elections. *Quarterly Journal of Economics*, Vol. 122, No. 2, pp. 807 – 829.',
  'Tetlock, P.C. (2007). Giving Content to Investor Sentiment: The Role of Media in the Stock Market. *Journal of Finance*, Vol. 62, No. 3, pp. 1139 – 1168.',
  'Wolfers, J. and Zitzewitz, E. (2004). Prediction Markets. *Journal of Economic Perspectives*, Vol. 18, No. 2, pp. 107 – 126.',
  'Zhang, Z., Zohren, S. and Roberts, S. (2019). DeepLOB: Deep Convolutional Neural Networks for Limit Order Books. *IEEE Transactions on Signal Processing*, Vol. 67, No. 11, pp. 3001 – 3012.',
];
const references = [H1('References'), ...refs.map(r => new Paragraph({ children: runs(r), spacing: { line: LINE15, after: 120 }, indent: { left: 567, hanging: 567 }, alignment: AlignmentType.LEFT }))];

// ---------------------------------- appendices ----------------------------------------
compact = true;
const AH = (t) => (headings.push([1, t]), new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT, size: 28, bold: true, color: '000000' })], spacing: { after: 200 } }));
const appA = [AH('Appendix A – Feature Definitions'),
  P('All features are computed from YES-token quotes received at or before the decision time *t*. A quote state is valid when bid < ask, both lie strictly inside (0, 1), and the spread is at most 0.05. Missing lag values are encoded as zero together with a missing flag.'),
  ...Tbl('The 18 features of row_hgb7. Features marked * are also used by the 14-feature V03 live model.',
    ['Feature', 'Definition'],
    [['midpoint*', '(best bid + best ask) / 2 of the current valid quote'], ['logit_midpoint*', 'ln(m / (1 − m)) of the midpoint'], ['spread*', 'best ask − best bid'],
     ['source_age', 'seconds since the venue timestamp of the current quote'], ['receive_age', 'seconds since the receive timestamp of the current quote'],
     ['hour_sin*, hour_cos*', 'UTC hour of day on the unit circle'], ['log_valid_updates30', 'log(1 + number of valid quote states in the last 30 min)'],
     ['valid_state_fraction30', 'number of valid quote states divided by the number of recorded quote states in the last 30 min'],
     ['delta5*, abs_delta5*, missing5*', 'signed and absolute midpoint change since t − 5 min; flag if unavailable'],
     ['delta15*, abs_delta15*, missing15*', 'same over 15 minutes'], ['delta30*, abs_delta30*, missing30*', 'same over 30 minutes']],
    [0.36, 0.64]),
  P('The activity logistic baseline uses midpoint, spread, log_valid_updates30, abs_delta5, missing5, abs_delta15, missing15, abs_delta30 and missing30. All logistic models standardise inputs and use L2 regularisation with C = 0.1.'),
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
     ['June 15–28 cohort v1', 'Only 15/60 contracts passed the end-date rule', 'Superseded before any price read by v2 (21 contracts)']],
    [0.22, 0.42, 0.36]),
];
const appC = [AH('Appendix C – Reproducibility'),
  P('**Consistency check.** verify_report_reproducibility_20261027 re-hashes the files locked by the cited release and data manifests (1,147 files in 84 manifests; two earlier locks pass only through their documented successor manifests) and fails if any is missing or changed. It checks the 24 headline claims listed in report/claims.json (each with its artifact, cohort, model and comparator) against their artifact values, and confirms that each claim’s printed value still appears in the report source. It re-renders the figures from frozen outputs and checks that the PNGs are byte-identical, and with --recompute reruns the post hoc analyses. Numbers not listed in the claims file are not checked. It reads no holdout and starts no evaluation. Its first run, on 27 October, caught one rounding error in this report, now corrected. [[PENDING: final run after close-out.]]'),
  P('All code is in the EventX repository. Frozen releases live under eventx/release/, and results with their hash manifests under data/. The principal entry points are listed below (run from the repository root with the project virtual environment). Commands marked once-only consume their block and refuse to run again; they are listed for audit, not for re-running.'),
  ...Tbl('Principal scripts and outputs.', ['Purpose', 'Command or path'],
    [['June 1–7 test (consumed, once-only)', 'python -m eventx.tasks.run_v7_june_replication_20261026'], ['June 8–14 test (consumed, once-only)', 'python -m eventx.tasks.run_v7_new_identity_test_20261026 {select,capture,evaluate}'],
     ['V03 secondary (consumed, once-only)', 'python -m eventx.tasks.evaluate_v7_new_identity_v03_20261026'], ['June 15–28 test (once-only)', 'python -m eventx.tasks.run_v7_late_june_test_20261027_v2 {capture,evaluate}'],
     ['Category breakdown', 'python -m eventx.tasks.analyze_v7_category_breakdown_20261027'], ['Figures', 'python -m eventx.tasks.plot_v7_report_figures_20261027'],
     ['Live runtime health (V02b)', 'python -m eventx.tasks.status_v7_forecast_runtime_20261026_v02b'], ['Live evaluation (V02b, once-only)', 'python -m eventx.tasks.evaluate_v7_forecast_runtime_20261026_v02b'],
     ['Close-out sequence (once-only)', 'zsh scripts/close_out_20261030.sh'],
     ['V4 close-out (once-only, in order)', 'audit_v4_confirmatory_collection, consume_v4_confirmatory_holdout, prepare_v4_confirmatory_inputs, build_v4_confirmatory_examples, evaluate_v4_confirmatory'],
     ['Runtime tests', 'python -m eventx.tasks.check_v7_forecast_runtime_20261026_v02 (32 tests; V02 code, reused unchanged by V02b)'],
     ['News bound (Section 4.3)', 'python -m eventx.tasks.analyze_v3_1_news_mde_20261027'],
     ['Booster drivers (Section 6.4)', 'python -m eventx.tasks.analyze_v7_booster_drivers_20261027'],
     ['One-command check', 'python -m eventx.tasks.verify_report_reproducibility_20261027 [--recompute]'],
     ['Claim-to-evidence map', 'report/claims.json'],
     ['Pending-result formatter (read-only)', 'python report/fill_pending_20261030.py']],
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
