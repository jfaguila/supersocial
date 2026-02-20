import React from 'react';
import { useLanguage } from '../i18n/LanguageProvider';

const SkipLinks = () => {
  const { t } = useLanguage();

  return (
    <div className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-primary-600 text-white p-2 rounded z-50">
      <a href="#main-content" className="block px-4 py-2 hover:bg-primary-700">
        {t('skipToMain')}
      </a>
      <a href="#file-upload" className="block px-4 py-2 hover:bg-primary-700">
        {t('skipToFileUpload')}
      </a>
      <a href="#manual-input" className="block px-4 py-2 hover:bg-primary-700">
        {t('skipToForm')}
      </a>
    </div>
  );
};

export default SkipLinks;
