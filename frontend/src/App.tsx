import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/app-shell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { DashboardPage } from './pages/dashboard';

// Route-level code splitting: heavy pages load on demand
const CreateResumePage = lazy(() => import('./pages/create-resume').then(m => ({ default: m.CreateResumePage })));
const ResumeViewPage = lazy(() => import('./pages/resume-view').then(m => ({ default: m.ResumeViewPage })));
const TailorChatPage = lazy(() => import('./pages/tailor-chat').then(m => ({ default: m.TailorChatPage })));
const SettingsPage = lazy(() => import('./pages/settings').then(m => ({ default: m.SettingsPage })));
const NotFoundPage = lazy(() => import('./pages/not-found').then(m => ({ default: m.NotFoundPage })));

function PageSkeleton() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="space-y-4 w-full max-w-[48rem] px-6">
        <div className="animate-pulse rounded-lg bg-[var(--brand-surface-soft)] h-8 w-48" />
        <div className="animate-pulse rounded-lg bg-[var(--brand-surface-soft)] h-64 w-full" />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageSkeleton />}>
        <ErrorBoundary>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />

          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/create" element={<CreateResumePage />} />
            <Route path="/builder" element={<ResumeViewPage />} />
            <Route path="/tailor" element={<TailorChatPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/resumes/:id" element={<ResumeViewPage />} />
          </Route>

          <Route path="/home" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
        </ErrorBoundary>
      </Suspense>
    </BrowserRouter>
  );
}
