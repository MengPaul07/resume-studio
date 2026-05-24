import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import zh from './locales/zh.json';

const STORAGE_KEY = 'app_language';

function detectLanguage(): string {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'en' || stored === 'zh') return stored;
  const browserLang = navigator.language.slice(0, 2);
  return browserLang === 'zh' ? 'zh' : 'en';
}

i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, zh: { translation: zh } },
  lng: detectLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
});

export function setLanguage(lang: 'en' | 'zh') {
  localStorage.setItem(STORAGE_KEY, lang);
  i18n.changeLanguage(lang);
}

export function getLanguage(): 'en' | 'zh' {
  const lng = i18n.language;
  return lng === 'zh' ? 'zh' : 'en';
}

export default i18n;
