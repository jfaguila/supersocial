import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations } from './translations';

const LanguageContext = createContext();

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState('es');

  useEffect(() => {
    const browserLang = navigator.language || navigator.userLanguage;
    if (browserLang.startsWith('en')) {
      setLanguage('en');
    }
  }, []);

  const t = (key) => {
    const keys = key.split('.');
    let value = translations[language];

    for (const k of keys) {
      if (value && value[k]) {
        value = value[k];
      } else {
        value = translations.es;
        for (const fallbackKey of keys) {
          if (value && value[fallbackKey]) {
            value = value[fallbackKey];
          } else {
            return key;
          }
        }
        break;
      }
    }

    return value || key;
  };

  const changeLanguage = (lang) => {
    setLanguage(lang);
    localStorage.setItem('language', lang);
  };

  useEffect(() => {
    const savedLang = localStorage.getItem('language');
    if (savedLang && ['es', 'en'].includes(savedLang)) {
      setLanguage(savedLang);
    }
  }, []);

  const value = {
    language,
    t,
    changeLanguage,
    availableLanguages: [
      { code: 'es', name: 'Espanol', flag: '\uD83C\uDDEA\uD83C\uDDF8' },
      { code: 'en', name: 'English', flag: '\uD83C\uDDEC\uD83C\uDDE7' }
    ]
  };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};
