/**
 * PDF text extraction and Spanish payroll (nómina) data parser.
 * Uses pdf.js to read PDFs client-side and regex to extract salary concepts.
 */
import * as pdfjsLib from 'pdfjs-dist';

// Use the bundled worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

/**
 * Extract all text content from a PDF file.
 * @param {File} file - PDF file object from input/dropzone
 * @returns {Promise<string>} - Full text content of the PDF
 */
export async function extractTextFromPDF(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  let fullText = '';
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const pageText = content.items.map((item) => item.str).join(' ');
    fullText += pageText + '\n';
  }
  return fullText;
}

/**
 * Parse a Spanish number string: "1.350,50" → 1350.50
 */
function parseSpanishNumber(str) {
  if (!str) return null;
  let clean = str.trim();
  // Remove currency symbols and spaces
  clean = clean.replace(/[€EUR\s]/gi, '').trim();
  if (clean.includes(',') && clean.includes('.')) {
    clean = clean.replace(/\./g, '').replace(',', '.');
  } else if (clean.includes(',')) {
    clean = clean.replace(',', '.');
  }
  const num = parseFloat(clean);
  return isNaN(num) ? null : num;
}

/**
 * Try to find a number near a keyword in the text.
 * Searches for patterns like "Salario Base  1.350,50" or "Salario Base: 1350.50"
 */
function findAmountNear(text, patterns) {
  for (const pattern of patterns) {
    // Match: keyword followed by optional separators then a number (Spanish or standard format)
    const regex = new RegExp(
      pattern + '[:\\s.,;|]*([\\d]{1,2}[.,])?\\s{0,5}([\\d]+[.,]?[\\d]*[.,]?[\\d]+)',
      'i'
    );
    const match = text.match(regex);
    if (match) {
      // Take the last capturing group that looks like a full number
      const raw = match[0].replace(new RegExp(pattern, 'i'), '').trim();
      // Extract all number-like sequences from the remaining text
      const numbers = raw.match(/[\d]+[.,]?[\d]*[.,]?[\d]*/g);
      if (numbers) {
        for (const numStr of numbers) {
          const val = parseSpanishNumber(numStr);
          if (val !== null && val > 0) return val;
        }
      }
    }
  }
  return null;
}

/**
 * Parse payroll data from extracted PDF text.
 * @param {string} text - Raw text from PDF
 * @returns {object} - Extracted payroll fields
 */
export function parsePayrollText(text) {
  // Normalize whitespace but keep structure
  const normalized = text.replace(/\s+/g, ' ');

  const result = {};

  // --- Salario Base ---
  const salarioBase = findAmountNear(normalized, [
    'salario\\s*base',
    'sueldo\\s*base',
    'sal\\.?\\s*base',
    'retribuci[oó]n\\s*base',
  ]);
  if (salarioBase) result.salarioBase = String(salarioBase);

  // --- Plus Convenio ---
  const plusConvenio = findAmountNear(normalized, [
    'plus\\s*convenio',
    'complemento\\s*convenio',
    'plus\\s*conv\\.?',
    'mejora\\s*voluntaria',
    'complemento\\s*puesto',
  ]);
  if (plusConvenio) result.plusConvenio = String(plusConvenio);

  // --- Antigüedad ---
  const antiguedad = findAmountNear(normalized, [
    'antig[uü]edad',
    'trienio',
    'complemento\\s*antig',
    'plus\\s*antig',
  ]);
  if (antiguedad) result.valorAntiguedad = String(antiguedad);

  // --- Nocturnidad ---
  const nocturnidad = findAmountNear(normalized, [
    'nocturnidad',
    'plus\\s*noct',
    'complemento\\s*noct',
    'turno\\s*noche',
  ]);
  if (nocturnidad) result.valorNocturnidad = String(nocturnidad);

  // --- Horas nocturnas (number, not amount) ---
  const horasNoct = findAmountNear(normalized, [
    'horas\\s*noct',
    'h\\.?\\s*noct',
    'hrs?\\.?\\s*noct',
  ]);
  if (horasNoct) result.horasNocturnas = String(horasNoct);

  // --- Dietas ---
  const dietas = findAmountNear(normalized, [
    'dietas?',
    'plus\\s*transporte',
    'locomoci[oó]n',
    'kilometraje',
    'manutenci[oó]n',
  ]);
  if (dietas) result.dietas = String(dietas);

  // --- Pagas (12, 14, 15) ---
  const pagasMatch = normalized.match(/(\d{2})\s*pagas/i);
  if (pagasMatch) {
    const p = parseInt(pagasMatch[1]);
    if ([12, 14, 15].includes(p)) result.pagas = String(p);
  }

  // --- Prorrateo ---
  if (/prorrat/i.test(normalized)) {
    result.prorrateo = true;
  }

  // --- Try to detect convenio from text ---
  const textLower = normalized.toLowerCase();
  if (/mercadona/i.test(textLower)) {
    result.convenio = 'mercadona';
  } else if (/leroy\s*merlin/i.test(textLower)) {
    result.convenio = 'leroy_merlin';
  } else if (/transporte\s*sanitario/i.test(textLower)) {
    result.convenio = 'transporte_sanitario_andalucia';
  } else if (/hosteler[ií]a/i.test(textLower)) {
    result.convenio = 'hosteleria';
  } else if (/comercio/i.test(textLower)) {
    result.convenio = 'comercio';
  } else if (/construcci[oó]n/i.test(textLower)) {
    result.convenio = 'construccion';
  }

  return result;
}
