import React from 'react';
import { motion } from 'framer-motion';
import ExportResults from './ExportResults';
import { useLanguage } from '../i18n/LanguageProvider';

const ResultsDisplay = ({ results }) => {
  const { t } = useLanguage();

  if (!results) return null;

  const { isValid, errors, warnings, details } = results;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="space-y-6"
    >
      {/* Estado General */}
      <div
        className={`glass-card p-8 border-l-8 ${isValid ? 'border-green-500' : 'border-red-500'}`}
        role="alert"
        aria-live="polite"
      >
        <div className="flex items-center space-x-4">
          <div className={`w-16 h-16 rounded-full flex items-center justify-center ${isValid ? 'bg-gradient-to-br from-green-400 to-emerald-500' : 'bg-gradient-to-br from-red-400 to-rose-500'
            }`} aria-hidden="true">
            {isValid ? (
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            ) : (
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            )}
          </div>
          <div>
            <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
              {isValid ? t('validPayroll') : t('invalidPayroll')}
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              {isValid ? t('validMessage') : t('invalidMessage')}
            </p>
          </div>
        </div>
      </div>

      {/* Errores */}
      {errors && errors.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-card p-6 border-l-4 border-red-500"
        >
          <h3 className="text-xl font-bold text-red-700 dark:text-red-400 mb-4 flex items-center">
            <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {t('errorDetected')}
          </h3>
          <ul className="space-y-3">
            {errors.map((error, index) => (
              <li key={index} className="flex items-start space-x-3 bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                <span className="text-red-600 font-bold">&#8226;</span>
                <span className="text-red-800 dark:text-red-300">{error}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Advertencias */}
      {warnings && warnings.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-6 border-l-4 border-yellow-500"
        >
          <h3 className="text-xl font-bold text-yellow-700 dark:text-yellow-400 mb-4 flex items-center">
            <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {t('warnings')}
          </h3>
          <ul className="space-y-3">
            {warnings.map((warning, index) => (
              <li key={index} className="flex items-start space-x-3 bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                <span className="text-yellow-600 font-bold">&#8226;</span>
                <span className="text-yellow-800 dark:text-yellow-300">{warning}</span>
              </li>
            ))}
          </ul>
        </motion.div>
      )}

      {/* Tabla Comparativa Detallada */}
      {details && results.comparativa ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-6"
        >
          <h3 className="text-2xl font-bold gradient-text mb-6 text-center">
            {t('comparativeTitle')}
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b-2 border-gray-100 dark:border-gray-700">
                  <th className="py-3 px-4 font-bold text-gray-600 dark:text-gray-400">{t('concept')}</th>
                  <th className="py-3 px-4 font-bold text-gray-600 dark:text-gray-400 text-right">{t('real')}</th>
                  <th className="py-3 px-4 font-bold text-gray-600 dark:text-gray-400 text-right">{t('legal')}</th>
                  <th className="py-3 px-4 font-bold text-gray-600 dark:text-gray-400 text-center">{t('status')}</th>
                </tr>
              </thead>
              <tbody>
                {/* Salario Base */}
                {details.salario_base_comparativa && (
                  <tr className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                    <td className="py-3 px-4 font-medium text-gray-800 dark:text-gray-200">
                      Salario Base
                      <span className="block text-xs font-normal text-gray-500 dark:text-gray-400 mt-1">
                        {details.salario_base_comparativa.mensaje}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.salario_base_comparativa.real?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.salario_base_comparativa.teorico?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${details.salario_base_comparativa.estado === 'CORRECTO' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {details.salario_base_comparativa.estado}
                      </span>
                    </td>
                  </tr>
                )}

                {/* Plus Convenio */}
                {details.plus_convenio && (
                  <tr className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                    <td className="py-3 px-4 font-medium text-gray-800 dark:text-gray-200">
                      Plus Convenio
                      <span className="block text-xs font-normal text-gray-500 dark:text-gray-400 mt-1">
                        {details.plus_convenio.mensaje}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.plus_convenio.real?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.plus_convenio.teorico?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${details.plus_convenio.estado === 'CORRECTO' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {details.plus_convenio.estado}
                      </span>
                    </td>
                  </tr>
                )}

                {/* Antiguedad */}
                {details.antiguedad && (
                  <tr className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                    <td className="py-3 px-4 font-medium text-gray-800 dark:text-gray-200">
                      Antiguedad
                      {details.antiguedad.detalle_calculo && (
                        <span className="block text-xs text-gray-400 font-normal">{details.antiguedad.detalle_calculo}</span>
                      )}
                      <span className="block text-xs font-normal text-gray-500 dark:text-gray-400 mt-1">
                        {details.antiguedad.mensaje}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.antiguedad.real?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.antiguedad.teorico?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${details.antiguedad.estado === 'CORRECTO' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {details.antiguedad.estado}
                      </span>
                    </td>
                  </tr>
                )}

                {/* Nocturnidad */}
                {details.nocturnidad && (
                  <tr className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                    <td className="py-3 px-4 font-medium text-gray-800 dark:text-gray-200">
                      Nocturnidad
                      {details.nocturnidad.detalle_calculo && (
                        <span className="block text-xs text-gray-400 font-normal">{details.nocturnidad.detalle_calculo}</span>
                      )}
                      <span className="block text-xs font-normal text-gray-500 dark:text-gray-400 mt-1">
                        {details.nocturnidad.mensaje}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.nocturnidad.real?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.nocturnidad.teorico?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${details.nocturnidad.estado === 'CORRECTO' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {details.nocturnidad.estado}
                      </span>
                    </td>
                  </tr>
                )}

                {/* Dietas */}
                {details.dietas && (
                  <tr className="border-b border-gray-50 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
                    <td className="py-3 px-4 font-medium text-gray-800 dark:text-gray-200">
                      Dietas
                      <span className="block text-xs font-normal text-gray-500 dark:text-gray-400 mt-1">
                        {details.dietas.mensaje}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.dietas.real?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-right text-gray-700 dark:text-gray-300">{details.dietas.teorico?.toFixed(2)} EUR</td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        {details.dietas.estado}
                      </span>
                    </td>
                  </tr>
                )}

                {/* Totales */}
                {details.calculos_finales && (
                  <tr className="border-t-2 border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 font-bold">
                    <td className="py-4 px-4 text-gray-900 dark:text-gray-100">
                      TOTAL DEVENGADO
                      {details.calculos_finales.diferencia_total !== 0 && (
                        <span className={`block text-xs font-normal mt-1 ${details.calculos_finales.diferencia_total >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          Diferencia: {details.calculos_finales.diferencia_total >= 0 ? '+' : ''}{details.calculos_finales.diferencia_total.toFixed(2)} EUR
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-right text-gray-900 dark:text-gray-100">{details.calculos_finales.total_devengado?.toFixed(2)} EUR</td>
                    <td className="py-4 px-4 text-right text-gray-900 dark:text-gray-100">{details.calculos_finales.total_teorico?.toFixed(2)} EUR</td>
                    <td className="py-4 px-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${details.calculos_finales.diferencia_total >= -5 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {details.calculos_finales.diferencia_total >= -5 ? 'CORRECTO' : 'REVISAR'}
                      </span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      ) : (
        details && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-6"
          >
            <h3 className="text-xl font-bold gradient-text mb-4">
              Detalles de la Verificacion
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(details).map(([key, value]) => (
                <div key={key} className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 p-4 rounded-xl">
                  <p className="text-sm text-gray-600 dark:text-gray-400 font-medium capitalize">
                    {key.replace(/_/g, ' ')}
                  </p>
                  <p className="text-lg font-bold text-gray-800 dark:text-gray-200 mt-1">
                    {typeof value === 'number' ? `${value.toFixed(2)} EUR` : JSON.stringify(value)}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>
        )
      )}

      {/* Export Options */}
      <ExportResults results={results} />
    </motion.div>
  );
};

export default ResultsDisplay;
