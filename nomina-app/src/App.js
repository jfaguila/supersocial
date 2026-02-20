import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { LanguageProvider } from './i18n/LanguageProvider';
import SkipLinks from './components/SkipLinks';
import LanguageSelector from './components/LanguageSelector';
import HomePage from './pages/HomePage';
import './index.css';

function App() {
  return (
    <LanguageProvider>
      <Router>
        <div className="min-h-screen">
          <SkipLinks />
          <LanguageSelector />
          <Routes>
            <Route path="/" element={<HomePage />} />
          </Routes>
        </div>
      </Router>
    </LanguageProvider>
  );
}

export default App;
