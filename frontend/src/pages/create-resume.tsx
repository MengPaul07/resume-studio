import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader2, Sparkles, Upload, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { saveRecentResume } from '../api';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { PageTransition } from '../components/layout/page-transition';
import { buildResumeSkeleton, buildTailorHint, type ResumeBrief } from '../lib/create-resume-skeleton';

export function CreateResumePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [targetRole, setTargetRole] = useState('');
  const [industry, setIndustry] = useState('');
  const [seniority, setSeniority] = useState('senior');
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [background, setBackground] = useState('');
  const [language, setLanguage] = useState<'en' | 'zh'>('en');

  const [pageState, setPageState] = useState<PageState>('idle');
  const [errorText, setErrorText] = useState('');

  const formValid =
    targetRole.trim().length >= 2 &&
    background.trim().length >= 10;

  const SENIORITY_OPTIONS = [
    { value: 'entry', label: t('createResume.entry') },
    { value: 'mid', label: t('createResume.mid') },
    { value: 'senior', label: t('createResume.senior') },
    { value: 'lead', label: t('createResume.lead') },
    { value: 'principal', label: t('createResume.principal') },
  ];

  function addSkill() {
    const value = skillInput.trim();
    if (!value) return;
    if (skills.includes(value)) {
      setSkillInput('');
      return;
    }
    setSkills((prev) => [...prev, value]);
    setSkillInput('');
  }

  function removeSkill(index: number) {
    setSkills((prev) => prev.filter((_, i) => i !== index));
  }

  function handleSkillKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSkill();
    }
    if (e.key === 'Backspace' && !skillInput && skills.length > 0) {
      removeSkill(skills.length - 1);
    }
  }

  async function handleSubmit() {
    if (!formValid || pageState !== 'idle') return;

    setPageState('generating');
    setErrorText('');

    const brief: ResumeBrief = {
      targetRole: targetRole.trim(),
      industry: industry.trim() || targetRole.trim(),
      seniority,
      skills,
      background: background.trim(),
      language,
    };

    try {
      const skeleton = buildResumeSkeleton(brief);
      const title = brief.targetRole;

      const saved = await saveRecentResume({
        title,
        status: 'draft',
        source: 'generated',
        tags: ['generated', `lang:${brief.language}`, `seniority:${brief.seniority}`],
        resume_obj: skeleton,
        output_markdown: '',
        output_html: '',
      });

      setPageState('redirecting');

      const hint = buildTailorHint(brief);
      const params = new URLSearchParams();
      params.set('resumeId', saved.id);
      params.set('hint', hint);

      setTimeout(() => {
        navigate(`/tailor?${params.toString()}`);
      }, 600);
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : t('createResume.failedToCreate'));
      setPageState('error');
    }
  }

  return (
    <PageTransition>
      <section className="min-h-screen px-4 py-10 md:px-8">
        <div className="mx-auto max-w-2xl">
          {/* Header */}
          <div className="mb-8 flex items-center justify-between">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 border border-black dark:border-[var(--brand-line)] bg-canvas px-3 py-2 font-mono text-xs uppercase"
            >
              <ArrowLeft className="size-4" />
              {t('createResume.back')}
            </Link>
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1 font-mono text-[10px] uppercase text-gray-500 dark:text-[var(--brand-ink-muted)] hover:text-black dark:hover:text-[var(--brand-ink)]"
            >
              <Upload className="size-3" />
              {t('createResume.importFromFile')}
            </Link>
          </div>

          {/* Card */}
          <div className="border-2 border-black dark:border-[var(--brand-line-strong)] bg-white dark:bg-[var(--brand-surface)] shadow-[8px_8px_0px_0px_#000000]">
            <div className="border-b-2 border-black dark:border-[var(--brand-line-strong)] bg-[var(--brand-surface-soft)] px-6 py-5">
              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-[var(--brand-signal)]">
                {t('createResume.newResume')}
              </p>
              <h1 className="mt-1 font-serif text-3xl uppercase leading-none">
                {t('createResume.createFromBrief')}
              </h1>
              <p className="mt-2 font-mono text-xs text-gray-600 dark:text-[var(--brand-ink-muted)]">
                {t('createResume.description')}
              </p>
            </div>

            {pageState === 'redirecting' ? (
              <div className="flex flex-col items-center gap-4 px-6 py-16 text-center">
                <Sparkles className="size-10 text-[var(--brand-signal)]" />
                <p className="font-serif text-2xl uppercase">{t('createResume.resumeCreated')}</p>
                <p className="font-mono text-xs text-gray-600 dark:text-[var(--brand-ink-muted)]">
                  {t('createResume.redirectingToTailor')}
                </p>
              </div>
            ) : (
              <div className="space-y-5 px-6 py-6">
                {/* Target Role */}
                <div>
                  <label className="mb-1 block font-mono text-[11px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">
                    {t('createResume.targetRole')}
                  </label>
                  <input
                    value={targetRole}
                    onChange={(e) => setTargetRole(e.target.value)}
                    placeholder={t('createResume.targetRolePlaceholder')}
                    disabled={pageState === 'generating'}
                    className="w-full border border-black dark:border-[var(--brand-line)] bg-[var(--brand-paper)] px-3 py-2.5 font-mono text-sm outline-none focus:border-[var(--brand-signal)] disabled:opacity-50"
                  />
                </div>

                {/* Industry + Seniority */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="mb-1 block font-mono text-[11px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">
                      {t('createResume.industry')}
                    </label>
                    <input
                      value={industry}
                      onChange={(e) => setIndustry(e.target.value)}
                      placeholder={t('createResume.industryPlaceholder')}
                      disabled={pageState === 'generating'}
                      className="w-full border border-black dark:border-[var(--brand-line)] bg-[var(--brand-paper)] px-3 py-2.5 font-mono text-sm outline-none focus:border-[var(--brand-signal)] disabled:opacity-50"
                    />
                  </div>
                  <div>
                    <label className="mb-1 block font-mono text-[11px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">
                      {t('createResume.seniority')}
                    </label>
                    <select
                      value={seniority}
                      onChange={(e) => setSeniority(e.target.value)}
                      disabled={pageState === 'generating'}
                      className="w-full border border-black dark:border-[var(--brand-line)] bg-[var(--brand-paper)] px-3 py-2.5 font-mono text-sm outline-none focus:border-[var(--brand-signal)] disabled:opacity-50"
                    >
                      {SENIORITY_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Skills */}
                <div>
                  <label className="mb-1 block font-mono text-[11px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">
                    {t('createResume.keySkills')}
                  </label>
                  <div className="flex flex-wrap gap-1.5 rounded-none border border-black dark:border-[var(--brand-line)] bg-[var(--brand-paper)] px-3 py-2">
                    {skills.map((skill, i) => (
                      <span
                        key={`${skill}-${i}`}
                        className="inline-flex items-center gap-1 border border-black dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-2 py-0.5 font-mono text-[11px]"
                      >
                        {skill}
                        <button
                          type="button"
                          onClick={() => removeSkill(i)}
                          disabled={pageState === 'generating'}
                          className="ml-0.5 text-gray-400 dark:text-[var(--brand-ink-muted)] hover:text-black dark:hover:text-[var(--brand-ink)] disabled:opacity-50"
                        >
                          <X className="size-3" />
                        </button>
                      </span>
                    ))}
                    <input
                      value={skillInput}
                      onChange={(e) => setSkillInput(e.target.value)}
                      onKeyDown={handleSkillKeyDown}
                      onBlur={() => addSkill()}
                      placeholder={skills.length ? t('createResume.addMore') : t('createResume.typeAndPressEnter')}
                      disabled={pageState === 'generating'}
                      className="min-w-[120px] flex-1 bg-transparent px-1 py-0.5 font-mono text-sm outline-none placeholder:text-gray-400 dark:placeholder:text-[var(--brand-ink-muted)] disabled:opacity-50"
                    />
                  </div>
                </div>

                {/* Background */}
                <div>
                  <label className="mb-1 block font-mono text-[11px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">
                    {t('createResume.background')}
                    <span className="ml-1 text-gray-400 dark:text-[var(--brand-ink-muted)]">{t('createResume.freeText')}</span>
                  </label>
                  <Textarea
                    value={background}
                    onChange={(e) => setBackground(e.target.value)}
                    placeholder={
                      language === 'zh'
                        ? t('createResume.backgroundPlaceholderZh')
                        : t('createResume.backgroundPlaceholderEn')
                    }
                    disabled={pageState === 'generating'}
                    className="min-h-[120px]"
                  />
                </div>

                {/* Language */}
                <div>
                  <label className="mb-2 block font-mono text-[11px] uppercase tracking-wide text-gray-700 dark:text-[var(--brand-ink)]">
                    {t('createResume.resumeLanguage')}
                  </label>
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={() => setLanguage('en')}
                      disabled={pageState === 'generating'}
                      className={`border px-4 py-2 font-mono text-xs uppercase transition-colors ${
                        language === 'en'
                          ? 'border-black dark:border-zinc-500 bg-black dark:bg-zinc-800 text-white dark:text-white'
                          : 'border-black/25 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] text-gray-600 dark:text-[var(--brand-ink-muted)] hover:border-black dark:hover:border-[var(--brand-ink)]'
                      } disabled:opacity-50`}
                    >
                      {t('createResume.english')}
                    </button>
                    <button
                      type="button"
                      onClick={() => setLanguage('zh')}
                      disabled={pageState === 'generating'}
                      className={`border px-4 py-2 font-mono text-xs uppercase transition-colors ${
                        language === 'zh'
                          ? 'border-black dark:border-zinc-500 bg-black dark:bg-zinc-800 text-white dark:text-white'
                          : 'border-black/25 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] text-gray-600 dark:text-[var(--brand-ink-muted)] hover:border-black dark:hover:border-[var(--brand-ink)]'
                      } disabled:opacity-50`}
                    >
                      {t('createResume.chinese')}
                    </button>
                  </div>
                </div>

                {/* Error */}
                {errorText ? (
                  <div className="border border-[var(--status-failed)] bg-red-50 dark:bg-red-900/20 px-4 py-3">
                    <p className="font-mono text-xs text-[var(--status-failed)]">{errorText}</p>
                  </div>
                ) : null}

                {/* Submit */}
                <Button
                  onClick={handleSubmit}
                  disabled={!formValid || pageState === 'generating'}
                  className="w-full"
                >
                  {pageState === 'generating' ? (
                    <>
                      <Loader2 className="animate-spin" />
                      {t('createResume.generatingSkeleton')}
                    </>
                  ) : (
                    <>
                      <Sparkles />
                      {t('createResume.generateAndOpen')}
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </div>
      </section>
    </PageTransition>
  );
}

type PageState = 'idle' | 'generating' | 'error' | 'redirecting';
