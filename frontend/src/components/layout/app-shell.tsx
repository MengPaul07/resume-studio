import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { FileText, WandSparkles, Settings, LayoutDashboard, PenSquare, Sun, Moon, MessageCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getLanguage, setLanguage } from '../../i18n/config';

const NAV_KEYS = ['dashboard', 'layoutBuilder', 'tailor', 'interview', 'settings'] as const;
const NAV_ICONS = [LayoutDashboard, PenSquare, WandSparkles, MessageCircle, Settings];
const NAV_PATHS: Record<string, string> = {
  dashboard: '/dashboard',
  layoutBuilder: '/builder',
  tailor: '/tailor',
  interview: '/interview',
  settings: '/settings',
};

type Theme = 'light' | 'dark';

function getStoredTheme(): Theme {
  return (localStorage.getItem('app_theme') as Theme) || 'light';
}

function applyTheme(theme: Theme) {
  localStorage.setItem('app_theme', theme);
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

export function AppShell() {
  const { t, i18n } = useTranslation();
  const [theme, setTheme] = useState<Theme>(getStoredTheme);

  useEffect(() => {
    document.documentElement.lang = i18n.language;
  }, [i18n.language]);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggleLang = () => setLanguage(getLanguage() === 'zh' ? 'en' : 'zh');
  const toggleTheme = () => setTheme(theme === 'light' ? 'dark' : 'light');

  return (
    <div className="writing-studio min-h-screen overflow-x-hidden bg-background text-foreground brand-grid-bg">
      <header className="sticky top-0 z-50 border-b border-[var(--brand-line)] bg-white/80 dark:bg-[var(--brand-surface)]/80 backdrop-blur-xl backdrop-saturate-150">
        <div className="mx-auto flex h-14 max-w-[88rem] items-center justify-between px-4 md:px-6">
          <Link to="/dashboard" className="inline-flex items-center gap-2.5">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand-signal)] text-white shadow-sm">
              <FileText className="size-4" />
            </span>
            <span className="font-sans text-sm font-semibold text-[var(--brand-ink)]">Resume Studio</span>
          </Link>
          <div className="flex items-center gap-1 md:gap-3">
            <nav className="hidden items-center gap-0.5 rounded-xl bg-[var(--brand-surface-soft)]/80 p-1 md:flex">
              {NAV_KEYS.map((key, i) => {
                const Icon = NAV_ICONS[i];
                return (
                  <NavLink
                    key={key}
                    to={NAV_PATHS[key]}
                    className={({ isActive }) =>
                      `inline-flex items-center gap-2 rounded-lg px-3 py-1.5 font-sans text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-white dark:bg-[var(--brand-surface-soft)] text-[var(--brand-signal)] shadow-sm'
                          : 'text-[var(--brand-ink-muted)] hover:text-[var(--brand-ink)] hover:bg-white/60 dark:hover:bg-[var(--brand-surface-soft)]/60'
                      }`
                    }
                  >
                    <Icon className="size-3.5" />
                    {t(`nav.${key}`)}
                  </NavLink>
                );
              })}
            </nav>
            <button
              onClick={toggleTheme}
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg font-sans text-xs font-medium text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface-soft)] transition-colors md:h-8 md:w-8"
              title={theme === 'light' ? '切换暗色模式' : 'Toggle dark mode'}
            >
              {theme === 'light' ? <Moon className="size-3.5" /> : <Sun className="size-3.5" />}
            </button>
            <button
              onClick={toggleLang}
              className="inline-flex h-10 min-w-10 items-center justify-center rounded-lg px-2 font-sans text-xs font-semibold text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface-soft)] transition-colors md:h-8"
              title={getLanguage() === 'zh' ? 'Switch to English' : '切换到中文'}
            >
              {getLanguage() === 'zh' ? 'EN' : '中'}
            </button>
          </div>
        </div>
      </header>
      <main className="pb-[calc(4.5rem+env(safe-area-inset-bottom))] md:pb-0">
        <Outlet />
      </main>
      <nav
        aria-label="Mobile navigation"
        className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-5 border-t border-[var(--brand-line)] bg-white/95 px-1 pb-[env(safe-area-inset-bottom)] backdrop-blur-xl dark:bg-[var(--brand-surface)]/95 md:hidden"
      >
        {NAV_KEYS.map((key, i) => {
          const Icon = NAV_ICONS[i];
          return (
            <NavLink
              key={key}
              to={NAV_PATHS[key]}
              className={({ isActive }) =>
                `relative flex min-h-16 flex-col items-center justify-center gap-1 px-1 font-sans text-[10px] font-medium ${
                  isActive ? 'text-[var(--brand-signal)]' : 'text-[var(--brand-ink-muted)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span className={`absolute top-1.5 h-0.5 w-5 rounded-full ${isActive ? 'bg-[var(--brand-signal)]' : 'bg-transparent'}`} />
                  <Icon className="size-5" strokeWidth={isActive ? 2.25 : 1.75} />
                  <span className="max-w-full truncate">{t(`nav.${key}`)}</span>
                </>
              )}
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}
