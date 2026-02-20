/**
 * Client-side payroll verification engine.
 * Compares user-provided payroll data against official Spanish convention tables.
 */

// Salario Minimo Interprofesional 2024
const SMI_MENSUAL = 1134.00;
// eslint-disable-next-line no-unused-vars
const SMI_ANUAL = 15876.00;

// Convention salary tables (monthly base salary by convention + category)
const CONVENTION_TABLES = {
  general: {
    empleado: { salarioBase: 1134.00, plusConvenio: 0, nocturnidadPct: 0.25 },
    tecnico: { salarioBase: 1350.00, plusConvenio: 80, nocturnidadPct: 0.25 },
    mando_intermedio: { salarioBase: 1600.00, plusConvenio: 120, nocturnidadPct: 0.25 },
    directivo: { salarioBase: 2200.00, plusConvenio: 200, nocturnidadPct: 0.25 },
  },
  hosteleria: {
    empleado: { salarioBase: 1200.00, plusConvenio: 50, nocturnidadPct: 0.25 },
    tecnico: { salarioBase: 1400.00, plusConvenio: 100, nocturnidadPct: 0.25 },
    mando_intermedio: { salarioBase: 1650.00, plusConvenio: 150, nocturnidadPct: 0.25 },
    directivo: { salarioBase: 2300.00, plusConvenio: 250, nocturnidadPct: 0.25 },
  },
  comercio: {
    empleado: { salarioBase: 1180.00, plusConvenio: 40, nocturnidadPct: 0.25 },
    tecnico: { salarioBase: 1380.00, plusConvenio: 90, nocturnidadPct: 0.25 },
    mando_intermedio: { salarioBase: 1620.00, plusConvenio: 130, nocturnidadPct: 0.25 },
    directivo: { salarioBase: 2250.00, plusConvenio: 220, nocturnidadPct: 0.25 },
  },
  construccion: {
    empleado: { salarioBase: 1250.00, plusConvenio: 60, nocturnidadPct: 0.25 },
    tecnico: { salarioBase: 1450.00, plusConvenio: 110, nocturnidadPct: 0.25 },
    mando_intermedio: { salarioBase: 1700.00, plusConvenio: 160, nocturnidadPct: 0.25 },
    directivo: { salarioBase: 2400.00, plusConvenio: 280, nocturnidadPct: 0.25 },
  },
  transporte_sanitario_andalucia: {
    tes_conductor: { salarioBase: 1350.00, plusConvenio: 180, nocturnidadPct: 0.30 },
    tes_ayudante_camillero: { salarioBase: 1200.00, plusConvenio: 150, nocturnidadPct: 0.30 },
    tes_camillero: { salarioBase: 1150.00, plusConvenio: 130, nocturnidadPct: 0.30 },
  },
  mercadona: {
    personal_base: { salarioBase: 1507.00, plusConvenio: 0, nocturnidadPct: 0.25 },
    gerente_a: { salarioBase: 1650.00, plusConvenio: 100, nocturnidadPct: 0.25 },
    gerente_b: { salarioBase: 1800.00, plusConvenio: 150, nocturnidadPct: 0.25 },
    gerente_c: { salarioBase: 2000.00, plusConvenio: 200, nocturnidadPct: 0.25 },
    coordinador: { salarioBase: 2200.00, plusConvenio: 250, nocturnidadPct: 0.25 },
  },
  leroy_merlin: {
    profesional: { salarioBase: 1400.00, plusConvenio: 60, nocturnidadPct: 0.25 },
    coordinador: { salarioBase: 1700.00, plusConvenio: 120, nocturnidadPct: 0.25 },
    tecnico: { salarioBase: 1550.00, plusConvenio: 90, nocturnidadPct: 0.25 },
  },
};

// Seniority bonus: percentage per triennium (3-year period)
const SENIORITY_RATES = {
  general: 0.03,       // 3% per triennium
  hosteleria: 0.03,
  comercio: 0.025,     // 2.5% per triennium
  construccion: 0.04,  // 4% per triennium
  transporte_sanitario_andalucia: 0.05, // 5% per triennium
  mercadona: 0.02,     // 2% per triennium
  leroy_merlin: 0.025,
};

const safeNum = (val) => {
  if (val === null || val === undefined || val === '') return 0;
  const parsed = parseFloat(val);
  return isNaN(parsed) ? 0 : parsed;
};

const TOLERANCE = 5.0; // EUR tolerance for "correct" comparisons

/**
 * Validates payroll data against convention tables.
 * Returns a results object with isValid, errors, warnings, details, and comparativa.
 */
export function validatePayroll(data) {
  const convenio = data.convenio || 'general';
  const categoria = data.categoria || 'empleado';
  const salarioBase = safeNum(data.salarioBase);
  const plusConvenio = safeNum(data.plusConvenio);
  const valorAntiguedad = safeNum(data.valorAntiguedad);
  const horasNocturnas = safeNum(data.horasNocturnas);
  const valorNocturnidad = safeNum(data.valorNocturnidad);
  const dietas = safeNum(data.dietas);
  const pagas = parseInt(data.pagas) || 14;
  const prorrateo = data.prorrateo || false;

  const convTable = CONVENTION_TABLES[convenio];
  if (!convTable) {
    return {
      isValid: false,
      errors: [`Convenio "${convenio}" no reconocido.`],
      warnings: [],
      details: {},
      comparativa: false,
      convenioAplicado: convenio
    };
  }

  const catTable = convTable[categoria];
  if (!catTable) {
    return {
      isValid: false,
      errors: [`Categoria "${categoria}" no encontrada en el convenio "${convenio}".`],
      warnings: [],
      details: {},
      comparativa: false,
      convenioAplicado: convenio
    };
  }

  const errors = [];
  const warnings = [];
  const details = {};

  // 1. Salario Base comparison
  const teoricoSalBase = catTable.salarioBase;
  const diffSalBase = salarioBase - teoricoSalBase;
  const salBaseEstado = salarioBase >= (teoricoSalBase - TOLERANCE) ? 'CORRECTO' : 'REVISAR';

  details.salario_base_comparativa = {
    real: salarioBase,
    teorico: teoricoSalBase,
    diferencia: diffSalBase,
    estado: salBaseEstado,
    mensaje: salBaseEstado === 'CORRECTO'
      ? `Tu salario base cumple con el minimo del convenio (${teoricoSalBase.toFixed(2)} EUR/mes).`
      : `Tu salario base (${salarioBase.toFixed(2)} EUR) esta por debajo del minimo del convenio (${teoricoSalBase.toFixed(2)} EUR). Diferencia: ${Math.abs(diffSalBase).toFixed(2)} EUR.`
  };

  if (salBaseEstado === 'REVISAR') {
    errors.push(`Salario Base inferior al minimo del convenio: ${salarioBase.toFixed(2)} EUR vs ${teoricoSalBase.toFixed(2)} EUR (diferencia de ${Math.abs(diffSalBase).toFixed(2)} EUR).`);
  }

  // Check against SMI
  if (salarioBase > 0 && salarioBase < SMI_MENSUAL) {
    errors.push(`Salario Base (${salarioBase.toFixed(2)} EUR) por debajo del SMI (${SMI_MENSUAL.toFixed(2)} EUR/mes).`);
  }

  // 2. Plus Convenio comparison
  const teoricoPlusConv = catTable.plusConvenio;
  if (teoricoPlusConv > 0 || plusConvenio > 0) {
    const diffPlus = plusConvenio - teoricoPlusConv;
    const plusEstado = plusConvenio >= (teoricoPlusConv - TOLERANCE) ? 'CORRECTO' : 'REVISAR';

    details.plus_convenio = {
      real: plusConvenio,
      teorico: teoricoPlusConv,
      diferencia: diffPlus,
      estado: plusEstado,
      mensaje: plusEstado === 'CORRECTO'
        ? `El plus de convenio cumple con el minimo establecido (${teoricoPlusConv.toFixed(2)} EUR).`
        : `El plus de convenio (${plusConvenio.toFixed(2)} EUR) esta por debajo del minimo (${teoricoPlusConv.toFixed(2)} EUR).`
    };

    if (plusEstado === 'REVISAR') {
      errors.push(`Plus Convenio inferior al establecido: ${plusConvenio.toFixed(2)} EUR vs ${teoricoPlusConv.toFixed(2)} EUR.`);
    }
  }

  // 3. Seniority (Antiguedad) validation
  if (valorAntiguedad > 0 || data.antiguedad) {
    const seniorityRate = SENIORITY_RATES[convenio] || 0.03;
    // Estimate: if user provided a start date, calculate triennia
    let triennia = 0;
    if (data.antiguedad) {
      const startDate = new Date(data.antiguedad);
      if (!isNaN(startDate.getTime())) {
        const now = new Date();
        const yearsWorked = (now - startDate) / (365.25 * 24 * 60 * 60 * 1000);
        triennia = Math.floor(yearsWorked / 3);
      }
    }

    const teoricoAntiguedad = triennia > 0 ? teoricoSalBase * seniorityRate * triennia : valorAntiguedad;
    const diffAntiguedad = valorAntiguedad - teoricoAntiguedad;
    const antEstado = (triennia === 0 || valorAntiguedad >= (teoricoAntiguedad - TOLERANCE)) ? 'CORRECTO' : 'REVISAR';

    details.antiguedad = {
      real: valorAntiguedad,
      teorico: teoricoAntiguedad,
      diferencia: diffAntiguedad,
      estado: antEstado,
      detalle_calculo: triennia > 0 ? `${triennia} trienio(s) x ${(seniorityRate * 100).toFixed(1)}% = ${(seniorityRate * triennia * 100).toFixed(1)}% del salario base` : null,
      mensaje: antEstado === 'CORRECTO'
        ? 'El complemento de antiguedad es correcto.'
        : `El complemento de antiguedad (${valorAntiguedad.toFixed(2)} EUR) no corresponde con el calculo teorico (${teoricoAntiguedad.toFixed(2)} EUR).`
    };

    if (antEstado === 'REVISAR') {
      warnings.push(`Antiguedad: se esperaba ${teoricoAntiguedad.toFixed(2)} EUR pero se detecto ${valorAntiguedad.toFixed(2)} EUR.`);
    }
  }

  // 4. Nocturnidad validation
  if (horasNocturnas > 0 || valorNocturnidad > 0) {
    const noctPct = catTable.nocturnidadPct || 0.25;
    // Hourly rate = monthly salary / 160 (standard hours)
    const hourlyRate = teoricoSalBase / 160;
    const teoricoNocturnidad = horasNocturnas * hourlyRate * noctPct;
    const diffNoct = valorNocturnidad - teoricoNocturnidad;
    const noctEstado = horasNocturnas === 0 || valorNocturnidad >= (teoricoNocturnidad - TOLERANCE) ? 'CORRECTO' : 'REVISAR';

    details.nocturnidad = {
      real: valorNocturnidad,
      teorico: teoricoNocturnidad,
      diferencia: diffNoct,
      horas: horasNocturnas,
      estado: noctEstado,
      detalle_calculo: `${horasNocturnas}h x ${hourlyRate.toFixed(2)} EUR/h x ${(noctPct * 100)}% = ${teoricoNocturnidad.toFixed(2)} EUR`,
      mensaje: noctEstado === 'CORRECTO'
        ? 'El plus de nocturnidad es correcto.'
        : `El plus de nocturnidad (${valorNocturnidad.toFixed(2)} EUR) no corresponde con el calculo teorico (${teoricoNocturnidad.toFixed(2)} EUR).`
    };

    if (noctEstado === 'REVISAR') {
      warnings.push(`Nocturnidad: se esperaba ${teoricoNocturnidad.toFixed(2)} EUR pero se detecto ${valorNocturnidad.toFixed(2)} EUR.`);
    }
  }

  // 5. Dietas
  if (dietas > 0) {
    details.dietas = {
      real: dietas,
      teorico: dietas, // Allowances don't have a fixed convention amount
      diferencia: 0,
      estado: 'CORRECTO',
      mensaje: `Dietas registradas: ${dietas.toFixed(2)} EUR. Las dietas dependen del acuerdo individual.`
    };
  }

  // 6. Prorrateo check
  if (prorrateo && pagas > 12) {
    const extraPayments = pagas - 12;
    const prorrateoAmount = (teoricoSalBase * extraPayments) / 12;
    warnings.push(`Prorrateo activado: ${extraPayments} pagas extra prorrateadas (+${prorrateoAmount.toFixed(2)} EUR/mes estimado).`);
  }

  // 7. Calculate total accrued
  const totalDevengadoReal = salarioBase + plusConvenio + valorAntiguedad + valorNocturnidad + dietas;
  const totalDevengadoTeorico = teoricoSalBase + (catTable.plusConvenio || 0) +
    (details.antiguedad?.teorico || 0) +
    (details.nocturnidad?.teorico || 0) +
    dietas;

  details.calculos_finales = {
    total_devengado: totalDevengadoReal,
    total_teorico: totalDevengadoTeorico,
    diferencia_total: totalDevengadoReal - totalDevengadoTeorico
  };

  const isValid = errors.length === 0;

  return {
    isValid,
    errors,
    warnings,
    details,
    comparativa: true,
    convenioAplicado: convenio,
    categoriaAplicada: categoria
  };
}

/**
 * Demo payroll examples for testing without a real file.
 */
export const DEMO_EXAMPLES = {
  correct: {
    convenio: 'general',
    categoria: 'tecnico',
    salarioBase: 1400,
    plusConvenio: 100,
    valorAntiguedad: 40,
    horasNocturnas: 0,
    valorNocturnidad: 0,
    dietas: 0,
    pagas: '14',
    prorrateo: false
  },
  withErrors: {
    convenio: 'mercadona',
    categoria: 'personal_base',
    salarioBase: 1100, // Below Mercadona minimum
    plusConvenio: 0,
    valorAntiguedad: 0,
    horasNocturnas: 10,
    valorNocturnidad: 15, // Too low
    dietas: 50,
    pagas: '14',
    prorrateo: false
  },
  withWarnings: {
    convenio: 'transporte_sanitario_andalucia',
    categoria: 'tes_conductor',
    salarioBase: 1360,
    plusConvenio: 180,
    valorAntiguedad: 30, // May not match triennium calc
    horasNocturnas: 20,
    valorNocturnidad: 45, // Slightly low
    dietas: 120,
    pagas: '14',
    prorrateo: true
  }
};
