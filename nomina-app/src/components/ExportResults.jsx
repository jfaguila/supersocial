import React from 'react';
import { motion } from 'framer-motion';

const ExportResults = ({ results, fileName = 'nomina-analisis' }) => {
  const exportToJSON = () => {
    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `${fileName}-${new Date().toISOString().split('T')[0]}.json`;
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const exportToCSV = () => {
    let csvContent = "Concepto,Tu Nomina (EUR),Deberia Ser (EUR),Diferencia (EUR),Estado\n";

    if (results.details) {
      if (results.details.salario_base_comparativa) {
        const sb = results.details.salario_base_comparativa;
        csvContent += `Salario Base,${sb.real || 0},${sb.teorico || 0},${sb.diferencia || 0},${sb.estado}\n`;
      }
      if (results.details.plus_convenio) {
        const pc = results.details.plus_convenio;
        csvContent += `Plus Convenio,${pc.real || 0},${pc.teorico || 0},${pc.diferencia || 0},${pc.estado}\n`;
      }
      if (results.details.antiguedad) {
        const ant = results.details.antiguedad;
        csvContent += `Antiguedad,${ant.real || 0},${ant.teorico || 0},${ant.diferencia || 0},${ant.estado}\n`;
      }
      if (results.details.nocturnidad) {
        const noc = results.details.nocturnidad;
        csvContent += `Nocturnidad,${noc.real || 0},${noc.teorico || 0},${noc.diferencia || 0},${noc.estado}\n`;
      }
    }

    csvContent += `\nResumen\n`;
    csvContent += `Estado General,${results.isValid ? 'VALIDO' : 'CON ERRORES'},,,\n`;
    csvContent += `Convenio Aplicado,${results.convenioAplicado || 'N/A'},,,\n`;
    csvContent += `Errores,${results.errors ? results.errors.length : 0},,,\n`;
    csvContent += `Advertencias,${results.warnings ? results.warnings.length : 0},,,\n`;

    if (results.errors && results.errors.length > 0) {
      csvContent += `\nErrores Detectados\n`;
      results.errors.forEach((error, index) => {
        csvContent += `Error ${index + 1},"${error}",,,\n`;
      });
    }

    if (results.warnings && results.warnings.length > 0) {
      csvContent += `\nAdvertencias\n`;
      results.warnings.forEach((warning, index) => {
        csvContent += `Advertencia ${index + 1},"${warning}",,,\n`;
      });
    }

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `${fileName}-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToPDF = () => {
    const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2563eb; margin-bottom: 10px; }
            .status { padding: 15px; border-radius: 8px; margin: 20px 0; }
            .valid { background: #10b981; color: white; }
            .invalid { background: #ef4444; color: white; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background: #f3f4f6; font-weight: bold; }
            .error { color: #ef4444; }
            .warning { color: #f59e0b; }
            .footer { margin-top: 40px; font-size: 12px; color: #666; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Analisis de Nomina</h1>
            <p>Fecha: ${new Date().toLocaleDateString('es-ES')}</p>
            <p>Convenio: ${results.convenioAplicado || 'No especificado'}</p>
        </div>

        <div class="status ${results.isValid ? 'valid' : 'invalid'}">
            <h2>${results.isValid ? 'Nomina Correcta' : 'Nomina con Errores'}</h2>
            <p>${results.isValid ? 'Tu nomina cumple con el convenio aplicable' : 'Se han detectado inconsistencias'}</p>
        </div>

        <h3>Comparativa Detallada</h3>
        <table>
            <thead>
                <tr>
                    <th>Concepto</th>
                    <th>Tu Nomina (EUR)</th>
                    <th>Deberia Ser (EUR)</th>
                    <th>Diferencia (EUR)</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
                ${results.details && results.details.salario_base_comparativa ? `
                <tr>
                    <td>Salario Base</td>
                    <td>${(results.details.salario_base_comparativa.real || 0).toFixed(2)}</td>
                    <td>${(results.details.salario_base_comparativa.teorico || 0).toFixed(2)}</td>
                    <td>${(results.details.salario_base_comparativa.diferencia || 0).toFixed(2)}</td>
                    <td>${results.details.salario_base_comparativa.estado}</td>
                </tr>` : ''}
                ${results.details && results.details.plus_convenio ? `
                <tr>
                    <td>Plus Convenio</td>
                    <td>${(results.details.plus_convenio.real || 0).toFixed(2)}</td>
                    <td>${(results.details.plus_convenio.teorico || 0).toFixed(2)}</td>
                    <td>${(results.details.plus_convenio.diferencia || 0).toFixed(2)}</td>
                    <td>${results.details.plus_convenio.estado}</td>
                </tr>` : ''}
                ${results.details && results.details.antiguedad ? `
                <tr>
                    <td>Antiguedad</td>
                    <td>${(results.details.antiguedad.real || 0).toFixed(2)}</td>
                    <td>${(results.details.antiguedad.teorico || 0).toFixed(2)}</td>
                    <td>${(results.details.antiguedad.diferencia || 0).toFixed(2)}</td>
                    <td>${results.details.antiguedad.estado}</td>
                </tr>` : ''}
            </tbody>
        </table>

        ${results.errors && results.errors.length > 0 ? `
        <h3>Errores Detectados</h3>
        <ul class="error">
            ${results.errors.map(error => `<li>${error}</li>`).join('')}
        </ul>` : ''}

        ${results.warnings && results.warnings.length > 0 ? `
        <h3>Advertencias</h3>
        <ul class="warning">
            ${results.warnings.map(warning => `<li>${warning}</li>`).join('')}
        </ul>` : ''}

        <div class="footer">
            <p>Reporte generado por NominIA - Verificador de Nominas</p>
            <p>Este reporte es informativo y no constituye asesoramiento legal</p>
        </div>
    </body>
    </html>`;

    const newWindow = window.open('', '_blank');
    newWindow.document.write(htmlContent);
    newWindow.document.close();
    newWindow.print();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-card p-6"
    >
      <h3 className="text-2xl font-bold gradient-text mb-6 text-center">
        Exportar Resultados
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={exportToJSON}
          className="bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold px-6 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <span>Exportar JSON</span>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={exportToCSV}
          className="bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold px-6 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span>Exportar CSV</span>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={exportToPDF}
          className="bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold px-6 py-4 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
          </svg>
          <span>Exportar PDF</span>
        </motion.button>
      </div>

      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
        <div className="flex items-start space-x-2">
          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="text-left">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-300">Formatos de exportacion</p>
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
              JSON para datos estructurados, CSV para Excel, PDF para informes impresos
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default ExportResults;
