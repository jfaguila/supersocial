import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLanguage } from '../i18n/LanguageProvider';
import FileUpload from '../components/FileUpload';
import ManualInput from '../components/ManualInput';
import ResultsDisplay from '../components/ResultsDisplay';
import LoadingSpinner from '../components/LoadingSpinner';
import DarkModeToggle from '../components/DarkModeToggle';
import InstructionsModal from '../components/InstructionsModal';
import { validatePayroll, DEMO_EXAMPLES, DEFAULT_CATEGORIES, CONVENTION_CATEGORY_KEYS } from '../utils/payrollEngine';
import { extractTextFromPDF, extractTextFromImage, parsePayrollText } from '../utils/pdfExtractor';

const HomePage = () => {
  const { t } = useLanguage();
  const [selectedFile, setSelectedFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState('');
  const [loadingProgress, setLoadingProgress] = useState(null);
  const [announcement, setAnnouncement] = useState('');
  const [showInstructions, setShowInstructions] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  // State for the Wizard steps: 1 (Upload), 2 (Review), 3 (Results)
  const [step, setStep] = useState(1);
  const [reviewData, setReviewData] = useState(null);

  // Pre-analysis options
  const [uploadData, setUploadData] = useState({
    convenio: 'general',
    categoria: 'empleado'
  });

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setResults(null);
    setStep(1);
    setError(null);
    setAnnouncement(`Archivo ${file.name} seleccionado. Pulsa analizar para continuar.`);
  };

  // State for extraction info shown in Step 2
  const [extractionInfo, setExtractionInfo] = useState(null);

  // Step 1 -> Step 2 (manual fallback) or Step 3 (direct results)
  const handleAnalyze = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setError(null);
    setExtractionInfo(null);
    setLoadingMessage('Leyendo archivo...');
    setLoadingProgress(10);

    try {
      let rawText = '';
      const isPDF = selectedFile.type === 'application/pdf';
      const isImage = selectedFile.type.startsWith('image/');

      // ── Extract text from file ──
      let extractError = '';
      if (isPDF) {
        setLoadingMessage('Extrayendo texto del PDF...');
        setLoadingProgress(25);
        try {
          rawText = await extractTextFromPDF(selectedFile);
        } catch (err) {
          extractError = `Error leyendo PDF: ${err.message || err}`;
          console.error('PDF extraction error:', err);
        }
        setLoadingProgress(60);
      } else if (isImage) {
        setLoadingMessage('Leyendo imagen con OCR (puede tardar 10-20s)...');
        setLoadingProgress(15);
        try {
          rawText = await extractTextFromImage(selectedFile, (pct) => {
            setLoadingProgress(15 + Math.round(pct * 0.55));
          });
        } catch (err) {
          extractError = `Error OCR: ${err.message || err}`;
          console.error('OCR error:', err);
        }
        setLoadingProgress(70);
      }

      // ── Parse salary concepts ──
      let extracted = {};
      let rawPreview = '';

      if (rawText && rawText.trim().length > 0) {
        setLoadingMessage('Analizando conceptos salariales...');
        setLoadingProgress(80);
        extracted = parsePayrollText(rawText);
        rawPreview = extracted._rawTextPreview || rawText.substring(0, 500);
        delete extracted._rawTextPreview;
      }
      setLoadingProgress(90);

      // Merge: extracted data takes priority, then user's convenio selection
      const convenio = extracted.convenio || uploadData.convenio;
      const validCats = CONVENTION_CATEGORY_KEYS[convenio] || [];
      const categoria = validCats.includes(uploadData.categoria)
        ? uploadData.categoria
        : (DEFAULT_CATEGORIES[convenio] || validCats[0] || 'empleado');

      const finalData = {
        convenio,
        categoria,
        salarioBase: extracted.salarioBase || '',
        plusConvenio: extracted.plusConvenio || '',
        valorAntiguedad: extracted.valorAntiguedad || '',
        horasNocturnas: extracted.horasNocturnas || '',
        valorNocturnidad: extracted.valorNocturnidad || '',
        dietas: extracted.dietas || '',
        pagas: extracted.pagas || '14',
        prorrateo: extracted.prorrateo || false
      };

      const fieldsFound = ['salarioBase', 'plusConvenio', 'valorAntiguedad',
        'valorNocturnidad', 'dietas'].filter(k => extracted[k]).length;

      // ── Decision: if we found at least the salary, go DIRECT to results ──
      if (extracted.salarioBase) {
        setLoadingMessage('Comparando con el convenio...');
        setLoadingProgress(95);
        const validationResults = validatePayroll(finalData);
        setResults(validationResults);
        setLoadingProgress(100);

        setExtractionInfo({ fieldsFound, rawPreview, isImage, extractError });

        setTimeout(() => {
          setLoading(false);
          setLoadingProgress(null);
          setLoadingMessage('');
          setStep(3);
        }, 300);
      } else {
        // No salary found → fallback to manual form
        setReviewData(finalData);
        setExtractionInfo({
          fieldsFound,
          rawPreview: rawPreview || '(no se pudo extraer texto)',
          isImage,
          extractError,
        });
        setLoadingProgress(100);

        setTimeout(() => {
          setLoading(false);
          setLoadingProgress(null);
          setLoadingMessage('');
          setStep(2);
        }, 300);
      }

    } catch (err) {
      handleError(err);
    }
  };

  // Step 2 -> Step 3: Validate with client-side engine
  const handleConfirmAnalysis = async (finalData) => {
    setLoading(true);
    setError(null);
    setLoadingMessage(t('analyzing'));
    setLoadingProgress(50);

    try {
      // Simulate processing delay
      await new Promise(r => setTimeout(r, 1000));
      setLoadingProgress(80);

      // Run client-side validation
      const validationResults = validatePayroll(finalData);

      setResults(validationResults);
      setLoadingProgress(100);

      setTimeout(() => {
        setLoading(false);
        setLoadingProgress(null);
        setLoadingMessage('');
        setStep(3);
      }, 300);

    } catch (err) {
      handleError(err);
    }
  };

  // Demo mode handler
  const handleDemoSelect = async (demoType) => {
    setShowDemo(false);
    setLoading(true);
    setLoadingMessage(t('analyzing'));
    setLoadingProgress(0);

    const demoData = DEMO_EXAMPLES[demoType];

    // Simulate analysis
    setLoadingProgress(30);
    await new Promise(r => setTimeout(r, 600));
    setLoadingProgress(60);
    await new Promise(r => setTimeout(r, 500));
    setLoadingProgress(90);

    const validationResults = validatePayroll(demoData);
    setResults(validationResults);
    setLoadingProgress(100);

    setTimeout(() => {
      setLoading(false);
      setLoadingProgress(null);
      setLoadingMessage('');
      setStep(3);
    }, 300);
  };

  const handleError = (err) => {
    setReviewData(null);
    setResults(null);
    setError(err.message || t('errorMessages.processingError'));
    setLoading(false);
    setLoadingProgress(null);
    setLoadingMessage('');
    setStep(1);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-gray-950 transition-colors duration-500 font-sans text-gray-900 dark:text-gray-100 selection:bg-blue-100 dark:selection:bg-blue-900/40">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-blue-100/50 dark:bg-blue-900/10 rounded-full blur-3xl" />
        <div className="absolute top-1/2 -left-24 w-72 h-72 bg-indigo-100/40 dark:bg-indigo-900/10 rounded-full blur-3xl" />
      </div>

      <InstructionsModal isOpen={showInstructions} onClose={() => setShowInstructions(false)} />

      <div className="relative max-w-6xl mx-auto px-4 py-8 md:py-12">
        <nav className="flex justify-between items-center mb-12 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-xl shadow-lg shadow-blue-500/20">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold tracking-tight">NominIA</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInstructions(true)}
              className="p-2 text-gray-500 hover:text-blue-600 transition-colors"
              title="Instrucciones"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </button>
            <DarkModeToggle />
          </div>
        </nav>

        <div aria-live="polite" className="sr-only">
          {announcement}
        </div>

        <AnimatePresence mode="wait">
          {loading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="py-20"
            >
              <LoadingSpinner message={loadingMessage} progress={loadingProgress} />
            </motion.div>
          ) : step === 1 ? (
            <motion.div
              key="step-1"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              className="space-y-12"
            >
              <div className="text-center">
                <h2 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight">
                  Verifica tu nomina en <span className="text-blue-600 dark:text-blue-400">segundos</span>
                </h2>
                <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                  Sube tu archivo y nuestra IA detectara si te estan pagando correctamente segun tu convenio.
                </p>
                <div className="mt-6">
                  <button
                    onClick={() => setShowDemo(!showDemo)}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-0.5"
                  >
                    <span>Probar con Ejemplos</span>
                  </button>
                </div>
              </div>

              {/* Demo Mode Panel */}
              <AnimatePresence>
                {showDemo && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="glass-card p-6 space-y-4">
                      <h3 className="text-xl font-bold gradient-text text-center">Nominas de Ejemplo</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                        Selecciona un ejemplo para ver como funciona el analisis sin necesidad de un archivo real.
                      </p>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <button
                          onClick={() => handleDemoSelect('correct')}
                          className="p-4 rounded-xl border-2 border-green-200 dark:border-green-800 hover:bg-green-50 dark:hover:bg-green-900/20 transition-all text-left"
                        >
                          <div className="text-green-600 font-bold mb-1">Nomina Correcta</div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Convenio General - Tecnico. Todos los conceptos cumplen con el convenio.</p>
                        </button>
                        <button
                          onClick={() => handleDemoSelect('withErrors')}
                          className="p-4 rounded-xl border-2 border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all text-left"
                        >
                          <div className="text-red-600 font-bold mb-1">Nomina con Errores</div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Mercadona - Personal Base. Salario por debajo del minimo del convenio.</p>
                        </button>
                        <button
                          onClick={() => handleDemoSelect('withWarnings')}
                          className="p-4 rounded-xl border-2 border-yellow-200 dark:border-yellow-800 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 transition-all text-left"
                        >
                          <div className="text-yellow-600 font-bold mb-1">Nomina con Advertencias</div>
                          <p className="text-xs text-gray-500 dark:text-gray-400">Transporte Sanitario - TES Conductor. Nocturnidad revisable.</p>
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {error && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="glass-card p-4 border-l-4 border-red-500 bg-red-50 dark:bg-red-900/10"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-red-700 dark:text-red-400 font-medium">{error}</p>
                  </div>
                </motion.div>
              )}

              <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-xl shadow-blue-500/5 p-8 border border-gray-100 dark:border-gray-800">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                  <div className="space-y-6">
                    <h3 className="text-xl font-bold flex items-center gap-3">
                      <span className="flex-none bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 w-8 h-8 rounded-full flex items-center justify-center text-sm">1</span>
                      Sube tu archivo
                    </h3>
                    <FileUpload onFileSelect={handleFileSelect} selectedFile={selectedFile} />
                  </div>

                  <div className="space-y-6">
                    <h3 className="text-xl font-bold flex items-center gap-3">
                      <span className="flex-none bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 w-8 h-8 rounded-full flex items-center justify-center text-sm">2</span>
                      Configuracion
                    </h3>

                    <div className="space-y-4 p-6 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-100 dark:border-gray-800">
                      <div>
                        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Convenio Aplicable</label>
                        <select
                          value={uploadData.convenio}
                          onChange={(e) => {
                            const newConvenio = e.target.value;
                            const validCats = CONVENTION_CATEGORY_KEYS[newConvenio] || [];
                            const currentCat = uploadData.categoria;
                            const newCat = validCats.includes(currentCat) ? currentCat : (DEFAULT_CATEGORIES[newConvenio] || validCats[0] || 'empleado');
                            setUploadData({ convenio: newConvenio, categoria: newCat });
                          }}
                          className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
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
                        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Categoria Profesional</label>
                        <select
                          value={uploadData.categoria}
                          onChange={(e) => setUploadData({ ...uploadData, categoria: e.target.value })}
                          className="w-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                        >
                          {uploadData.convenio === 'transporte_sanitario_andalucia' ? (
                            <>
                              <option value="tes_conductor">TES Conductor</option>
                              <option value="tes_ayudante_camillero">TES Ayudante Camillero</option>
                              <option value="tes_camillero">TES Camillero</option>
                            </>
                          ) : uploadData.convenio === 'mercadona' ? (
                            <>
                              <option value="personal_base">Personal Base</option>
                              <option value="gerente_a">Gerente A (0-2 anhos)</option>
                              <option value="gerente_b">Gerente B (2-4 anhos)</option>
                              <option value="gerente_c">Gerente C (4+ anhos)</option>
                              <option value="coordinador">Coordinador</option>
                            </>
                          ) : uploadData.convenio === 'leroy_merlin' ? (
                            <>
                              <option value="profesional">Profesional</option>
                              <option value="coordinador">Coordinador</option>
                              <option value="tecnico">Tecnico</option>
                            </>
                          ) : (
                            <>
                              <option value="empleado">Empleado</option>
                              <option value="tecnico">Tecnico</option>
                              <option value="mando_intermedio">Mando Intermedio</option>
                              <option value="directivo">Directivo</option>
                            </>
                          )}
                        </select>
                      </div>
                    </div>

                    <button
                      onClick={handleAnalyze}
                      disabled={!selectedFile || loading}
                      className="w-full py-4 px-6 rounded-2xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-lg shadow-lg shadow-blue-500/20 transition-all flex items-center justify-center gap-3"
                    >
                      <span>Analizar Nomina</span>
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          ) : step === 2 ? (
            <motion.div
              key="step-2"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="max-w-4xl mx-auto space-y-8"
            >
              <div className="text-center space-y-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 font-bold text-sm">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                  </span>
                  Paso 2 de 3
                </div>
                <h2 className="text-3xl font-bold">Revisa los datos de tu nomina</h2>
                <p className="text-gray-600 dark:text-gray-400">
                  {extractionInfo && extractionInfo.fieldsFound > 0
                    ? `Hemos detectado ${extractionInfo.fieldsFound} concepto(s) del PDF. Revisa que sean correctos.`
                    : 'Introduce los datos tal como aparecen en tu nomina para compararlos con el convenio.'
                  }
                </p>
              </div>

              {/* Extraction feedback */}
              {extractionInfo && extractionInfo.extractError && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm">
                  <p className="font-bold mb-1">Error al leer el archivo:</p>
                  <p className="font-mono text-xs">{extractionInfo.extractError}</p>
                </div>
              )}

              {extractionInfo && !extractionInfo.extractError && extractionInfo.fieldsFound === 0 && (
                <div className="p-4 rounded-xl bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-400 text-sm">
                  <p className="font-bold mb-1">No hemos podido extraer datos automaticamente.</p>
                  <p>Introduce los datos a mano como aparecen en tu nomina.</p>
                  {extractionInfo.rawPreview && (
                    <details className="mt-2">
                      <summary className="cursor-pointer text-xs text-yellow-600 dark:text-yellow-500">Ver texto detectado (debug)</summary>
                      <pre className="mt-1 text-xs bg-yellow-100 dark:bg-yellow-900/30 p-2 rounded overflow-auto max-h-40 whitespace-pre-wrap">{extractionInfo.rawPreview}</pre>
                    </details>
                  )}
                </div>
              )}

              {extractionInfo && extractionInfo.fieldsFound > 0 && (
                <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400 text-sm">
                  <p className="font-bold">Datos extraidos: {extractionInfo.fieldsFound} concepto{extractionInfo.fieldsFound > 1 ? 's' : ''}.</p>
                  <p>Revisa que los importes coincidan con tu nomina antes de verificar.</p>
                </div>
              )}

              <ManualInput
                onSubmit={handleConfirmAnalysis}
                initialData={reviewData}
                onBack={() => setStep(1)}
              />
            </motion.div>
          ) : (
            <motion.div
              key="step-3"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <h2 className="text-3xl font-bold tracking-tight">Tu Informe de Verificacion</h2>
                  <p className="text-gray-600 dark:text-gray-400 mt-1">Resultados basados en tu convenio colectivo.</p>
                </div>
                <button
                  onClick={() => {
                    setStep(1);
                    setResults(null);
                    setSelectedFile(null);
                    setShowDemo(false);
                  }}
                  className="px-6 py-3 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 font-bold transition-all flex items-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Nueva verificacion
                </button>
              </div>
              {/* Show extraction debug info if available */}
              {extractionInfo && extractionInfo.rawPreview && (
                <details className="glass-card p-4 text-sm text-gray-500 dark:text-gray-400">
                  <summary className="cursor-pointer font-medium">
                    Datos extraidos del archivo ({extractionInfo.fieldsFound} concepto{extractionInfo.fieldsFound !== 1 ? 's' : ''} detectado{extractionInfo.fieldsFound !== 1 ? 's' : ''})
                  </summary>
                  <pre className="mt-2 text-xs bg-gray-50 dark:bg-gray-800 p-3 rounded-lg overflow-auto max-h-48 whitespace-pre-wrap">{extractionInfo.rawPreview}</pre>
                </details>
              )}
              <ResultsDisplay results={results} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default HomePage;
