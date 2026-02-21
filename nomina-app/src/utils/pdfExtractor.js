/**
 * Payroll file reader – PDF (pdf.js) + Image OCR (Tesseract.js)
 *
 * Both libraries need web workers. To guarantee they load:
 *   • pdf.js  → worker copied to public/ (postinstall script)
 *   • Tesseract → downloads its own worker + language pack from CDN
 */

import * as pdfjsLib from 'pdfjs-dist';
import Tesseract from 'tesseract.js';

// pdf.js worker lives in public/ — copied by "postinstall" script.
pdfjsLib.GlobalWorkerOptions.workerSrc =
  `${process.env.PUBLIC_URL || ''}/pdf.worker.min.mjs`;

// ═════════════════════════════════════════════════════════════
// 1. TEXT EXTRACTION
// ═════════════════════════════════════════════════════════════

/** Read every text item from a PDF, group by Y row, return lines. */
export async function extractTextFromPDF(file) {
  const buf = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: buf }).promise;

  const items = [];
  for (let p = 1; p <= pdf.numPages; p++) {
    const page = await pdf.getPage(p);
    const { items: pageItems } = await page.getTextContent();
    for (const it of pageItems) {
      const t = it.str.trim();
      if (t) items.push({ text: t, x: Math.round(it.transform[4]), y: Math.round(it.transform[5]) });
    }
  }

  if (items.length === 0) return '';

  // sort top→bottom, left→right
  items.sort((a, b) => b.y - a.y || a.x - b.x);

  const lines = [];
  let row = [items[0]];
  let curY = items[0].y;

  for (let i = 1; i < items.length; i++) {
    if (Math.abs(items[i].y - curY) > 3) {
      row.sort((a, b) => a.x - b.x);
      lines.push(row.map((r) => r.text).join('  '));
      row = [items[i]];
      curY = items[i].y;
    } else {
      row.push(items[i]);
    }
  }
  row.sort((a, b) => a.x - b.x);
  lines.push(row.map((r) => r.text).join('  '));

  return lines.join('\n');
}

/** OCR an image (JPEG / PNG) with Tesseract in Spanish. */
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
  return data.text || '';
}

// ═════════════════════════════════════════════════════════════
// 2. NUMBER HELPERS
// ═════════════════════════════════════════════════════════════

function parseES(s) {
  if (!s) return null;
  let c = s.replace(/[€\s]/g, '');
  if (c.includes(',') && c.includes('.')) c = c.replace(/\./g, '').replace(',', '.');
  else if (c.includes(',')) c = c.replace(',', '.');
  const n = parseFloat(c);
  return isNaN(n) ? null : n;
}

/** Extract all Spanish-format numbers from a string. */
function nums(s) {
  return (s.match(/\d[\d.]*,\d{2}|\d+\.\d{2}|\d+/g) || [])
    .map(parseES)
    .filter((n) => n !== null && n >= 0);
}

// ═════════════════════════════════════════════════════════════
// 3. PAYROLL PARSER
// ═════════════════════════════════════════════════════════════

function findAmount(lines, patterns, min = 50) {
  for (const pat of patterns) {
    const re = new RegExp(pat, 'i');
    for (const line of lines) {
      if (!re.test(line)) continue;
      // Get numbers on this line that are >= min (skip day-counts like 30)
      const big = nums(line).filter((n) => n >= min);
      if (big.length) return big[0];
      // fallback: last number on line
      const all = nums(line);
      if (all.length) return all[all.length - 1];
    }
  }
  return null;
}

export function parsePayrollText(rawText) {
  const text = rawText.replace(/[|¦]/g, '').replace(/\r/g, '').replace(/[ \t]+/g, ' ');
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
  const result = {};

  result._rawTextPreview = lines.slice(0, 40).join('\n');

  // Salario Base
  const sb = findAmount(lines, ['salario\\s*base', 'sueldo\\s*base', 'sal\\.?\\s*base', 's[.,]\\s*base', 'retrib.*base'], 200);
  if (sb) result.salarioBase = String(sb);

  // Plus Convenio
  const pc = findAmount(lines, ['plus\\s*conv', 'compl.*conv', 'plus\\s*puesto', 'compl.*puesto', 'mejora\\s*vol', 'plus\\s*activ', 'plus\\s*product'], 10);
  if (pc) result.plusConvenio = String(pc);

  // Antigüedad
  const ant = findAmount(lines, ['antig', 'trienio', 'quinquenio', 'bienio'], 5);
  if (ant) result.valorAntiguedad = String(ant);

  // Nocturnidad
  const noc = findAmount(lines, ['nocturn', 'plus.*noche', 'turno.*noche', 'nocturno'], 5);
  if (noc) result.valorNocturnidad = String(noc);

  // Horas nocturnas
  const hn = findAmount(lines, ['horas?.*noct', 'h\\.?.*nocturna'], 1);
  if (hn && hn < 200) result.horasNocturnas = String(hn);

  // Dietas
  const di = findAmount(lines, ['dietas?\\b', 'plus.*transp', 'locomoci', 'kilometraje', 'manutenci', 'quebranto'], 5);
  if (di) result.dietas = String(di);

  // Pagas
  const pm = text.match(/(\d{2})\s*pagas/i);
  if (pm) { const p = parseInt(pm[1]); if ([12, 14, 15].includes(p)) result.pagas = String(p); }

  // Prorrateo
  if (/prorrat/i.test(text)) result.prorrateo = true;

  // Convenio auto-detect
  const lo = text.toLowerCase();
  if (/mercadona/i.test(lo))                    result.convenio = 'mercadona';
  else if (/leroy\s*merlin/i.test(lo))          result.convenio = 'leroy_merlin';
  else if (/transporte\s*sanitario/i.test(lo))  result.convenio = 'transporte_sanitario_andalucia';
  else if (/ambulanci/i.test(lo))               result.convenio = 'transporte_sanitario_andalucia';
  else if (/hosteler/i.test(lo))                result.convenio = 'hosteleria';
  else if (/comercio/i.test(lo))                result.convenio = 'comercio';
  else if (/construcci/i.test(lo))              result.convenio = 'construccion';

  return result;
}
