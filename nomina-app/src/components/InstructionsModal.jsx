import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const InstructionsModal = ({ isOpen, onClose }) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
          >
            <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-2xl w-full p-8 pointer-events-auto overflow-y-auto max-h-[90vh]">
              <div className="flex justify-between items-start mb-6">
                <h2 className="text-2xl font-bold gradient-text">Como funciona?</h2>
                <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-6 text-gray-600 dark:text-gray-300">
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center font-bold">1</div>
                  <div>
                    <h3 className="font-semibold text-lg text-gray-800 dark:text-white mb-2">Sube tu Nomina</h3>
                    <p>Arrastra tu archivo PDF o imagen al recuadro. Nuestro sistema intentara leer automaticamente datos clave como el <strong>Salario Base</strong>, <strong>Antiguedad</strong> y <strong>Plus Convenio</strong>.</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center font-bold">2</div>
                  <div>
                    <h3 className="font-semibold text-lg text-gray-800 dark:text-white mb-2">Verifica los Datos</h3>
                    <p>Revisa el formulario de la derecha. Si el sistema no leyo algun dato correctamente (como las horas extras), puedes corregirlo manualmente antes de analizar.</p>
                  </div>
                </div>

                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center font-bold">3</div>
                  <div>
                    <h3 className="font-semibold text-lg text-gray-800 dark:text-white mb-2">Obten el Analisis</h3>
                    <p>Pulsa "Verificar Nomina". Compararemos tus datos con las tablas oficiales del convenio seleccionado (General, Transporte Sanitario, Mercadona, etc.) para ver si te estan pagando lo correcto.</p>
                  </div>
                </div>
              </div>

              <div className="mt-8 text-center">
                <button
                  onClick={onClose}
                  className="btn-primary"
                >
                  Entendido!
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default InstructionsModal;
