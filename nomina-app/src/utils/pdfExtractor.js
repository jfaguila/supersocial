/**
 * PDF text extraction and Spanish payroll (nómina) data parser.
 * Uses pdf.js to read PDFs client-side. Extracts text with position data
 * to reconstruct the table layout of a Spanish payslip.
 */
import * as pdfjsLib from 'pdfjs-dist';

// Worker setup: use CDN for reliability with CRA/webpack
pdfjsLib.GlobalWorkerOptions.workerSrc =
  `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`;

/**
 * Parse a Spanish number string: "1.507,00" → 1507.00
 */
function parseSpanishNumber(str) {
  if (!str) return null;
  let clean = str.trim();
  clean = clean.replace(/[€\s]/g, '');
  if (clean.includes(',') && clean.includes('.')) {
    clean = clean.replace(/\./g, '').replace(',', '.');
  } else if (clean.includes(',')) {
    clean = clean.replace(',', '.');
  }
  const num = parseFloat(clean);
  return isNaN(num) ? null : num;
}

/**
 * Extract text items with positions from a PDF, grouped into lines.
 * Returns an array of lines, each line is a string with all items on that y-position.
 */
export async function extractTextFromPDF(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const allItems = [];
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    for (const item of content.items) {
      if (item.str.trim()) {
        allItems.push({
          text: item.str.trim(),
          x: Math.round(item.transform[4]),
          y: Math.round(item.transform[5]),
        });
      }
    }
  }

  // Group by Y position (same row = within 3px tolerance)
  allItems.sort((a, b) => b.y - a.y || a.x - b.x); // top to bottom, left to right
  const lines = [];
  let currentLine = [];
  let currentY = allItems.length > 0 ? allItems[0].y : 0;

  for (const item of allItems) {
    if (Math.abs(item.y - currentY) > 3) {
      if (currentLine.length > 0) {
        currentLine.sort((a, b) => a.x - b.x);
        lines.push(currentLine.map((i) => i.text).join('  '));
      }
      currentLine = [item];
      currentY = item.y;
    } else {
      currentLine.push(item);
    }
  }
  if (currentLine.length > 0) {
    currentLine.sort((a, b) => a.x - b.x);
    lines.push(currentLine.map((i) => i.text).join('  '));
  }

  return lines.join('\n');
}

/**
 * Extract all Spanish-format numbers from a string.
 * Returns array of parsed floats.
 */
function extractNumbers(str) {
  // Match Spanish numbers: 1.507,00 or 1507,00 or 1507.00 or 30 or 30,00
  const matches = str.match(/\d[\d.]*,\d{2}|\d+\.\d{2}|\d+/g) || [];
  return matches
    .map(parseSpanishNumber)
    .filter((n) => n !== null && n >= 0);
}

/**
 * Find a salary amount near a keyword. Strategy:
 * - Find the line containing the keyword
 * - Extract all numbers from that line
 * - Return the largest number > minValue (salary amounts are bigger than day counts)
 */
function findSalaryAmount(lines, patterns, minValue = 50) {
  const text = lines.toLowerCase();
  for (const pattern of patterns) {
    const regex = new RegExp(pattern, 'im');
    const match = text.match(regex);
    if (match) {
      // Get the line containing this match
      const matchPos = match.index;
      // Find the line boundaries
      const lineStart = text.lastIndexOf('\n', matchPos) + 1;
      const lineEnd = text.indexOf('\n', matchPos);
      const line = text.substring(lineStart, lineEnd === -1 ? text.length : lineEnd);

      const numbers = extractNumbers(line);
      // Filter out small numbers (day counts like 30, 31) and pick the best salary amount
      const salaryNumbers = numbers.filter((n) => n >= minValue);
      if (salaryNumbers.length > 0) {
        // Return the first salary-sized number (typically the monthly amount)
        return salaryNumbers[0];
      }
      // If no number > minValue, try any number
      if (numbers.length > 0) {
        return numbers[numbers.length - 1]; // last number on the line
      }
    }
  }
  return null;
}

/**
 * Parse payroll data from extracted PDF text.
 */
export function parsePayrollText(text) {
  const result = {};

  // Debug: store raw text for troubleshooting
  result._rawTextPreview = text.substring(0, 500);

  // --- Salario Base ---
  const salarioBase = findSalaryAmount(text, [
    'salario\\s*base',
    'sueldo\\s*base',
    'sal\\.?\\s*base',
    'retrib.*base',
  ], 200);
  if (salarioBase) result.salarioBase = String(salarioBase);

  // --- Plus Convenio ---
  const plusConvenio = findSalaryAmount(text, [
    'plus\\s*convenio',
    'compl.*convenio',
    'plus\\s*conv',
    'mejora\\s*vol',
    'compl.*puesto',
    'plus\\s*puesto',
  ], 10);
  if (plusConvenio) result.plusConvenio = String(plusConvenio);

  // --- Antigüedad ---
  const antiguedad = findSalaryAmount(text, [
    'antig[uü]edad',
    'trienio',
    'compl.*antig',
    'plus.*antig',
    'quinquenio',
  ], 5);
  if (antiguedad) result.valorAntiguedad = String(antiguedad);

  // --- Nocturnidad ---
  const nocturnidad = findSalaryAmount(text, [
    'nocturnidad',
    'plus.*noct',
    'compl.*noct',
    'turno.*noche',
    'nocturno',
  ], 5);
  if (nocturnidad) result.valorNocturnidad = String(nocturnidad);

  // --- Horas nocturnas ---
  const horasNoct = findSalaryAmount(text, [
    'horas?.*noct',
    'h\\.?.*nocturnas',
  ], 1);
  if (horasNoct && horasNoct < 200) result.horasNocturnas = String(horasNoct);

  // --- Dietas ---
  const dietas = findSalaryAmount(text, [
    'dietas?[^s]',
    'plus.*transporte',
    'locomoci',
    'kilometraje',
    'manutenci',
    'quebranto.*moneda',
  ], 5);
  if (dietas) result.dietas = String(dietas);

  // --- Pagas ---
  const pagasMatch = text.match(/(\d{2})\s*pagas/i);
  if (pagasMatch) {
    const p = parseInt(pagasMatch[1]);
    if ([12, 14, 15].includes(p)) result.pagas = String(p);
  }

  // --- Prorrateo ---
  if (/prorrat/i.test(text)) {
    result.prorrateo = true;
  }

  // --- Detect convenio from text ---
  const textLower = text.toLowerCase();
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
