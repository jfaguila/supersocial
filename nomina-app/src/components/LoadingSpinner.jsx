import React from 'react';
import { motion } from 'framer-motion';

const LoadingSpinner = ({ message, progress = null }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="glass-card p-8 text-center space-y-6"
    >
      <div className="flex flex-col items-center space-y-4">
        <div className="relative">
          <div className="w-16 h-16 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
          {progress !== null && (
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-primary-600">{Math.round(progress)}%</span>
            </div>
          )}
        </div>

        <div className="space-y-2">
          <h3 className="text-xl font-bold gradient-text">
            {message || 'Procesando...'}
          </h3>
          <p className="text-gray-600 text-sm max-w-md mx-auto">
            Esto puede tardar unos segundos. Por favor, espera...
          </p>
        </div>
      </div>

      <div className="space-y-3 pt-4 border-t border-gray-100">
        <div className="flex items-center justify-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-primary-600 rounded-full animate-pulse"></div>
            <div className="w-2 h-2 bg-primary-600 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-2 h-2 bg-primary-600 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
          </div>
          <span className="text-sm text-gray-500">Analizando documento</span>
        </div>

        <div className="max-w-xs mx-auto">
          <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progress || 0}%` }}
            ></div>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 rounded-xl p-4 max-w-sm mx-auto">
        <div className="flex items-start space-x-2">
          <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
          <div className="text-left">
            <p className="text-xs text-blue-800 font-medium">Consejo</p>
            <p className="text-xs text-blue-600 mt-1">
              Asegurate de que la imagen o PDF sea claro y legible para mejores resultados.
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default LoadingSpinner;
