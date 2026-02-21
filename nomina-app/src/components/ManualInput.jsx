import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { DEFAULT_CATEGORIES, CONVENTION_CATEGORY_KEYS } from '../utils/payrollEngine';

const ManualInput = ({ onSubmit, onBack, initialData = null, disabled = false }) => {
  const [validationError, setValidationError] = useState('');
  const [formData, setFormData] = useState({
    horasExtras: '',
    dietas: '',
    salarioBase: '',
    plusConvenio: '',
    valorAntiguedad: '',
    valorNocturnidad: '',
    horasNocturnas: '',
    antiguedad: '',
    pagas: '14',
    prorrateo: false,
    categoria: 'empleado',
    convenio: 'general'
  });

  useEffect(() => {
    if (initialData) {
      setFormData(prev => ({
        ...prev,
        ...initialData
      }));
    }
  }, [initialData]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    if (name === 'convenio') {
      // Reset category to a valid default when convenio changes
      const validCats = CONVENTION_CATEGORY_KEYS[value] || [];
      const currentCat = formData.categoria;
      const newCat = validCats.includes(currentCat) ? currentCat : (DEFAULT_CATEGORIES[value] || validCats[0] || 'empleado');
      setFormData(prev => ({
        ...prev,
        convenio: value,
        categoria: newCat
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value
      }));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const salVal = String(formData.salarioBase).trim();
    if (!salVal) {
      setValidationError('Debes introducir al menos el Salario Base para poder verificar la nomina.');
      return;
    }
    setValidationError('');
    onSubmit(formData);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <form onSubmit={handleSubmit} className="space-y-10">
        {validationError && (
          <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 font-medium flex items-center gap-3">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {validationError}
          </div>
        )}
        {/* 1. Contexto Laboral */}
        <section className="space-y-6 bg-gray-50/50 dark:bg-gray-800/20 p-6 rounded-3xl border border-gray-100 dark:border-gray-800/50">
          <h4 className="text-sm font-bold text-blue-600 dark:text-blue-400 uppercase tracking-widest flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
            Contexto Laboral
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Convenio</label>
              <select
                name="convenio"
                value={formData.convenio}
                onChange={handleChange}
                className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
              >
                <option value="general">Convenio General</option>
                <option value="hosteleria">Hosteleria</option>
                <option value="comercio">Comercio</option>
                <option value="construccion">Construccion</option>
                <option value="transporte_sanitario_andalucia">Transporte Sanitario Andalucia</option>
                <option value="mercadona">Mercadona (2024-2028)</option>
                <option value="leroy_merlin">Leroy Merlin (Grandes Almacenes)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Categoria</label>
              <select
                name="categoria"
                value={formData.categoria}
                onChange={handleChange}
                className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-sm font-medium focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
              >
                {formData.convenio === 'transporte_sanitario_andalucia' ? (
                  <>
                    <option value="tes_conductor">TES Conductor</option>
                    <option value="tes_ayudante_camillero">TES Ayudante Camillero</option>
                    <option value="tes_camillero">TES Camillero</option>
                  </>
                ) : formData.convenio === 'mercadona' ? (
                  <>
                    <option value="personal_base">Personal Base</option>
                    <option value="gerente_a">Gerente A (0-2 anhos)</option>
                    <option value="gerente_b">Gerente B (2-4 anhos)</option>
                    <option value="gerente_c">Gerente C (4+ anhos)</option>
                    <option value="coordinador">Coordinador</option>
                  </>
                ) : formData.convenio === 'leroy_merlin' ? (
                  <>
                    <option value="profesional">Profesional</option>
                    <option value="coordinador">Coordinador</option>
                    <option value="tecnico">Tecnico</option>
                  </>
                ) : (
                  <>
                    <option value="empleado">Empleado Base</option>
                    <option value="tecnico">Tecnico/a</option>
                    <option value="mando_intermedio">Mando Intermedio</option>
                    <option value="directivo">Directivo/a</option>
                  </>
                )}
              </select>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-10">
          {/* 2. Conceptos Salariales */}
          <div className="space-y-6">
            <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100 dark:border-gray-800 pb-2 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              Conceptos Fijos
            </h4>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Salario Base Mensual (EUR) <span className="text-red-500">*</span></label>
                <input
                  type="text"
                  inputMode="decimal"
                  name="salarioBase"
                  value={formData.salarioBase}
                  onChange={(e) => { setValidationError(''); handleChange(e); }}
                  placeholder="Ej: 1.350,50"
                  className={`w-full bg-white dark:bg-gray-800 border rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm ${validationError && !String(formData.salarioBase).trim() ? 'border-red-400 dark:border-red-600 ring-2 ring-red-200 dark:ring-red-800' : 'border-gray-200 dark:border-gray-700'}`}
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Plus Convenio / Extras (EUR)</label>
                <input
                  type="text"
                  inputMode="decimal"
                  name="plusConvenio"
                  value={formData.plusConvenio}
                  onChange={handleChange}
                  placeholder="Ej: 80,00"
                  className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Plus Antiguedad (EUR)</label>
                <input
                  type="text"
                  inputMode="decimal"
                  name="valorAntiguedad"
                  value={formData.valorAntiguedad}
                  onChange={handleChange}
                  placeholder="Ej: 40,50"
                  className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
                />
              </div>
            </div>
          </div>

          {/* 3. Variables y Extras */}
          <div className="space-y-6">
            <h4 className="text-sm font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100 dark:border-gray-800 pb-2 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" /></svg>
              Variables y Otros
            </h4>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Horas Noct.</label>
                <input
                  type="text"
                  inputMode="numeric"
                  name="horasNocturnas"
                  value={formData.horasNocturnas}
                  onChange={handleChange}
                  placeholder="0"
                  className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Tot. Noct. (EUR)</label>
                <input
                  type="text"
                  inputMode="decimal"
                  name="valorNocturnidad"
                  value={formData.valorNocturnidad}
                  onChange={handleChange}
                  placeholder="Ej: 35,45"
                  className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 ml-1">Dietas y Complementos (EUR)</label>
              <input
                type="text"
                inputMode="decimal"
                name="dietas"
                value={formData.dietas}
                onChange={handleChange}
                placeholder="Ej: 120,00"
                className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 focus:ring-2 focus:ring-blue-500 outline-none transition-all shadow-sm"
              />
            </div>

            <div className="flex items-center gap-6 p-4 bg-blue-50/30 dark:bg-blue-900/10 rounded-2xl border border-blue-100/50 dark:border-blue-900/30">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="prorrateo"
                  name="prorrateo"
                  checked={formData.prorrateo}
                  onChange={handleChange}
                  className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                />
                <label htmlFor="prorrateo" className="text-sm font-bold text-gray-700 dark:text-gray-300 cursor-pointer">Prorrateo extras</label>
              </div>
              <div className="flex-1">
                <select
                  name="pagas"
                  value={formData.pagas}
                  onChange={handleChange}
                  className="w-full bg-transparent text-sm font-black text-blue-700 dark:text-blue-400 outline-none cursor-pointer"
                >
                  <option value="12">12 pagas</option>
                  <option value="14">14 pagas</option>
                  <option value="15">15 pagas</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-gray-100 dark:border-gray-800 flex flex-col md:flex-row gap-4">
          <button
            type="button"
            onClick={onBack}
            disabled={disabled}
            className="flex-1 py-4 px-6 rounded-2xl font-bold text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
            Subir otro archivo
          </button>
          <button
            type="submit"
            disabled={disabled}
            className="flex-[2] py-4 px-6 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg shadow-xl shadow-blue-500/20 transition-all flex items-center justify-center gap-3 active:scale-[0.98]"
          >
            <span>Verificar Nomina</span>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
        </div>
      </form>
    </motion.div>
  );
};

export default ManualInput;
