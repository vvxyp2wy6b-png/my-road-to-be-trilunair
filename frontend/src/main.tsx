/**
 * نقطة الدخول الرئيسية لواجهة مركز القيادة الهولوغرامي
 * My Road to be Trilunair Dr.MaJoOoOoOoD — QUANTUM AI TRADING COMMAND CENTER
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { ThemeProvider } from './theme/ThemeContext';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>
);
