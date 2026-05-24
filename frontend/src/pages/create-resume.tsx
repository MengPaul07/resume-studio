import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Sparkles, Briefcase, GraduationCap, Code } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { saveRecentResume } from '../api';
import { Button } from '../components/ui/button';
import { PageTransition } from '../components/layout/page-transition';
import { buildResumeSkeleton, buildTailorHint, type ResumeBrief } from '../lib/create-resume-skeleton';

export function CreateResumePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [targetRole, setTargetRole] = useState('');
  const [industry, setIndustry] = useState('');
  const [seniority, setSeniority] = useState('senior');
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [background, setBackground] = useState('');
  const [language, setLanguage] = useState<'en' | 'zh'>('en');

  const [pageState, setPageState] = useState<'idle' | 'generating' | 'error' | 'redirecting'>('idle');
  const [errorText, setErrorText] = useState('');
  
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement>(null);

  // Auto focus input when step changes
  useEffect(() => {
    if (inputRef.current && step !== 4 && pageState === 'idle') {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [step, pageState]);

  const SENIORITY_OPTIONS = [
    { value: 'entry', label: t('createResume.entry') || 'Entry Level' },
    { value: 'mid', label: t('createResume.mid') || 'Mid Level' },
    { value: 'senior', label: t('createResume.senior') || 'Senior' },
    { value: 'lead', label: t('createResume.lead') || 'Lead' },
    { value: 'principal', label: t('createResume.principal') || 'Principal' },
  ];

  function addSkill() {
    const value = skillInput.trim();
    if (!value) return;
    if (!skills.includes(value)) {
      setSkills((prev) => [...prev, value]);
    }
    setSkillInput('');
  }

  function handleSkillKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSkill();
    }
    if (e.key === 'Backspace' && !skillInput && skills.length > 0) {
      setSkills((prev) => prev.slice(0, -1));
    }
  }

  const handleNext = () => {
    if (step < 3) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  async function handleSubmit() {
    if (pageState !== 'idle') return;

    setPageState('generating');
    setErrorText('');

    const brief: ResumeBrief = {
      targetRole: targetRole.trim() || 'Software Engineer',
      industry: industry.trim() || targetRole.trim() || 'Technology',
      seniority,
      skills,
      background: background.trim() || 'I am an experienced professional looking for a new role.',
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
      }, 1500);
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : 'Failed to create resume');
      setPageState('error');
    }
  }

  const handleInputEnter = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if ((step === 0 && targetRole) || (step === 1 && industry)) {
         handleNext();
      }
    }
  };

  const stepsConfig = [
    {
      title: "What's your target role?",
      subtitle: "To give the AI a clear focal point for your resume.",
      icon: <Briefcase className="size-6" />,
      content: (
        <input
          ref={inputRef as any}
          value={targetRole}
          onChange={(e) => setTargetRole(e.target.value)}
          onKeyDown={handleInputEnter}
          placeholder="e.g. Senior Frontend Engineer"
          className="w-full border-none bg-transparent px-0 py-4 font-serif text-3xl md:text-5xl outline-none placeholder:text-[var(--brand-ink-muted)] text-[var(--brand-ink)]"
        />
      ),
      canAdvance: targetRole.trim().length >= 2,
    },
    {
      title: "What industry & level?",
      subtitle: "We tune the default keywords and narrative tone accordingly.",
      icon: <GraduationCap className="size-6" />,
      content: (
        <div className="space-y-8 mt-4">
          <div>
            <label className="mb-3 block font-mono text-xs uppercase tracking-wide text-[var(--brand-ink-muted)]">Industry / Domain</label>
            <input
              ref={inputRef as any}
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              onKeyDown={handleInputEnter}
              placeholder="e.g. AI / SaaS / Fintech"
              className="w-full border-b border-[var(--brand-line)] bg-transparent px-0 py-3 font-serif text-2xl outline-none focus:border-[var(--brand-ink)] text-[var(--brand-ink)]"
            />
          </div>
          <div>
            <label className="mb-3 block font-mono text-xs uppercase tracking-wide text-[var(--brand-ink-muted)]">Seniority Level</label>
            <div className="flex flex-wrap gap-3">
              {SENIORITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setSeniority(opt.value)}
                  className={`rounded-full border px-5 py-2 font-sans text-sm font-medium transition-colors ${
                    seniority === opt.value
                      ? 'border-[var(--brand-ink)] bg-[var(--brand-ink)] text-white'
                      : 'border-[var(--brand-line)] bg-transparent text-[var(--brand-ink-muted)] hover:border-[var(--brand-ink)] hover:text-[var(--brand-ink)]'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      ),
      canAdvance: industry.trim().length >= 2,
    },
    {
      title: "Add a few core skills",
      subtitle: "Just bullet out your top skills (press Enter after each).",
      icon: <Code className="size-6" />,
      content: (
        <div className="mt-4">
          <div className="flex flex-wrap gap-2 mb-4">
            {skills.map((s, i) => (
              <span key={i} className="inline-flex items-center gap-1 rounded-full bg-[var(--brand-signal)]/10 px-3 py-1 font-mono text-sm text-[var(--brand-signal)]">
                {s}
              </span>
            ))}
          </div>
          <input
            ref={inputRef as any}
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={handleSkillKeyDown}
            placeholder="e.g. React, Python, Product Strategy..."
            className="w-full border-none bg-transparent px-0 py-3 font-serif text-2xl outline-none placeholder:text-[var(--brand-ink-muted)] text-[var(--brand-ink)]"
          />
        </div>
      ),
      canAdvance: skills.length > 0 || skillInput.length > 0,
    },
    {
      title: "The human story",
      subtitle: "Write briefly what you've done. The AI will weave it into professional bullet points later.",
      icon: <Sparkles className="size-6" />,
      content: (
        <div className="mt-4">
          <textarea
            ref={inputRef as any}
            value={background}
            onChange={(e) => setBackground(e.target.value)}
            placeholder="e.g. Built the main dashboard, migrated from Vue to React, led a team of 3..."
            className="min-h-[160px] w-full resize-none border-none bg-transparent px-0 py-3 font-serif text-xl outline-none placeholder:text-[var(--brand-ink-muted)] text-[var(--brand-ink)] leading-relaxed"
          />
          <div className="mt-6 flex items-center justify-between border-t border-[var(--brand-line)] pt-6">
            <span className="font-mono text-xs uppercase tracking-wide text-[var(--brand-ink-muted)]">Output Language</span>
            <div className="flex bg-[var(--brand-surface)] p-1 rounded-lg">
              <button 
                onClick={() => setLanguage('en')} 
                className={`px-4 py-1.5 rounded-md text-xs font-bold ${language === 'en' ? 'bg-white dark:bg-[var(--brand-ink)] dark:text-[var(--brand-paper)] shadow-sm text-black' : 'text-[var(--brand-ink-muted)] hover:text-[var(--brand-ink)] transition-colors'}`}>
                English
              </button>
              <button 
                onClick={() => setLanguage('zh')} 
                className={`px-4 py-1.5 rounded-md text-xs font-bold ${language === 'zh' ? 'bg-white dark:bg-[var(--brand-ink)] dark:text-[var(--brand-paper)] shadow-sm text-black' : 'text-[var(--brand-ink-muted)] hover:text-[var(--brand-ink)] transition-colors'}`}>
                中文
              </button>
            </div>
          </div>
        </div>
      ),
      canAdvance: background.trim().length > 5,
    }
  ];

  return (
    <PageTransition>
      <section className="min-h-screen bg-[var(--brand-paper)] flex flex-col items-center">
        
        {/* Minimalist Top Nav */}
        <header className="px-6 py-8 flex items-center justify-between max-w-3xl w-full">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-wider text-[var(--brand-ink-muted)] hover:text-[var(--brand-ink)] transition-colors"
          >
            <ArrowLeft className="size-4" /> Leave Editor
          </Link>
          <div className="font-mono text-[10px] tracking-[0.2em] px-3 py-1 bg-[var(--brand-surface)] rounded-full text-[var(--brand-ink)]">
            {pageState === 'idle' ? `STEP ${step + 1} OF ${stepsConfig.length}` : 'MAGIC TIME'}
          </div>
        </header>

        {/* Central Wizard Area */}
        <main className="flex-1 flex flex-col justify-center w-full max-w-2xl p-6">
          <div className="relative w-full">
            
            {(pageState === 'generating' || pageState === 'redirecting') ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center justify-center text-center space-y-6 py-12"
              >
                <div className="relative">
                  <div className="absolute inset-0 bg-[var(--brand-signal)] blur-3xl opacity-20 rounded-full animate-pulse object-fill w-32 h-32" />
                  <Sparkles className="size-16 text-[var(--brand-signal)] relative z-10 animate-pulse" />
                </div>
                <div>
                  <h2 className="font-serif text-3xl text-[var(--brand-ink)] mb-3">
                    {pageState === 'generating' ? 'Drafting Blueprint...' : 'Ready to refine!'}
                  </h2>
                  <p className="font-sans text-[var(--brand-ink-muted)] max-w-sm mx-auto">
                    {pageState === 'generating' 
                      ? 'The AI is structuring your raw input into a valid format.' 
                      : 'Transferring you to the canvas now.'}
                  </p>
                </div>
              </motion.div>
            ) : pageState === 'error' ? (
               <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center">
                  <div className="bg-red-50 dark:bg-red-900/10 text-[var(--status-failed)] p-6 rounded-2xl mb-6 border border-red-100 dark:border-red-900/20">
                    <p className="font-mono text-sm mb-2 uppercase">System Error</p>
                    <p>{errorText}</p>
                  </div>
                  <Button onClick={() => setPageState('idle')} variant="secondary">Try Again</Button>
               </motion.div>
            ) : (
              <AnimatePresence mode="wait">
                <motion.div
                  key={step}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, ease: 'easeOut' }}
                  className="w-full"
                >
                  <div className="mb-6 text-[var(--brand-signal)]">
                    {stepsConfig[step].icon}
                  </div>
                  <h1 className="font-serif text-3xl md:text-5xl text-[var(--brand-ink)] leading-tight mb-2">
                    {stepsConfig[step].title}
                  </h1>
                  <p className="font-sans text-base md:text-lg text-[var(--brand-ink-muted)] mb-12">
                    {stepsConfig[step].subtitle}
                  </p>
                  
                  <div className="min-h-[140px]">
                    {stepsConfig[step].content}
                  </div>

                  <div className="mt-12 flex items-center gap-4">
                    {step < stepsConfig.length - 1 ? (
                      <Button
                        size="lg"
                        onClick={handleNext}
                        disabled={!stepsConfig[step].canAdvance}
                        className="rounded-full px-8 text-sm"
                      >
                        Continue <ArrowRight className="size-4 ml-2" />
                      </Button>
                    ) : (
                      <Button
                        size="lg"
                        onClick={() => { if(skillInput) addSkill(); handleSubmit(); }}
                        disabled={!stepsConfig[step].canAdvance}
                        className="rounded-full px-8 text-sm bg-[var(--brand-signal)] text-white hover:bg-[var(--brand-signal)]/90"
                      >
                        Generate <Sparkles className="size-4 ml-2" />
                      </Button>
                    )}
                    
                    {step > 0 && (
                      <button
                        onClick={handleBack}
                        className="font-sans text-sm font-medium text-[var(--brand-ink-muted)] hover:text-[var(--brand-ink)] transition-colors"
                      >
                        Go back
                      </button>
                    )}
                    
                    {step === stepsConfig.length - 1 && stepsConfig[step].canAdvance && (
                      <span className="text-xs font-mono text-[var(--brand-ink-muted)] ml-auto hidden md:block">
                        Press Enter or Submit
                      </span>
                    )}
                  </div>
                </motion.div>
              </AnimatePresence>
            )}

          </div>
        </main>
        
        {/* Progress Bar */}
        {pageState === 'idle' && (
          <div className="h-1.5 w-full bg-[var(--brand-surface)]">
             <motion.div 
               className="h-full bg-[var(--brand-signal)]"
               initial={{ width: `${(step / stepsConfig.length) * 100}%` }}
               animate={{ width: `${((step + 1) / stepsConfig.length) * 100}%` }}
               transition={{ duration: 0.3 }}
             />
          </div>
        )}
      </section>
    </PageTransition>
  );
}
