/**
 * PDF + Image text extraction and Spanish payroll (nómina) parser.
 *
 * - PDFs:   uses pdf.js to extract text directly
 * - Images: uses Tesseract.js (OCR) to recognise Spanish text
 *
 * Then a shared parser pulls salary concepts out of the raw text.
 */
import * as pdfjsLib from 'pdfjs-dist';
import Tesseract from 'tesseract.js';

// pdf.js worker — CDN is most reliable with CRA / webpack 5
pdfjsLib.GlobalWorkerOptions.workerSrc =
  `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

// ─────────────────────────────────────────────────
// 1.  TEXT EXTRACTION
// ─────────────────────────────────────────────────

/**
 * Extract text from a PDF, reconstructing lines by Y-position.
 */
export async function extractTextFromPDF(file) {
  const buf = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: buf }).promise;

  const items = [];
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const content = await page.getTextContent();
    for (const it of content.items) {
      if (it.str.trim()) {
        items.push({
          text: it.str.trim(),
          x: Math.round(it.transform[4]),
          y: Math.round(it.transform[5]),
        });
      }
    }
  }

  // Group by row (Y ± 3 px)
  items.sort((a, b) => b.y - a.y || a.x - b.x);
  const lines = [];
  let row = [];
  let curY = items[0]?.y ?? 0;

  for (const it of items) {
    if (Math.abs(it.y - curY) > 3) {
      row.sort((a, b) => a.x - b.x);
      lines.push(row.map((r) => r.text).join('  '));
      row = [it];
      curY = it.y;
    } else {
      row.push(it);
    }
  }
  if (row.length) {
    row.sort((a, b) => a.x - b.x);
    lines.push(row.map((r) => r.text).join('  '));
  }

  return lines.join('\n');
}

/**
 * Extract text from an image via Tesseract OCR (Spanish).
 * @param {File} file  – JPEG / PNG image
 * @param {function} onProgress – optional (0-100)
 */
export async function extractTextFromImage(file, onProgress) {
  const worker = await Tesseract.createWorker('spa', 1, {
    logger: (m) => {
      if (onProgress && m.status === 'recognizing text') {
        onProgress(Math.round((m.progress || 0) * 100));
      }
    },
  });

  const { data } = await worker.recognize(file);
  await worker.terminate();
  return data.text;
}

// ─────────────────────────────────────────────────
// 2.  NUMBER HELPERS
// ─────────────────────────────────────────────────

/** Parse a single Spanish-format number: "1.507,00" → 1507  */
function parseES(str) {
  if (!str) return null;
  let c = str.replace(/[€\s]/g, '');
  if (c.includes(',') && c.includes('.')) c = c.replace(/\./g, '').replace(',', '.');
  else if (c.includes(',')) c = c.replace(',', '.');
  const n = parseFloat(c);
  return isNaN(n) ? null : n;
}

/** Pull every Spanish-format number out of a string. */
function pullNumbers(str) {
  // Matches: 1.507,00 | 1507,00 | 1507.00 | 507 | 30,00
  const hits = str.match(/\d[\d.]*,\d{2}|\d+\.\d{2}|\d+/g) || [];
  return hits.map(parseES).filter((n) => n !== null && n >= 0);
}

// ─────────────────────────────────────────────────
// 3.  PAYROLL PARSER
// ─────────────────────────────────────────────────

/**
 * Given a block of text (from PDF or OCR), find the line matching
 * any of `patterns` and return the best numeric value on that line.
 *
 *   minVal – ignore numbers smaller than this (filters day-counts
 *            like "30" when we're looking for a salary > 200).
 */
function findAmount(allLines, patterns, minVal = 50) {
  for (const pat of patterns) {
    const re = new RegExp(pat, 'i');
    for (const line of allLines) {
      if (!re.test(line)) continue;
      const nums = pullNumbers(line).filter((n) => n >= minVal);
      if (nums.length) return nums[0]; // first salary-sized number
      // fallback: any number on the line
      const any = pullNumbers(line);
      if (any.length) return any[any.length - 1];
    }
  }
  return null;
}

/**
 * Main parser – returns an object with the fields the engine expects.
 */
export function parsePayrollText(rawText) {
  // Normalise OCR artefacts
  const text = rawText
    .replace(/[|¦]/g, '')          // table borders
    .replace(/\r/g, '')
    .replace(/[ \t]+/g, ' ');      // collapse spaces

  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const result = {};

  // Store preview for debug
  result._rawTextPreview = lines.slice(0, 30).join('\n');

  // — Salario Base —
  const sb = findAmount(lines, [
    'salario\\s*base',
    'sueldo\\s*base',
    'sal\\.?\\s*base',
    's\\.?\\s*base',
    'retrib.*base',
  ], 200);
  if (sb) result.salarioBase = String(sb);

  // — Plus Convenio —
  const pc = findAmount(lines, [
    'plus\\s*conv',
    'compl.*conv',
    'plus\\s*puesto',
    'compl.*puesto',
    'mejora\\s*vol',
    'plus\\s*actividad',
    'plus\\s*productividad',
  ], 10);
  if (pc) result.plusConvenio = String(pc);

  // — Antigüedad —
  const ant = findAmount(lines, [
    'antig[uü\\.]',
    'trienio',
    'complemento.*antig',
    'plus.*antig',
    'quinquenio',
    'bienio',
  ], 5);
  if (ant) result.valorAntiguedad = String(ant);

  // — Nocturnidad —
  const noc = findAmount(lines, [
    'nocturn',
    'plus.*noche',
    'turno.*noche',
    'nocturno',
  ], 5);
  if (noc) result.valorNocturnidad = String(noc);

  // — Horas nocturnas —
  const hn = findAmount(lines, [
    'horas?.*noct',
    'h\\.?.*nocturna',
  ], 1);
  if (hn && hn < 200) result.horasNocturnas = String(hn);

  // — Dietas / transporte —
  const di = findAmount(lines, [
    'dietas?\\b',
    'plus.*transporte',
    'locomoci',
    'kilometraje',
    'manutenci',
    'quebranto',
  ], 5);
  if (di) result.dietas = String(di);

  // — Pagas —
  const pm = text.match(/(\d{2})\s*pagas/i);
  if (pm) {
    const p = parseInt(pm[1]);
    if ([12, 14, 15].includes(p)) result.pagas = String(p);
  }

  // — Prorrateo —
  if (/prorrat/i.test(text)) result.prorrateo = true;

  // — Convenio detection —
  const lo = text.toLowerCase();
  if (/mercadona/i.test(lo))               result.convenio = 'mercadona';
  else if (/leroy\s*merlin/i.test(lo))     result.convenio = 'leroy_merlin';
  else if (/transporte\s*sanitario/i.test(lo)) result.convenio = 'transporte_sanitario_andalucia';
  else if (/ambulancia/i.test(lo))         result.convenio = 'transporte_sanitario_andalucia';
  else if (/hosteler[ií]a/i.test(lo))      result.convenio = 'hosteleria';
  else if (/comercio/i.test(lo))           result.convenio = 'comercio';
  else if (/construcci[oó]n/i.test(lo))    result.convenio = 'construccion';

  return result;
}
