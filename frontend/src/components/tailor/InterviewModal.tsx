import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronLeft, ChevronRight, RotateCcw, History, Play, Code2, MessageCircle, Clock, Signal } from 'lucide-react';
import { toolChat, toolSessionStart } from '../../api';
import { renderAssistantMarkdown } from '../../lib/tailor/markdown';
import { WritingPanel } from './WritingPanel';
import type { EditorQuestion, EditorMode } from './WritingPanel';
import interviewerAvatars from '../../assets/interview/interviewer-avatars.png';
import interviewerAvatarsExtra from '../../assets/interview/interviewer-avatars-extra.png';

// ── Types ──────────────────────────────────────────────────────────────

interface InterviewRecord {
  id: string;
  date: string;
  score: number;
  summary: string;
  messages: InterviewMessage[];
  report: Record<string, unknown> | null;
  sessionNum: number;
}

type InterviewAttitude = 'neutral' | 'waiting' | 'interested' | 'skeptical' | 'impatient' | 'satisfied';

interface InterviewMessage {
  role: string;
  text: string;
  blocks?: string[];
  phase?: string;
  attitude?: InterviewAttitude;
  waitSeconds?: number;
}

interface InteractionProfile {
  patience: 'low' | 'medium' | 'high';
  nudge_style: 'gentle' | 'structured' | 'skeptical' | 'pressure';
  silence_threshold_sec: number;
  max_proactive_nudges_per_question: number;
}

interface InProgressSession {
  config: InterviewConfig | null;
  messages: InterviewMessage[];
  report: Record<string, unknown> | null;
  reviewMode: boolean;
  currentRecordId: string;
  ivSessionId: string;
  updatedAt: string;
}

// ── Persistence ─────────────────────────────────────────────────────────

const HISTORY_KEY = 'interview_history';
const IN_PROGRESS_KEY = 'interview_in_progress';
const SETUP_STORAGE_KEY = 'interview_setup_last';

function loadInterviewHistory(): InterviewRecord[] {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
  catch { return []; }
}

function saveInterviewHistory(records: InterviewRecord[]) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(records));
}

function loadInProgress(): InProgressSession | null {
  try {
    const raw = localStorage.getItem(IN_PROGRESS_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

function saveInProgress(session: InProgressSession | null) {
  if (session) {
    localStorage.setItem(IN_PROGRESS_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(IN_PROGRESS_KEY);
  }
}

function loadLastSetup(): InterviewConfig | null {
  try { const s = localStorage.getItem(SETUP_STORAGE_KEY); if (s) return JSON.parse(s); }
  catch { /* ignore */ }
  return null;
}

function saveLastSetup(cfg: InterviewConfig) {
  localStorage.setItem(SETUP_STORAGE_KEY, JSON.stringify(cfg));
}

// ── Presets ─────────────────────────────────────────────────────────────

const PRESETS = [
  { id: 'li-yan', name: 'Li Yan', title: 'ByteDance Backend Bar Raiser', desc: 'Sharp, fast, and allergic to vague project claims.', bestFor: 'Backend / full-stack candidates preparing for Chinese big-tech rounds.', tags: ['Chinese', 'High pressure', 'Projects'], industries: ['internet', 'software'], rounds: 7, language: 'zh', avatarSheet: 'primary', avatarPosition: '0% 0%' },
  { id: 'maya-chen', name: 'Maya Chen', title: 'FAANG System Design Coach', desc: 'Calm, structured, and obsessed with tradeoffs.', bestFor: 'Mid-to-senior engineers practicing design and behavioral loops.', tags: ['English', 'System design', 'Behavioral'], industries: ['internet', 'software'], rounds: 6, language: 'en', avatarSheet: 'primary', avatarPosition: '50% 0%' },
  { id: 'helena-brooks', name: 'Helena Brooks', title: 'Investment Bank Risk Panelist', desc: 'Composed, numbers-first, and strict about reliability under pressure.', bestFor: 'Finance, banking, risk platform, quant engineering, and regulated systems roles.', tags: ['English', 'Finance', 'Risk'], industries: ['finance', 'regulated'], rounds: 6, language: 'en', avatarSheet: 'primary', avatarPosition: '100% 0%' },
  { id: 'qiao-lin', name: 'Qiao Lin', title: 'Campus Interview Mentor', desc: 'Friendly, patient, and good at finding fundamentals gaps.', bestFor: 'Internship, new-grad, and first serious technical interview practice.', tags: ['Chinese', 'Friendly', 'Fundamentals'], industries: ['campus', 'software'], rounds: 5, language: 'zh', avatarSheet: 'primary', avatarPosition: '0% 100%' },
  { id: 'sofia-rivera', name: 'Sofia Rivera', title: 'ML Engineering Panelist', desc: 'Balances modeling intuition with production ML discipline.', bestFor: 'ML engineer, data platform, recommendation, and applied AI roles.', tags: ['English', 'ML systems', 'MLOps'], industries: ['ai', 'software'], rounds: 6, language: 'en', avatarSheet: 'primary', avatarPosition: '50% 100%' },
  { id: 'aisha-patel', name: 'Dr. Aisha Patel', title: 'Healthcare AI Safety Reviewer', desc: 'Careful, ethical, and focused on safety-critical product judgment.', bestFor: 'Healthcare, biotech, clinical AI, data platform, and safety-critical software roles.', tags: ['English', 'Healthcare', 'Safety'], industries: ['healthcare', 'regulated', 'ai'], rounds: 6, language: 'en', avatarSheet: 'primary', avatarPosition: '100% 100%' },
  { id: 'eleanor-park', name: 'Prof. Eleanor Park', title: 'Research Faculty Interviewer', desc: 'Academic, skeptical, and deeply interested in original contribution.', bestFor: 'Research scientist, PhD, lab, applied research, and publication-heavy roles.', tags: ['English', 'Research', 'Publications'], industries: ['research', 'ai'], rounds: 7, language: 'en', avatarSheet: 'extra', avatarPosition: '0% 0%' },
  { id: 'marcus-reed', name: 'Marcus Reed', title: 'Management Consulting Case Lead', desc: 'Structured, quantitative, and relentless about clear business logic.', bestFor: 'Consulting, strategy, analytics, business operations, and PM case interviews.', tags: ['English', 'Case', 'Quant'], industries: ['consulting', 'business'], rounds: 5, language: 'en', avatarSheet: 'extra', avatarPosition: '50% 0%' },
  { id: 'priya-nair', name: 'Priya Nair', title: 'Product Growth Panelist', desc: 'Customer-obsessed, metric-driven, and sharp about prioritization.', bestFor: 'Product manager, growth, marketplace, SaaS, and product analytics roles.', tags: ['English', 'Product', 'Metrics'], industries: ['product', 'business', 'software'], rounds: 6, language: 'en', avatarSheet: 'extra', avatarPosition: '100% 0%' },
  { id: 'carlos-mendes', name: 'Carlos Mendes', title: 'Game Engine Technical Director', desc: 'Hands-on, performance-minded, and focused on real-time systems tradeoffs.', bestFor: 'Game engine, graphics, simulation, C++, tools, and interactive media roles.', tags: ['English', 'Games', 'C++'], industries: ['games', 'software'], rounds: 6, language: 'en', avatarSheet: 'extra', avatarPosition: '0% 100%' },
  { id: 'kenji-sato', name: 'Kenji Sato', title: 'Robotics Systems Reviewer', desc: 'Systems-minded, hardware-aware, and strict about real-world constraints.', bestFor: 'Robotics, autonomous systems, embedded, hardware-software integration roles.', tags: ['English', 'Robotics', 'Embedded'], industries: ['hardware', 'robotics'], rounds: 6, language: 'en', avatarSheet: 'extra', avatarPosition: '50% 100%' },
  { id: 'grace-okafor', name: 'Grace Okafor', title: 'Public Sector Digital Services Lead', desc: 'Mission-focused, accessibility-aware, and careful about stakeholder complexity.', bestFor: 'Government, nonprofit, civic tech, education, and public-service platform roles.', tags: ['English', 'Public sector', 'Accessibility'], industries: ['public', 'education', 'regulated'], rounds: 5, language: 'en', avatarSheet: 'extra', avatarPosition: '100% 100%' },
] as const;

const INDUSTRY_FILTER_IDS = ['all','internet','software','finance','healthcare','research','consulting','product','games','hardware','public','campus'] as const;

const DEFAULT_INTERACTION_PROFILE: InteractionProfile = {
  patience: 'medium',
  nudge_style: 'structured',
  silence_threshold_sec: 90,
  max_proactive_nudges_per_question: 1,
};

const INTERACTION_PROFILES: Record<string, InteractionProfile> = {
  'li-yan': { patience: 'low', nudge_style: 'pressure', silence_threshold_sec: 45, max_proactive_nudges_per_question: 1 },
  'maya-chen': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 90, max_proactive_nudges_per_question: 1 },
  'helena-brooks': { patience: 'low', nudge_style: 'skeptical', silence_threshold_sec: 60, max_proactive_nudges_per_question: 1 },
  'qiao-lin': { patience: 'high', nudge_style: 'gentle', silence_threshold_sec: 120, max_proactive_nudges_per_question: 1 },
  'sofia-rivera': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 90, max_proactive_nudges_per_question: 1 },
  'aisha-patel': { patience: 'high', nudge_style: 'gentle', silence_threshold_sec: 110, max_proactive_nudges_per_question: 1 },
  'eleanor-park': { patience: 'medium', nudge_style: 'skeptical', silence_threshold_sec: 90, max_proactive_nudges_per_question: 1 },
  'marcus-reed': { patience: 'low', nudge_style: 'pressure', silence_threshold_sec: 55, max_proactive_nudges_per_question: 1 },
  'priya-nair': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 75, max_proactive_nudges_per_question: 1 },
  'carlos-mendes': { patience: 'medium', nudge_style: 'skeptical', silence_threshold_sec: 75, max_proactive_nudges_per_question: 1 },
  'kenji-sato': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 85, max_proactive_nudges_per_question: 1 },
  'grace-okafor': { patience: 'high', nudge_style: 'gentle', silence_threshold_sec: 120, max_proactive_nudges_per_question: 1 },
};

const LENGTH_OPTION_IDS = ['micro','short','standard','deep','marathon'] as const;
const LENGTH_OPTIONS = [
  { id: 'micro' as const, rounds: 3 },
  { id: 'short' as const, rounds: 5 },
  { id: 'standard' as const, rounds: 7 },
  { id: 'deep' as const, rounds: 10 },
  { id: 'marathon' as const, rounds: 14 },
];

function hasIndustry(preset: (typeof PRESETS)[number], industry: string): boolean {
  return (preset.industries as readonly string[]).includes(industry);
}

function avatarUrl(preset: (typeof PRESETS)[number]): string {
  return preset.avatarSheet === 'extra' ? interviewerAvatarsExtra : interviewerAvatars;
}

function getInteractionProfile(presetId?: string): InteractionProfile {
  return INTERACTION_PROFILES[presetId || ''] || DEFAULT_INTERACTION_PROFILE;
}

function splitAssistantBlocks(text: string, metaBlocks?: unknown): string[] {
  if (Array.isArray(metaBlocks)) {
    const blocks = metaBlocks.map(x => String(x || '').trim()).filter(Boolean);
    if (blocks.length) return blocks;
  }
  const clean = String(text || '').trim();
  if (!clean) return [];
  if (clean.length > 900 || /Overall Score|评分|复盘|总结|报告|```/i.test(clean)) return [clean];
  const byBlank = clean.split(/\n\s*\n+/).map(x => x.trim()).filter(Boolean);
  if (byBlank.length > 1 && byBlank.length <= 4) return byBlank;
  const sentences = clean
    .split(/(?<=[。！？!?])\s+/)
    .map(x => x.trim())
    .filter(Boolean);
  if (sentences.length >= 2 && sentences.length <= 4) return sentences;
  return [clean];
}

function attitudeLabel(attitude: InterviewAttitude): string {
  const labels: Record<InterviewAttitude, string> = {
    neutral: 'Neutral',
    waiting: 'Waiting',
    interested: 'Interested',
    skeptical: 'Skeptical',
    impatient: 'Impatient',
    satisfied: 'Satisfied',
  };
  return labels[attitude] || labels.neutral;
}

function attitudeClass(attitude: InterviewAttitude): string {
  if (attitude === 'satisfied') return 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800';
  if (attitude === 'interested') return 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/30 dark:text-blue-300 dark:border-blue-800';
  if (attitude === 'impatient') return 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-800';
  if (attitude === 'skeptical') return 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-800';
  return 'bg-zinc-50 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:border-zinc-700';
}

function flattenText(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(flattenText).join(' ');
  if (typeof value === 'object') return Object.values(value as Record<string, unknown>).map(flattenText).join(' ');
  return '';
}

const RECOMMENDATION_RULES: Record<string, Array<{pattern: RegExp; points: number; reason: string}>> = {
  'li-yan': [
    {pattern: /backend|后端|distributed|分布式|microservice|微服务|database|数据库|redis|payment|支付|高并发/i, points: 4, reason: 'backend, systems, or high-concurrency signals'},
    {pattern: /字节|阿里|腾讯|大厂|china|chinese/i, points: 2, reason: 'Chinese big-tech style preparation'},
  ],
  'maya-chen': [
    {pattern: /system design|系统设计|scale|scalability|architecture|架构|distributed|availability|reliability/i, points: 5, reason: 'system design and architecture expectations'},
    {pattern: /faang|google|meta|amazon|netflix|apple|leadership/i, points: 3, reason: 'structured FAANG-style loop signals'},
  ],
  'helena-brooks': [
    {pattern: /finance|bank|trading|risk|compliance|audit|ledger|reconciliation|payment|fraud|金融|银行|风控|合规/i, points: 6, reason: 'finance, risk, compliance, or payment reliability signals'},
  ],
  'qiao-lin': [
    {pattern: /intern|internship|new grad|campus|entry level|junior|实习|校招|应届|毕业/i, points: 6, reason: 'early-career or campus interview signals'},
  ],
  'sofia-rivera': [
    {pattern: /machine learning|ml\b|model|llm|recommendation|ranking|data pipeline|feature|training|inference|模型|机器学习|推荐/i, points: 6, reason: 'ML, data, or model-production signals'},
  ],
  'aisha-patel': [
    {pattern: /health|clinical|medical|patient|biotech|hipaa|privacy|safety|healthcare|医疗|临床|患者|隐私/i, points: 6, reason: 'healthcare, privacy, or safety-critical signals'},
  ],
  'eleanor-park': [
    {pattern: /research|phd|paper|publication|conference|thesis|实验|论文|科研|博士|baseline|ablation/i, points: 6, reason: 'research, publication, or experimental rigor signals'},
  ],
  'marcus-reed': [
    {pattern: /consulting|strategy|case|market sizing|profit|operations|mckinsey|bcg|bain|咨询|战略|案例/i, points: 6, reason: 'consulting case or strategy interview signals'},
  ],
  'priya-nair': [
    {pattern: /product|pm\b|growth|activation|retention|marketplace|experiment|a\/b|用户|产品|增长|转化|留存/i, points: 6, reason: 'product, growth, or metric ownership signals'},
  ],
  'carlos-mendes': [
    {pattern: /game|unity|unreal|graphics|render|simulation|c\+\+|frame|游戏|渲染|图形|引擎/i, points: 6, reason: 'game engine, graphics, or real-time performance signals'},
  ],
  'kenji-sato': [
    {pattern: /robot|robotics|embedded|firmware|sensor|control|autonomous|hardware|iot|机器人|嵌入式|传感器|硬件/i, points: 6, reason: 'robotics, embedded, or hardware-software signals'},
  ],
  'grace-okafor': [
    {pattern: /government|public sector|nonprofit|civic|education|accessibility|wcag|privacy|公共|政府|公益|教育|无障碍/i, points: 6, reason: 'public-sector, accessibility, or civic-tech signals'},
  ],
};

function getRecommendations(resumeObj: Record<string, unknown>, targetJd?: string) {
  const source = `${targetJd || ''} ${flattenText(resumeObj)}`.toLowerCase();
  const hasJd = Boolean((targetJd || '').trim());
  const scored = PRESETS.map((preset) => {
    let score = 1;
    const reasons: string[] = [];
    for (const rule of RECOMMENDATION_RULES[preset.id] || []) {
      if (rule.pattern.test(source)) {
        score += rule.points;
        if (!reasons.includes(rule.reason)) reasons.push(rule.reason);
      }
    }
    if (preset.id === 'maya-chen' && hasJd) score += 1;
    if (preset.id === 'li-yan' && !hasJd) score += 1;
    return {
      preset,
      score,
      reason: reasons[0] || (hasJd ? 'broad match against this JD and resume' : 'solid general-purpose practice from your resume'),
    };
  });
  return scored.sort((a, b) => b.score - a.score).slice(0, 3);
}

const PRESET_CONFIGS: Record<string, any> = {
  'cn-tech-pressure':  { company:'enterprise', role:'backend',  level:'senior', style:'high_pressure', depth:'deep',     focus:{algo_ds:2,os_db:3,sys_design:1,projects:3,behavioral:1,lang_specific:0}, rounds:8, language:'zh', time_pressure:'tight' },
  'faang-sde':         { company:'faang',      role:'general',  level:'mid',    style:'balanced',      depth:'moderate', focus:{algo_ds:3,os_db:1,sys_design:2,projects:1,behavioral:2,lang_specific:0}, rounds:8, language:'en', time_pressure:'standard' },
  'cn-intern':         { company:'enterprise', role:'general',  level:'junior', style:'balanced',      depth:'shallow',  focus:{algo_ds:3,os_db:2,sys_design:0,projects:1,behavioral:1,lang_specific:0}, rounds:5, language:'zh', time_pressure:'standard' },
  'staff-arch':        { company:'faang',      role:'backend',  level:'staff',  style:'collaborative', depth:'deep',     focus:{algo_ds:0,os_db:0,sys_design:4,projects:2,behavioral:1,lang_specific:0}, rounds:8, language:'zh', time_pressure:'relaxed' },
  'startup-fullstack': { company:'startup',    role:'fullstack',level:'senior', style:'collaborative', depth:'moderate', focus:{algo_ds:1,os_db:1,sys_design:2,projects:3,behavioral:2,lang_specific:0}, rounds:8, language:'en', time_pressure:'standard' },
  'consulting-case':   { company:'consulting', role:'general',  level:'mid',    style:'balanced',      depth:'moderate', focus:{algo_ds:0,os_db:0,sys_design:0,projects:2,behavioral:4,lang_specific:0}, rounds:6, language:'en', time_pressure:'tight' },
  'ml-engineer':       { company:'faang',      role:'ml',       level:'senior', style:'balanced',      depth:'deep',     focus:{algo_ds:2,os_db:0,sys_design:2,projects:3,behavioral:1,lang_specific:0}, rounds:8, language:'en', time_pressure:'standard' },
  'quick-screen':      { company:'enterprise', role:'general',  level:'mid',    style:'balanced',      depth:'moderate', focus:{algo_ds:2,os_db:1,sys_design:0,projects:1,behavioral:0,lang_specific:0}, rounds:4, language:'zh', time_pressure:'tight' },
};

const FOCUS_KEYS = ['algo_ds','os_db','sys_design','projects','behavioral','lang_specific'] as const;
const FOCUS_LABELS: Record<string, string> = {}; // populated from i18n at render time

export interface InterviewConfig {
  preset_id?: string;
  company: string; role: string; level: string;
  style: string; depth: string;
  focus: Record<string, number>;
  rounds: number; language: string; time_pressure: string;
  length_id?: string;
  user_preferences?: string;
}

// ── Helper ──────────────────────────────────────────────────────────────

function allocateRounds(focus: Record<string, number>, total: number): Record<string, number> {
  const sum = Object.values(focus).reduce((a,b)=>a+b,0);
  if (sum===0) return {};
  const result: Record<string,number> = {};
  let allocated = 0;
  for (const k of FOCUS_KEYS) {
    result[k] = Math.max(0, Math.round((focus[k]||0)/sum*total));
    allocated += result[k];
  }
  if (allocated < total) {
    const mk = FOCUS_KEYS.reduce((a,b)=> (result[a]||0) >= (result[b]||0) ? a : b );
    result[mk] += total - allocated;
  }
  return result;
}

// ── Chip components ─────────────────────────────────────────────────────

function Badge({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button onClick={onClick}
      className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-all ${
        active ? 'border-zinc-900 bg-zinc-900 text-white shadow-sm' : 'border-zinc-200 bg-white dark:bg-zinc-800 dark:text-zinc-100 text-zinc-500 hover:border-zinc-400 dark:hover:border-zinc-500'
      }`}>{children}</button>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2">
      <span className="font-sans text-[11px] font-medium text-zinc-500 dark:text-zinc-400">{children}</span>
    </div>
  );
}

// ── Component ───────────────────────────────────────────────────────────

interface Props {
  resumeObj: Record<string, unknown>;
  targetJd?: string;
  onClose: () => void;
}

export function InterviewModal({ resumeObj, targetJd, onClose }: Props) {
  const { t } = useTranslation();
  const last = loadLastSetup();
  const [inProgress, setInProgress] = useState<InProgressSession | null>(loadInProgress);
  const defaultPreset = PRESETS.find(p => p.id === (last?.preset_id || inProgress?.config?.preset_id || 'li-yan')) || PRESETS[0];

  const [step, setStep] = useState<'setup'|'interview'>('setup');
  const [selectedPreset, setSelectedPreset] = useState<string>(defaultPreset.id);
  const [industryFilter, setIndustryFilter] = useState<string>('all');

  const defaultCfg = PRESET_CONFIGS[selectedPreset] || PRESET_CONFIGS['cn-tech-pressure'];
  const [company, setCompany] = useState(last?.company || defaultCfg.company);
  const [role, setRole] = useState(last?.role || defaultCfg.role);
  const [level, setLevel] = useState(last?.level || defaultCfg.level);
  const [style, setStyle] = useState(last?.style || defaultCfg.style);
  const [depth, setDepth] = useState(last?.depth || defaultCfg.depth);
  const [rounds, setRounds] = useState(last?.rounds || defaultCfg.rounds);
  const [lengthId, setLengthId] = useState<string>(last?.length_id || 'standard');
  const [language, setLanguage] = useState(last?.language || defaultCfg.language);
  const [timePressure, setTimePressure] = useState(last?.time_pressure || defaultCfg.time_pressure);
  const [focus, setFocus] = useState<Record<string,number>>(last?.focus || {...defaultCfg.focus});
  const [userPreferences, setUserPreferences] = useState<string>(last?.user_preferences || '');
  const [config, setConfig] = useState<InterviewConfig|null>(null);

  // Interview state
  const [messages, setMessages] = useState<InterviewMessage[]>([]);
  const [input, setInput] = useState('');
  const [running, setRunning] = useState(false);
  const [report, setReport] = useState<Record<string,unknown>|null>(null);
  const [reviewMode, setReviewMode] = useState(false);
  const [currentRecordId, setCurrentRecordId] = useState<string>('');
  const [ivSessionId, setIvSessionId] = useState<string>('');
  const [sessionReady, setSessionReady] = useState(false);
  const [history, setHistory] = useState<InterviewRecord[]>(loadInterviewHistory);
  const [showHistory, setShowHistory] = useState(false);
  const [phase, setPhase] = useState<string>('setup');
  const [attitude, setAttitude] = useState<InterviewAttitude>('neutral');
  const [waitingSeconds, setWaitingSeconds] = useState(0);
  const [nudgeCountForQuestion, setNudgeCountForQuestion] = useState(0);
  const [codingQuestion, setCodingQuestion] = useState<{problem:string;language:string;difficulty:string;time_limit?:number}|null>(null);
  const [codingEditorOpen, setCodingEditorOpen] = useState(false);
  const [manualEditorOpen, setManualEditorOpen] = useState(false);
  const [codingCode, setCodingCode] = useState('');
  const [codingQuestionKey, setCodingQuestionKey] = useState('');
  const [manualCode, setManualCode] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const filteredPresets = industryFilter === 'all'
    ? PRESETS
    : PRESETS.filter(p => hasIndustry(p, industryFilter));
  const recommendations = getRecommendations(resumeObj, targetJd);
  const activePreset = PRESETS.find(p => p.id === (config?.preset_id || selectedPreset)) || PRESETS[0];
  const interactionProfile = getInteractionProfile(activePreset.id);
  const lastAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant');
  const effectiveThreshold = Math.max(20, Math.min(240, Number(lastAssistantMessage?.waitSeconds || interactionProfile.silence_threshold_sec || 90)));

  // ── Persist in-progress session on every state change ───────────────
  useEffect(() => {
    if (step === 'interview' && messages.length > 0) {
      saveInProgress({
        config, messages, report, reviewMode, currentRecordId, ivSessionId,
        updatedAt: new Date().toISOString(),
      });
    }
  }, [step, messages, report, reviewMode, currentRecordId, ivSessionId, config]);

  // Clear in-progress when interview ends (has report and no review)
  useEffect(() => {
    if (report && !reviewMode) {
      saveInProgress(null);
    }
  }, [report, reviewMode]);

  // ── Handlers ─────────────────────────────────────────────────────────

  const handlePreset = (id: string) => {
    setSelectedPreset(id);
    const cfg = PRESET_CONFIGS[id];
    if (cfg) {
      setCompany(cfg.company); setRole(cfg.role); setLevel(cfg.level);
      setStyle(cfg.style); setDepth(cfg.depth); setRounds(cfg.rounds);
      setLanguage(cfg.language); setTimePressure(cfg.time_pressure);
      setFocus({...cfg.focus});
      return;
    }
    const preset = PRESETS.find(p => p.id === id);
    if (preset) {
      setLanguage(preset.language);
    }
  };

  const handleStartInterview = () => {
    const preset = PRESETS.find(p => p.id === selectedPreset);
    const length = LENGTH_OPTIONS.find(o => o.id === lengthId) || LENGTH_OPTIONS[2];
    const cfg: InterviewConfig = {
      company, role, level, style, depth,
      rounds: length.rounds,
      language: preset?.language ?? language,
      time_pressure: timePressure,
      focus,
      length_id: length.id,
      user_preferences: userPreferences.trim(),
    };
    if (selectedPreset) cfg.preset_id = selectedPreset;
    saveLastSetup(cfg);
    setConfig(cfg);
    setStep('interview');
    setMessages([]);
    setReport(null);
    setReviewMode(false);
    setCurrentRecordId('');
    setPhase('opening');
    setAttitude('neutral');
    setWaitingSeconds(0);
    setNudgeCountForQuestion(0);
    setCodingQuestion(null);
    setCodingEditorOpen(false);
  };

  const handleContinueInterview = () => {
    if (!inProgress) return;
    setConfig(inProgress.config);
    setMessages(inProgress.messages);
    setReport(inProgress.report);
    setReviewMode(inProgress.reviewMode);
    setCurrentRecordId(inProgress.currentRecordId);
    setIvSessionId(inProgress.ivSessionId);
    setPhase(inProgress.report ? 'review' : 'interview');
    setStep('interview');
  };

  const handleDiscardInProgress = () => {
    saveInProgress(null);
    setInProgress(null);
  };

  const createSession = () => {
    setSessionReady(false);
    setIvSessionId('');
    toolSessionStart({
      doc_type: 'resume',
      title: 'Mock Interview',
      refined_document_obj: resumeObj,
    })
      .then((d) => {
        setIvSessionId(d.session_id);
        setSessionReady(Boolean(d.session_id));
      })
      .catch(() => {
        setIvSessionId('');
        setSessionReady(false);
      });
  };

  const startNewSession = () => {
    if (messages.length===0) return;
    setMessages([]); setReport(null); setReviewMode(false); setCurrentRecordId(''); setInput('');
    setPhase('opening'); setAttitude('neutral'); setWaitingSeconds(0); setNudgeCountForQuestion(0);
    setCodingCode(''); setCodingQuestionKey(''); setManualCode('');
    setCodingQuestion(null); setCodingEditorOpen(false); setManualEditorOpen(false);
    saveInProgress(null);
    createSession();
  };

  useEffect(() => { createSession(); }, []);

  useEffect(() => {
    if (step !== 'interview') return;
    if (!sessionReady || !ivSessionId || running || messages.length > 0 || report) return;
    void sendTurn('Start the interview. Introduce yourself as the interviewer and ask the first question.', undefined, false);
  }, [step, sessionReady, ivSessionId, running, messages.length, report]);

  const sendTurn = async (text: string, forceMode?: string, appendUser = true) => {
    if (running || !ivSessionId || (appendUser && !text.trim())) return;
    const mode = forceMode || (reviewMode ? 'interview_review' : 'interview');
    const isAutoKickoff = mode === 'interview' && messages.length === 0 && (
      !appendUser || text.includes('Start the interview') || text.includes('开始面试') || text.includes('濮嬮潰')
    );
    const outboundText = isAutoKickoff ? '' : text;
    setRunning(true);
    if (appendUser && !isAutoKickoff) {
      setMessages(prev => [...prev, {role:'user', text}]);
      setInput('');
      setWaitingSeconds(0);
      setNudgeCountForQuestion(0);
      setAttitude('neutral');
    }
    try {
      const turn = await toolChat({
        doc_type:'resume', session_id:ivSessionId, message:outboundText, allow_mutation:false,
        layout_preferences:{} as any, target_jd: targetJd||'', mode,
        interview_config: config ? {
          preset_id: config.preset_id, company: config.company, role: config.role,
          level: config.level, style: config.style, depth: config.depth,
          focus: config.focus, rounds: config.rounds, language: config.language,
          time_pressure: config.time_pressure,
          user_preferences: config.user_preferences,
        } : undefined,
        onEvent: (eventName, data) => {
          if (eventName==='coding_question'&&data) {
            const q = data as any;
            const key = (q.problem || '').slice(0, 100);
            if (key !== codingQuestionKey) {
              setCodingCode('');
              setCodingQuestionKey(key);
            }
            setCodingQuestion(q);
            setCodingEditorOpen(true);
          }
        },
      });
      const interviewMeta = (turn.turn_output_bundle as Record<string, any> | undefined)?.interview;
      const asst = turn.assistant_message || '';
      const blocks = splitAssistantBlocks(asst, interviewMeta?.message_blocks);
      const nextAttitude = (interviewMeta?.attitude || '') as InterviewAttitude;
      const nextPhase = String(interviewMeta?.phase || '').trim();
      const waitSeconds = Number(interviewMeta?.next_wait_seconds || interviewMeta?.silence_threshold_sec || 0);
      if (nextPhase) setPhase(nextPhase);
      if (nextAttitude) setAttitude(nextAttitude);
      setMessages(prev => [...prev, {
        role:'assistant',
        text:asst,
        blocks,
        phase: nextPhase || phase,
        attitude: nextAttitude || attitude,
        waitSeconds: Number.isFinite(waitSeconds) && waitSeconds > 0 ? waitSeconds : undefined,
      }]);
      if (interviewMeta?.ended && turn.turn_output_bundle) {
        const bundle = turn.turn_output_bundle as Record<string,unknown>;
        const reportData = { assistant_message: asst, thinking: (bundle.thinking as string)||'' };
        setReport(reportData);
        setPhase('review');
        const scoreMatch = asst.match(/Overall Score[^0-9]*(\d+)/i) || asst.match(/(\d+)\s*\/\s*10/);
        const score = scoreMatch ? parseInt(scoreMatch[1]) : 0;
        setAttitude(score >= 7 ? 'satisfied' : 'skeptical');
        const record: InterviewRecord = {
          id: Date.now().toString(36), date: new Date().toISOString(), score,
          summary: asst.slice(0,200), messages: [...messages,{role:'assistant',text:asst,blocks}], report: reportData,
          sessionNum: loadInterviewHistory().length+1,
        };
        setCurrentRecordId(record.id);
        const updated = [record, ...loadInterviewHistory()];
        saveInterviewHistory(updated); setHistory(updated);
        saveInProgress(null);
        setInProgress(null);
      }
    } catch(err) {
      setMessages(prev => [...prev, {role:'system', text:`Error: ${err instanceof Error?err.message:'Failed'}`}]);
    } finally { setRunning(false); }
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({top:scrollRef.current.scrollHeight, behavior:'smooth'});
  }, [messages]);

  useEffect(() => {
    if (step !== 'interview' || reviewMode || report || showHistory || running) return;
    const last = messages[messages.length - 1];
    if (!last || last.role !== 'assistant') return;
    setWaitingSeconds(0);
    const timer = window.setInterval(() => {
      setWaitingSeconds(prev => prev + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [step, reviewMode, report, showHistory, running, messages.length]);

  useEffect(() => {
    if (step !== 'interview' || reviewMode || report || running || !ivSessionId) return;
    const last = messages[messages.length - 1];
    if (!last || last.role !== 'assistant') return;
    if (waitingSeconds < effectiveThreshold) return;
    if (nudgeCountForQuestion >= interactionProfile.max_proactive_nudges_per_question) {
      setAttitude(interactionProfile.patience === 'high' ? 'waiting' : 'impatient');
      return;
    }
    setNudgeCountForQuestion(prev => prev + 1);
    setAttitude(interactionProfile.patience === 'high' ? 'waiting' : 'impatient');
    void sendTurn(
      `Candidate has been silent for ${waitingSeconds} seconds. Stay in persona. Give a short, natural nudge. Do not ask a new main question unless appropriate.`,
      'interview',
      false,
    );
  }, [waitingSeconds, effectiveThreshold, ivSessionId, messages, nudgeCountForQuestion, report, reviewMode, running, step]);

  const handleClose = () => {
    if (messages.length>0 && !report) {
      // In-progress session will auto-save via useEffect
    }
    onClose();
  };

  const enterReviewMode = () => {
    if (!report) return;
    setReviewMode(true);
    setPhase('review');
    saveInProgress({
      config, messages, report, reviewMode: true, currentRecordId, ivSessionId,
      updatedAt: new Date().toISOString(),
    });
  };

  // ── Setup UI ──────────────────────────────────────────────────────────
  if (step==='setup') {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 dark:bg-black/50 backdrop-blur-sm" onClick={onClose}>
        <div className="flex h-[92vh] w-[min(1120px,94vw)] flex-col overflow-hidden rounded-xl border border-zinc-200 dark:border-zinc-600 bg-white dark:bg-[var(--brand-surface)] shadow-xl" onClick={e => e.stopPropagation()}>
          {/* Header */}
          <div className="flex shrink-0 items-center gap-3 border-b border-zinc-100 dark:border-zinc-700 px-5 py-3">
            <button onClick={onClose} className="rounded-full p-1.5 text-zinc-400 dark:text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-700 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"><ChevronLeft className="size-4" /></button>
            <div>
              <h3 className="font-sans text-sm font-semibold text-zinc-800 dark:text-zinc-200">{t('interview.setup')}</h3>
              <p className="font-sans text-[11px] text-zinc-400 dark:text-zinc-500">{t('interview.configureHint')}</p>
            </div>
          </div>

          {/* Body */}
          <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_320px] overflow-hidden">
            <div className="min-h-0 overflow-auto">
            {/* Continue session banner */}
            {inProgress && inProgress.messages && inProgress.messages.length > 0 && (
              <div className="mx-5 mt-4 rounded-xl border-2 border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-950/30 p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                    <RotateCcw className="size-4 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-sans text-sm font-semibold text-blue-900 dark:text-blue-200">{t('interview.inProgressTitle')}</p>
                    <p className="mt-0.5 font-sans text-[11px] text-blue-600/70 dark:text-blue-400/70">
                      {t('interview.inProgressDesc', {n: inProgress.messages.length, time: new Date(inProgress.updatedAt).toLocaleTimeString('zh-CN')})}
                      {inProgress.config?.preset_id ? ` • ${PRESETS.find(p => p.id === inProgress.config?.preset_id)?.name || ''}` : ''}
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <button onClick={handleContinueInterview}
                        className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 font-sans text-xs font-semibold text-white transition-all hover:bg-blue-500 active:scale-[0.98]">
                        <Play className="size-3.5" /> {t('interview.continue')}
                      </button>
                      <button onClick={handleDiscardInProgress}
                        className="rounded-lg px-3 py-2 font-sans text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors">
                        {t('interview.discard')}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Interviewers */}
            <div className="px-5 pt-4 pb-3">
              <div className="mb-4 rounded-xl border border-zinc-100 bg-zinc-50 p-3 dark:border-zinc-700 dark:bg-zinc-800/60">
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <p className="font-sans text-xs font-semibold text-zinc-900 dark:text-zinc-100">Recommended for this role</p>
                    <p className="mt-0.5 font-sans text-[11px] text-zinc-400 dark:text-zinc-500">
                      Based on your resume{targetJd ? ' and target JD' : ''}
                    </p>
                  </div>
                  <span className="rounded-full bg-white px-2 py-0.5 font-mono text-[10px] text-zinc-400 dark:bg-zinc-900 dark:text-zinc-500">top 3</span>
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {recommendations.map(({preset, reason}, idx) => {
                    const active = selectedPreset === preset.id;
                    return (
                      <button
                        key={preset.id}
                        onClick={() => {
                          setSelectedPreset(preset.id);
                          setIndustryFilter('all');
                          setLanguage(preset.language);
                        }}
                        className={`rounded-lg border p-2 text-left transition-all ${
                          active
                            ? 'border-zinc-900 bg-white shadow-sm dark:border-zinc-200 dark:bg-zinc-900'
                            : 'border-zinc-100 bg-white/70 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900/60'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="h-8 w-8 shrink-0 rounded-full border border-zinc-200 bg-cover dark:border-zinc-600"
                            style={{
                              backgroundImage: `url(${avatarUrl(preset)})`,
                              backgroundPosition: preset.avatarPosition,
                              backgroundSize: '300% 200%',
                            }}
                          />
                          <div className="min-w-0">
                            <p className="truncate font-sans text-[11px] font-semibold text-zinc-900 dark:text-zinc-100">{preset.name}</p>
                            <p className="font-mono text-[10px] text-zinc-400 dark:text-zinc-500">rank {idx + 1}</p>
                          </div>
                        </div>
                        <p className="mt-2 line-clamp-2 font-sans text-[10px] leading-relaxed text-zinc-500 dark:text-zinc-400">{reason}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mb-3 flex items-end justify-between gap-3">
                <div>
                  <p className="font-sans text-sm font-semibold text-zinc-900 dark:text-zinc-100">{t('interview.chooseInterviewer')}</p>
                  <p className="mt-0.5 font-sans text-[11px] text-zinc-400 dark:text-zinc-500">{t('interview.chooseInterviewerHint')}</p>
                </div>
                <span className="shrink-0 rounded-full border border-zinc-200 dark:border-zinc-700 px-2.5 py-1 font-mono text-[10px] text-zinc-500 dark:text-zinc-400">{t('interview.modesCount', {current: filteredPresets.length, total: PRESETS.length})}</span>
              </div>

              <div className="mb-3 flex gap-1.5 overflow-x-auto pb-1">
                {INDUSTRY_FILTER_IDS.map(filterId => {
                  const active = industryFilter === filterId;
                  return (
                    <button
                      key={filterId}
                      onClick={() => {
                        setIndustryFilter(filterId);
                        const next = filterId === 'all'
                          ? PRESETS[0]
                          : PRESETS.find(p => hasIndustry(p, filterId));
                        if (next && !hasIndustry(next, filterId) && filterId !== 'all') return;
                        if (next && (filterId !== industryFilter)) setSelectedPreset(next.id);
                      }}
                      className={`shrink-0 rounded-full border px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${
                        active
                          ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-950'
                          : 'border-zinc-200 bg-white text-zinc-500 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400'
                      }`}
                    >
                      {(t as any)(`interview.industryFilters.${filterId}`)}
                    </button>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {filteredPresets.map(p => {
                  const active = selectedPreset === p.id;
                  return (
                    <button key={p.id} onClick={() => handlePreset(p.id)}
                      className={`min-h-[142px] rounded-xl border p-3 text-left transition-all ${
                        active
                          ? 'border-zinc-900 dark:border-zinc-200 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-950 shadow-md'
                          : 'border-zinc-100 dark:border-zinc-700 bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 hover:border-zinc-300 dark:hover:border-zinc-500 hover:shadow-sm'
                      }`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 items-start gap-2.5">
                          <span
                            className={`h-11 w-11 shrink-0 rounded-full border bg-cover shadow-sm ${active ? 'border-white/30 dark:border-zinc-300' : 'border-zinc-200 dark:border-zinc-600'}`}
                            style={{
                              backgroundImage: `url(${avatarUrl(p)})`,
                              backgroundPosition: p.avatarPosition,
                              backgroundSize: '300% 200%',
                            }}
                          />
                          <div className="min-w-0">
                            <p className="font-sans text-sm font-semibold leading-tight">{p.name}</p>
                            <p className={`mt-0.5 font-sans text-[11px] leading-snug ${active ? 'text-white/70 dark:text-zinc-700' : 'text-zinc-500 dark:text-zinc-400'}`}>{p.title}</p>
                          </div>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 font-mono text-[10px] ${active ? 'bg-white/15 dark:bg-zinc-950/10' : 'bg-zinc-100 dark:bg-zinc-700 text-zinc-500 dark:text-zinc-300'}`}>{t('interview.defaultRounds', {n: p.rounds})}</span>
                      </div>
                      <p className={`mt-3 font-sans text-xs leading-relaxed ${active ? 'text-white/85 dark:text-zinc-800' : 'text-zinc-700 dark:text-zinc-300'}`}>{p.desc}</p>
                      <p className={`mt-2 line-clamp-2 font-sans text-[11px] leading-relaxed ${active ? 'text-white/55 dark:text-zinc-600' : 'text-zinc-400 dark:text-zinc-500'}`}>{p.bestFor}</p>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {p.tags.map(tag => (
                          <span key={tag} className={`rounded-full px-2 py-0.5 font-sans text-[10px] font-medium ${active ? 'bg-white/15 dark:bg-zinc-950/10 text-white/80 dark:text-zinc-700' : 'bg-zinc-50 dark:bg-zinc-700 text-zinc-500 dark:text-zinc-300'}`}>{tag}</span>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            </div>

            <aside className="min-h-0 overflow-auto border-l border-zinc-100 bg-zinc-50/70 p-4 dark:border-zinc-700 dark:bg-zinc-900/30">
            <div className="mb-4 rounded-xl border border-zinc-100 dark:border-zinc-700 bg-white dark:bg-zinc-800/60 p-4">
              {(() => {
                const picked = PRESETS.find(p => p.id === selectedPreset) || PRESETS[0];
                return (
                  <div className="flex items-start gap-3">
                    <div
                      className="h-12 w-12 shrink-0 rounded-full border border-zinc-200 bg-cover shadow-sm dark:border-zinc-600"
                      style={{
                        backgroundImage: `url(${avatarUrl(picked)})`,
                        backgroundPosition: picked.avatarPosition,
                        backgroundSize: '300% 200%',
                      }}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="font-sans text-xs font-semibold text-zinc-900 dark:text-zinc-100">{t('interview.youWillMeet', {name: picked.name})}</p>
                      <p className="mt-1 font-sans text-[11px] leading-relaxed text-zinc-500 dark:text-zinc-400">{picked.bestFor}</p>
                      <div className="mt-2 flex flex-wrap gap-2 font-mono text-[10px] text-zinc-400 dark:text-zinc-500">
                        <span>{picked.language === 'zh' ? t('interview.chineseInterview') : t('interview.englishInterview')}</span>
                        <span>{t('interview.plannedRounds', {n: (LENGTH_OPTIONS.find(o => o.id === lengthId) || LENGTH_OPTIONS[2]).rounds})}</span>
                        {targetJd && <span>{t('interview.jdAware')}</span>}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            <div className="mb-4 space-y-4 rounded-xl border border-zinc-100 dark:border-zinc-700 bg-white dark:bg-zinc-800 p-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-sans text-xs font-semibold text-zinc-900 dark:text-zinc-100">{t('interview.interviewLength')}</p>
                  <span className="font-mono text-[10px] text-zinc-400 dark:text-zinc-500">
                    {t('interview.roundsCount', {n: (LENGTH_OPTIONS.find(o => o.id === lengthId) || LENGTH_OPTIONS[2]).rounds})}
                  </span>
                </div>
                <div className="grid grid-cols-5 gap-1.5">
                  {LENGTH_OPTIONS.map(option => {
                    const active = lengthId === option.id;
                    return (
                      <button
                        key={option.id}
                        onClick={() => {
                          setLengthId(option.id);
                          setRounds(option.rounds);
                        }}
                        className={`rounded-lg border px-2 py-2 text-center transition-all ${
                          active
                            ? 'border-zinc-900 bg-zinc-900 text-white dark:border-zinc-200 dark:bg-zinc-100 dark:text-zinc-950'
                            : 'border-zinc-100 bg-zinc-50 text-zinc-500 hover:border-zinc-300 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400'
                        }`}
                      >
                        <p className="font-sans text-[11px] font-semibold">{(t as any)(`interview.lengthOptions.${option.id}.label`)}</p>
                        <p className={`mt-0.5 font-mono text-[10px] ${active ? 'opacity-70' : 'text-zinc-400'}`}>{option.rounds}r</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-sans text-xs font-semibold text-zinc-900 dark:text-zinc-100">{t('interview.customPreference')}</p>
                  <span className="font-mono text-[10px] text-zinc-400 dark:text-zinc-500">{t('interview.sentToInterviewer')}</span>
                </div>
                <textarea
                  value={userPreferences}
                  onChange={e => setUserPreferences(e.target.value)}
                  rows={3}
                  maxLength={600}
                  placeholder={t('interview.preferencesPlaceholder')}
                  className="w-full resize-none rounded-lg border border-zinc-100 bg-zinc-50 px-3 py-2 font-sans text-xs leading-5 text-zinc-700 outline-none transition-colors placeholder:text-zinc-400 focus:border-zinc-300 focus:bg-white dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:focus:border-zinc-500"
                />
              </div>
            </div>
            <button onClick={handleStartInterview}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--brand-signal)] py-3 font-sans text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-[0.98]">
              {t('interview.startInterviewBtn')} <ChevronRight className="size-4" />
            </button>
            </aside>

          </div>

          {/* Footer */}
          <div className="hidden shrink-0 border-t border-zinc-100 dark:border-zinc-700 px-5 py-3">
            <button onClick={handleStartInterview}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[var(--brand-signal)] py-3 font-sans text-sm font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-[0.98]">
              {t('interview.startInterviewBtn')} <ChevronRight className="size-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Interview UI ──────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20 dark:bg-black/50 backdrop-blur-sm" onClick={handleClose}>
      <div className="flex h-[92vh] w-[min(1120px,94vw)] flex-col overflow-hidden rounded-xl border border-zinc-200 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] shadow-xl" onClick={e => e.stopPropagation()}>
        <div className="flex shrink-0 items-center justify-between border-b border-zinc-100 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-5 py-2.5">
          <div>
            <h2 className="font-sans text-sm font-semibold text-zinc-800 dark:text-[var(--brand-ink)]">{showHistory ? t('interview.history') : t('interview.title')}</h2>
            <p className="font-sans text-[11px] text-zinc-400 dark:text-zinc-500">
              {showHistory ? t('interview.sessions', {n: history.length}) : reviewMode ? t('interview.enterReviewMode') : report ? t('interview.completed') : running ? t('interview.running') : t('interview.sessionNum', {n: history.length+1})}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                if (codingQuestion) { setCodingEditorOpen(!codingEditorOpen); }
                else { setManualEditorOpen(!manualEditorOpen); }
              }}
              className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${
                (codingQuestion && codingEditorOpen) || (!codingQuestion && manualEditorOpen)
                  ? 'bg-zinc-100 dark:bg-[var(--brand-surface-soft)] text-zinc-800 dark:text-[var(--brand-ink)]'
                  : 'text-zinc-500 dark:text-[var(--brand-ink-muted)] hover:bg-zinc-100 dark:hover:bg-[var(--brand-surface-soft)] hover:text-zinc-700 dark:hover:text-zinc-300'
              }`}
              title={codingQuestion ? t('interview.openCoding') : t('interview.openEditor')}
            >
              <Code2 className="size-3" />
              {codingQuestion ? t('interview.problem') : t('interview.notes')}
              {codingQuestion && !codingEditorOpen && (
                <span className="ml-0.5 size-1.5 rounded-full bg-amber-400 dark:bg-amber-500" />
              )}
            </button>
            <button className="rounded-md px-2.5 py-1 text-[11px] font-medium text-zinc-500 dark:text-[var(--brand-ink-muted)] hover:bg-zinc-100 dark:hover:bg-[var(--brand-surface-soft)] hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
              onClick={() => setShowHistory(!showHistory)}>
              {showHistory ? t('interview.back') : <span className="flex items-center gap-1"><History className="size-3" /> {t('interview.history')}</span>}
            </button>
            <button className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors ${messages.length===0?'text-zinc-300 dark:text-zinc-600 cursor-not-allowed':'text-zinc-500 dark:text-[var(--brand-ink-muted)] hover:bg-zinc-100 dark:hover:bg-[var(--brand-surface-soft)] hover:text-zinc-700 dark:hover:text-zinc-300'}`}
              onClick={startNewSession} disabled={messages.length===0}>{t('interview.new')}</button>
            <button className="rounded-md p-1 text-zinc-400 dark:text-zinc-500 hover:bg-zinc-100 dark:hover:bg-[var(--brand-surface-soft)] hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors" onClick={handleClose}><ChevronLeft className="size-4" /></button>
          </div>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_260px] overflow-hidden">
        <div ref={scrollRef} className="min-h-0 overflow-auto p-4">
          {showHistory ? (
            <div className="space-y-2">
              {history.length===0 ? (
                <div className="py-12 text-center">
                  <History className="mx-auto size-8 text-zinc-300 dark:text-zinc-600" />
                  <p className="mt-3 text-[13px] text-zinc-400 dark:text-zinc-500">{t('interview.noRecords')}</p>
                  <p className="mt-1 text-[11px] text-zinc-300 dark:text-zinc-600">{t('interview.startFirst')}</p>
                </div>
              ) : (
                history.map(rec => (
                  <div key={rec.id} className="cursor-pointer rounded-xl border border-zinc-100 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] p-3.5 hover:border-zinc-300 dark:hover:border-[var(--brand-line-strong)] hover:shadow-sm transition-all"
                    onClick={() => { setMessages(rec.messages); setReport(rec.report); setCurrentRecordId(rec.id); setReviewMode(false); setShowHistory(false); }}>
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-semibold text-zinc-900 dark:text-[var(--brand-ink)]">{t('interview.sessionNum', {n: rec.sessionNum})}</span>
                      <span className={`rounded-full px-2.5 py-0.5 font-mono text-[11px] font-semibold ${
                        rec.score>=8?'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300':rec.score>=6?'bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-300':'bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300'
                      }`}>{t('interview.scoreFmt', {s: rec.score})}</span>
                    </div>
                    <p className="mt-1 font-sans text-[11px] text-zinc-400 dark:text-zinc-500">{new Date(rec.date).toLocaleString('zh-CN')}</p>
                    <p className="mt-1 line-clamp-2 text-xs text-zinc-600 dark:text-[var(--brand-ink-muted)]">{rec.summary}</p>
                  </div>
                ))
              )}
            </div>
          ) : (
          <>
          {messages.length===0 && !report && (
            <div className="rounded-xl border border-zinc-100 dark:border-[var(--brand-line)] bg-zinc-50 dark:bg-[var(--brand-surface-soft)] p-6 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-zinc-100 dark:bg-[var(--brand-surface)]">
                <MessageCircle className="size-5 text-zinc-400 dark:text-zinc-500" />
              </div>
              <p className="font-sans text-sm font-semibold text-zinc-900 dark:text-[var(--brand-ink)]">{t('interview.mockInterviewMode')}</p>
              <p className="mt-1 text-xs text-zinc-500 dark:text-[var(--brand-ink-muted)]">
                {t('interview.welcomeDesc', {jd: targetJd ? t('interview.welcomeDescJd') : ''})}
              </p>
              <div className="mt-4 flex justify-center gap-4">
                <div className="rounded-lg border border-zinc-200 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-3 py-2 text-center">
                  <p className="font-sans text-[10px] text-zinc-400 dark:text-zinc-500">{t('interview.pressEnter')}</p>
                  <p className="font-mono text-[10px] font-semibold text-zinc-600 dark:text-[var(--brand-ink-muted)]">{t('interview.toSend')}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-3 py-2 text-center">
                  <p className="font-sans text-[10px] text-zinc-400 dark:text-zinc-500">{t('interview.sayEnd')}</p>
                  <p className="font-mono text-[10px] font-semibold text-zinc-600 dark:text-[var(--brand-ink-muted)]">{t('interview.toFinish')}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)] px-3 py-2 text-center">
                  <p className="font-sans text-[10px] text-zinc-400 dark:text-zinc-500">{t('interview.shiftEnter')}</p>
                  <p className="font-mono text-[10px] font-semibold text-zinc-600 dark:text-[var(--brand-ink-muted)]">{t('interview.newLine')}</p>
                </div>
              </div>
            </div>
          )}
          <div className="space-y-3 text-[13px] leading-6">
            {messages.map((m, i) => (
              <div key={i} className={m.role==='user'?'flex justify-end':'flex justify-start'}>
                <span className={`inline-block max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap ${
                  m.role==='user'
                    ? 'bg-zinc-900 dark:bg-zinc-700 text-white dark:text-white'
                    : m.role==='system'
                      ? 'bg-zinc-100 dark:bg-[var(--brand-surface-soft)] text-zinc-400 dark:text-zinc-500 text-[11px]'
                      : 'bg-zinc-50 dark:bg-[var(--brand-surface-soft)] border border-zinc-200 dark:border-[var(--brand-line)] text-zinc-800 dark:text-[var(--brand-ink)]'
                }`}>
                  {m.role==='assistant'
                    ? (m.blocks && m.blocks.length > 1
                      ? <div className="space-y-2">{m.blocks.map((block, bi) => <div key={bi}>{renderAssistantMarkdown(block)}</div>)}</div>
                      : renderAssistantMarkdown(m.text))
                    : m.text}
                </span>
              </div>
            ))}
            {running && (
              <div className="flex justify-start">
                <span className="inline-flex items-center gap-1 rounded-2xl border border-zinc-200 dark:border-[var(--brand-line)] bg-zinc-50 dark:bg-[var(--brand-surface-soft)] px-4 py-2.5">
                  <span className="size-1.5 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce" style={{animationDelay:'0ms'}} />
                  <span className="size-1.5 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce" style={{animationDelay:'150ms'}} />
                  <span className="size-1.5 rounded-full bg-zinc-400 dark:bg-zinc-500 animate-bounce" style={{animationDelay:'300ms'}} />
                </span>
              </div>
            )}
          </div>
          {report && (
            <div className="mt-4 rounded-xl border-2 border-zinc-900 dark:border-zinc-300 bg-zinc-50 dark:bg-[var(--brand-surface-soft)] p-5">
              <div className="mb-3 flex items-center justify-center gap-2">
                <Check className="size-4 text-emerald-600 dark:text-emerald-400" />
                <p className="font-serif text-base font-bold text-zinc-900 dark:text-[var(--brand-ink)]">{t('interview.report')}</p>
              </div>
              <div className="font-sans text-[13px] leading-6 text-zinc-700 dark:text-zinc-300">
                {renderAssistantMarkdown((report.assistant_message as string)||'')}
              </div>
              {!reviewMode && (
                <div className="mt-4 text-center">
                  <button className="rounded-xl bg-zinc-900 dark:bg-zinc-700 dark:text-white px-5 py-2.5 font-sans text-xs font-semibold text-white hover:bg-zinc-800 dark:hover:bg-zinc-600 transition-colors"
                    onClick={enterReviewMode}>{t('interview.enterReviewMode')}</button>
                  <p className="mt-1.5 font-sans text-[11px] text-zinc-400 dark:text-zinc-500">{t('interview.discussCoach')}</p>
                </div>
              )}
            </div>
          )}
          </>
          )}
        </div>

        {!showHistory && (
          <aside className="hidden min-h-0 border-l border-zinc-100 bg-zinc-50/70 p-4 dark:border-[var(--brand-line)] dark:bg-[var(--brand-surface-soft)] md:block">
            <div className="flex flex-col items-center text-center">
              <span
                className="h-20 w-20 rounded-full border border-zinc-200 bg-cover shadow-sm dark:border-zinc-600"
                style={{
                  backgroundImage: `url(${avatarUrl(activePreset)})`,
                  backgroundPosition: activePreset.avatarPosition,
                  backgroundSize: '300% 200%',
                }}
              />
              <p className="mt-3 font-sans text-sm font-semibold text-zinc-900 dark:text-[var(--brand-ink)]">{activePreset.name}</p>
              <p className="mt-1 font-sans text-[11px] leading-snug text-zinc-500 dark:text-zinc-400">{activePreset.title}</p>
            </div>
            <div className="mt-5 space-y-2">
              <div className={`rounded-lg border px-3 py-2 ${attitudeClass(attitude)}`}>
                <p className="font-sans text-[10px] uppercase tracking-[0.08em] opacity-70">Attitude</p>
                <p className="mt-0.5 font-sans text-xs font-semibold">{attitudeLabel(attitude)}</p>
              </div>
              <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900">
                <p className="font-sans text-[10px] uppercase tracking-[0.08em] text-zinc-400">Phase</p>
                <p className="mt-0.5 truncate font-sans text-xs font-semibold text-zinc-700 dark:text-zinc-200">{phase || 'interview'}</p>
              </div>
              <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900">
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 font-sans text-[10px] uppercase tracking-[0.08em] text-zinc-400"><Clock className="size-3" /> Waiting</span>
                  <span className="font-mono text-[10px] text-zinc-400">{effectiveThreshold}s</span>
                </div>
                <p className="mt-0.5 font-mono text-sm font-semibold text-zinc-700 dark:text-zinc-200">{waitingSeconds}s</p>
              </div>
              <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900">
                <p className="flex items-center gap-1.5 font-sans text-[10px] uppercase tracking-[0.08em] text-zinc-400"><Signal className="size-3" /> JD-aware</p>
                <p className="mt-0.5 font-sans text-xs font-semibold text-zinc-700 dark:text-zinc-200">{targetJd ? 'Enabled' : 'No target JD'}</p>
              </div>
            </div>
          </aside>
        )}
        </div>

        {!showHistory && (!report || reviewMode) && (
          <div className="shrink-0 border-t border-zinc-100 dark:border-[var(--brand-line)] bg-white dark:bg-[var(--brand-surface)]">
            {/* Pending coding question indicator */}
            {codingQuestion && !codingEditorOpen && (
              <button
                onClick={() => setCodingEditorOpen(true)}
                className="flex w-full items-center gap-2 border-b border-amber-100 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/30 px-4 py-2 text-left transition-colors hover:bg-amber-50 dark:hover:bg-amber-950/50"
              >
                <Code2 className="size-3.5 text-amber-500" />
                <span className="flex-1 font-sans text-[11px] font-medium text-amber-800 dark:text-amber-300 truncate">
                  {t('interview.codingPending', {d: codingQuestion.difficulty})}
                </span>
                <span className="font-mono text-[10px] text-amber-500 dark:text-amber-400">{t('interview.openArrow')}</span>
              </button>
            )}
            <div className="p-3">
            <div className="flex gap-2">
              <textarea value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key==='Enter'&&!e.shiftKey) {
                    e.preventDefault();
                    if (!running) sendTurn(input);
                  }
                }}
                placeholder={reviewMode ? t('interview.askCoach') : messages.length===0 ? t('interview.typeToStart') : t('interview.yourAnswer')}
                rows={1}
                className="flex-1 resize-none rounded-xl border border-zinc-200 dark:border-[var(--brand-line)] bg-zinc-50 dark:bg-[var(--brand-surface-soft)] px-4 py-2.5 font-sans text-sm outline-none transition-colors focus:border-zinc-400 dark:focus:border-zinc-500 focus:bg-white dark:focus:bg-[var(--brand-surface)]"
                disabled={!sessionReady} />
              <button className="shrink-0 rounded-lg bg-[var(--brand-signal)] px-5 py-2.5 font-sans text-xs font-semibold text-white shadow-sm transition-all hover:brightness-110 active:scale-[0.97] disabled:opacity-30"
                onClick={() => sendTurn(input)} disabled={running || !sessionReady || !input.trim()}>{t('interview.send')}</button>
            </div>
          </div>
          </div>
        )}
        {codingEditorOpen && codingQuestion && (
          <WritingPanel
            mode="code"
            question={codingQuestion as EditorQuestion}
            initialCode={codingCode}
            onCodeChange={setCodingCode}
            submitLabel={t('interview.submitSolution')}
            onSubmit={(code, lang) => {
              setCodingEditorOpen(false);
              setCodingQuestion(null);
              setCodingCode('');
              setCodingQuestionKey('');
              const formatted = '```' + (lang || 'python') + '\n' + code + '\n```';
              setTimeout(() => sendTurn(formatted), 0);
            }}
            onClose={() => setCodingEditorOpen(false)} />
        )}
        {manualEditorOpen && (
          <WritingPanel
            mode="write"
            question={{ problem: t('interview.writeHere') }}
            initialCode={manualCode}
            onCodeChange={setManualCode}
            title={t('interview.notes')}
            submitLabel={t('interview.send')}
            placeholder={t('interview.startWriting')}
            onSubmit={(text) => {
              setManualEditorOpen(false);
              setManualCode('');
              sendTurn(text);
            }}
            onClose={() => setManualEditorOpen(false)} />
        )}
      </div>
    </div>
  );
}
