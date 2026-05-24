import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { MessageCircle, Briefcase } from 'lucide-react';
import { InterviewModal } from '../components/tailor/InterviewModal';
import { getRecentResume, listRecentResumes, listJobDescriptions, getJobDescription } from '../api';
import type { RecentResumeRecord, JobDescriptionRecord } from '../types';
import type { JDMatch } from '../lib/tailor/types';

interface JDCard {
  id: string;
  title: string;
  text: string;
  source: 'server' | 'localStorage';
}

function loadLocalJDMatch(): JDMatch | null {
  try {
    const raw = localStorage.getItem('tailor_target_jd');
    if (!raw) return null;
    return JSON.parse(raw) as JDMatch;
  } catch { return null; }
}

export function InterviewPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resumeIdParam = searchParams.get('resumeId') || '';

  const [resumes, setResumes] = useState<RecentResumeRecord[]>([]);
  const [serverJds, setServerJds] = useState<JobDescriptionRecord[]>([]);
  const [pickedResumeId, setPickedResumeId] = useState<string>(resumeIdParam || '');
  const [pickedJdId, setPickedJdId] = useState<string>('');
  const [selectedResume, setSelectedResume] = useState<RecentResumeRecord | null>(null);
  const [starting, setStarting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRecentResumes(20).then(setResumes).finally(() => setLoading(false));
    listJobDescriptions(20).then(setServerJds).catch(() => {});
    if (resumeIdParam) setPickedResumeId(resumeIdParam);
  }, [resumeIdParam]);

  // Unified JD list: server JDs + localStorage JD
  const jdCards = useMemo<JDCard[]>(() => {
    const cards: JDCard[] = [];
    const local = loadLocalJDMatch();
    if (local && local.text && local.text.trim()) {
      cards.push({ id: local.id || '__local__', title: local.metadata && typeof local.metadata === 'object' && 'title' in local.metadata ? String((local.metadata as any).title) : 'Current Target JD', text: local.text, source: 'localStorage' });
    }
    for (const jd of serverJds) {
      if (!cards.find(c => c.id === jd.id)) {
        cards.push({ id: jd.id, title: jd.title || 'Untitled JD', text: jd.content || '', source: 'server' });
      }
    }
    return cards;
  }, [serverJds]);

  const startInterview = async () => {
    const picked = resumes.find(r => r.id === pickedResumeId);
    if (!picked) return;
    setStarting(true);
    const jdCard = jdCards.find(j => j.id === pickedJdId);
    if (jdCard && !jdCard.text) {
      try { jdCard.text = (await getJobDescription(jdCard.id)).content || ''; }
      catch { /* ignore */ }
    }
    let resume: RecentResumeRecord;
    try { resume = await getRecentResume(picked.id); }
    catch { resume = picked; }
    setSelectedResume(resume);
    setStarting(false);
  };

  const targetJdCard = pickedJdId ? jdCards.find(j => j.id === pickedJdId) : undefined;

  if (selectedResume) {
    return (
      <div className="h-[calc(100vh-57px)]">
        <InterviewModal
          embedded
          resumeObj={(selectedResume.resume_obj || {}) as Record<string, unknown>}
          resumeId={selectedResume.id}
          targetJd={targetJdCard?.text}
          targetJdId={targetJdCard?.id}
          targetJdTitle={targetJdCard?.title}
          onClose={() => { setSelectedResume(null); }}
        />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-57px)] flex flex-col">
      {/* Hero */}
      <section className="flex flex-col items-center text-center px-6 pt-16 pb-10">
        <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-signal)] text-white shadow-lg shadow-[var(--brand-signal)]/20">
          <MessageCircle className="size-7" />
        </div>
        <h1 className="font-sans text-2xl font-bold text-[var(--brand-ink)] tracking-tight">{t('nav.interview')}</h1>
        <p className="mt-2 max-w-md font-sans text-sm text-[var(--brand-ink-muted)] leading-relaxed">
          Select a resume and optionally a target job description to practice with AI interviewers.
        </p>
      </section>

      {/* Selection */}
      <section className="flex-1 px-6 pb-12">
        <div className="mx-auto max-w-4xl space-y-8">

          {/* Resume selection */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-sans text-sm font-semibold text-[var(--brand-ink)]">Select a resume</h2>
              <span className="font-sans text-[11px] text-[var(--brand-ink-muted)]">{resumes.length} available</span>
            </div>

            {loading ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {[1,2,3].map(i => (
                  <div key={i} className="animate-pulse rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] h-28" />
                ))}
              </div>
            ) : resumes.length === 0 ? (
              <div className="rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-12 text-center">
                <MessageCircle className="mx-auto size-8 text-[var(--brand-ink-muted)]/20 mb-3" />
                <p className="font-sans text-sm text-[var(--brand-ink-muted)]">No resumes yet</p>
                <p className="mt-1 font-sans text-xs text-[var(--brand-ink-muted)]">Create or import a resume first, then come back here.</p>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {resumes.map(r => (
                  <button
                    key={r.id}
                    onClick={() => setPickedResumeId(r.id)}
                    className={`group rounded-xl border p-4 text-left transition-all ${
                      pickedResumeId === r.id
                        ? 'border-[var(--brand-signal)] bg-[var(--brand-signal-soft)] shadow-sm'
                        : 'border-[var(--brand-line)] bg-[var(--brand-surface)] hover:border-[var(--brand-signal)] hover:shadow-md'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors ${
                        pickedResumeId === r.id
                          ? 'bg-[var(--brand-signal)] text-white'
                          : 'bg-[var(--brand-signal-soft)] text-[var(--brand-signal)] group-hover:bg-[var(--brand-signal)] group-hover:text-white'
                      }`}>
                        <MessageCircle className="size-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-sans text-sm font-semibold text-[var(--brand-ink)] truncate">{r.title || 'Untitled Resume'}</p>
                        <p className="mt-0.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">
                          {r.status || 'draft'} &middot; {r.tags?.slice(0, 2).join(', ') || 'No tags'}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* JD selection */}
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-sans text-sm font-semibold text-[var(--brand-ink)]">Target JD (optional)</h2>
              <span className="font-sans text-[11px] text-[var(--brand-ink-muted)]">{jdCards.length} available</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <button
                onClick={() => setPickedJdId('')}
                className={`rounded-xl border p-4 text-left transition-all ${
                  !pickedJdId
                    ? 'border-[var(--brand-signal)] bg-[var(--brand-signal-soft)] shadow-sm'
                    : 'border-[var(--brand-line)] bg-[var(--brand-surface)] hover:border-[var(--brand-line-strong)]'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors ${
                    !pickedJdId ? 'bg-[var(--brand-signal)] text-white' : 'bg-[var(--brand-surface-soft)] text-[var(--brand-ink-muted)]'
                  }`}>
                    <Briefcase className="size-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-sans text-sm font-semibold text-[var(--brand-ink)]">General Practice</p>
                    <p className="mt-0.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">No specific job target</p>
                  </div>
                </div>
              </button>
              {jdCards.map(jd => (
                <button
                  key={jd.id}
                  onClick={() => setPickedJdId(jd.id)}
                  className={`group rounded-xl border p-4 text-left transition-all ${
                    pickedJdId === jd.id
                      ? 'border-[var(--brand-signal)] bg-[var(--brand-signal-soft)] shadow-sm'
                      : 'border-[var(--brand-line)] bg-[var(--brand-surface)] hover:border-[var(--brand-signal)] hover:shadow-md'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      pickedJdId === jd.id
                        ? 'bg-[var(--brand-signal)] text-white'
                        : 'bg-[var(--brand-surface-soft)] text-[var(--brand-ink-muted)] group-hover:bg-[var(--brand-signal)] group-hover:text-white'
                    }`}>
                      <Briefcase className="size-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <p className="font-sans text-sm font-semibold text-[var(--brand-ink)] truncate">{jd.title}</p>
                        {jd.source === 'localStorage' && (
                          <span className="shrink-0 rounded bg-[var(--brand-signal-soft)] px-1.5 py-0.5 font-sans text-[9px] font-medium text-[var(--brand-signal)]">active</span>
                        )}
                      </div>
                      <p className="mt-0.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">
                        {jd.text.length} chars &middot; {jd.text.slice(0, 50).replace(/\n/g, ' ')}{jd.text.length > 50 ? '...' : ''}
                      </p>
                    </div>
                  </div>
                </button>
              ))}
              {!loading && jdCards.length === 0 && (
                <div className="rounded-xl border border-dashed border-[var(--brand-line)] bg-[var(--brand-surface)] p-4 text-center">
                  <p className="font-sans text-xs text-[var(--brand-ink-muted)]">No job descriptions yet</p>
                  <p className="mt-0.5 font-sans text-[10px] text-[var(--brand-ink-muted)]">Set a Target JD in AI Tailor or import one from Dashboard</p>
                </div>
              )}
            </div>
          </div>

          {/* Start CTA */}
          {pickedResumeId && (
            <div className="pt-4 border-t border-[var(--brand-line)]">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-[var(--brand-surface-soft)] border border-[var(--brand-line)]">
                <div className="flex-1">
                  <p className="font-sans text-xs text-[var(--brand-ink-muted)]">Ready to start:</p>
                  <p className="font-sans text-sm font-semibold text-[var(--brand-ink)]">
                    Resume: {resumes.find(r => r.id === pickedResumeId)?.title || '...'}
                    {pickedJdId && <span className="text-[var(--brand-ink-muted)]"> &middot; JD: {jdCards.find(j => j.id === pickedJdId)?.title || '...'}</span>}
                  </p>
                </div>
                <button onClick={startInterview}
                  className="rounded-lg bg-[var(--brand-signal)] px-6 py-2.5 font-sans text-sm font-semibold text-white transition-all hover:brightness-110 active:scale-[0.98] shadow-lg shadow-[var(--brand-signal)]/20"
                >
                  Start Interview
                </button>
              </div>
            </div>
          )}

        </div>
      </section>
    </div>
  );
}
