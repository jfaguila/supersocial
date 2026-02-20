import React from 'react';
import { useLanguage } from '../i18n/LanguageProvider';

const LanguageSelector = () => {
  const { language, changeLanguage, availableLanguages } = useLanguage();

  return (
    <div className="fixed top-4 right-4 z-50">
      <div className="glass-card p-2 flex items-center space-x-2">
        {availableLanguages.map((lang) => (
          <button
            key={lang.code}
            onClick={() => changeLanguage(lang.code)}
            className={`
              px-3 py-2 rounded-lg text-sm font-medium transition-all duration-300
              ${language === lang.code
                ? 'bg-primary-600 text-white'
                : 'text-gray-600 hover:bg-gray-100'
              }
            `}
            title={lang.name}
          >
            <span className="mr-2">{lang.flag}</span>
            <span className="hidden sm:inline">{lang.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
};

export default LanguageSelector;
