import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronLeft, ChevronRight, RotateCcw, History, Play, Code2, MessageCircle, Clock, Signal, Send, X, GripHorizontal } from 'lucide-react';
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-go';
import 'prismjs/themes/prism.css';
import { toolChat, toolSessionStart } from '../../api';
import { renderAssistantMarkdown } from '../../lib/tailor/markdown';
import { WritingPanel } from './WritingPanel';
import { postJson } from '../../api';
import type { EditorQuestion, EditorMode } from './WritingPanel';
import { Button } from '../ui/button';
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
  resumeId: string;
  targetJdId?: string;
  targetJdTitle?: string;
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
  resumeId: string;
  updatedAt: string;
}

// ── Persistence ─────────────────────────────────────────────────────────

const SETUP_STORAGE_KEY = 'interview_setup_last';

function historyKey(resumeId: string) { return `interview_history:${resumeId}`; }
function inProgressKey(resumeId: string) { return `interview_in_progress:${resumeId}`; }

function loadInterviewHistory(resumeId: string): InterviewRecord[] {
  try { return JSON.parse(localStorage.getItem(historyKey(resumeId)) || '[]'); }
  catch { return []; }
}

function saveInterviewHistory(resumeId: string, records: InterviewRecord[]) {
  localStorage.setItem(historyKey(resumeId), JSON.stringify(records));
}

function loadInProgress(resumeId: string): InProgressSession | null {
  try {
    const raw = localStorage.getItem(inProgressKey(resumeId));
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return null;
}

function saveInProgress(resumeId: string, session: InProgressSession | null) {
  if (session) {
    localStorage.setItem(inProgressKey(resumeId), JSON.stringify(session));
  } else {
    localStorage.removeItem(inProgressKey(resumeId));
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
  silence_threshold_sec: 300,
  max_proactive_nudges_per_question: 1,
};

const INTERACTION_PROFILES: Record<string, InteractionProfile> = {
  'li-yan': { patience: 'low', nudge_style: 'pressure', silence_threshold_sec: 120, max_proactive_nudges_per_question: 1 },
  'maya-chen': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 300, max_proactive_nudges_per_question: 1 },
  'helena-brooks': { patience: 'low', nudge_style: 'skeptical', silence_threshold_sec: 240, max_proactive_nudges_per_question: 1 },
  'qiao-lin': { patience: 'high', nudge_style: 'gentle', silence_threshold_sec: 600, max_proactive_nudges_per_question: 1 },
  'sofia-rivera': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 360, max_proactive_nudges_per_question: 1 },
  'aisha-patel': { patience: 'high', nudge_style: 'gentle', silence_threshold_sec: 480, max_proactive_nudges_per_question: 1 },
  'eleanor-park': { patience: 'medium', nudge_style: 'skeptical', silence_threshold_sec: 420, max_proactive_nudges_per_question: 1 },
  'marcus-reed': { patience: 'low', nudge_style: 'pressure', silence_threshold_sec: 180, max_proactive_nudges_per_question: 1 },
  'priya-nair': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 300, max_proactive_nudges_per_question: 1 },
  'carlos-mendes': { patience: 'medium', nudge_style: 'skeptical', silence_threshold_sec: 300, max_proactive_nudges_per_question: 1 },
  'kenji-sato': { patience: 'medium', nudge_style: 'structured', silence_threshold_sec: 360, max_proactive_nudges_per_question: 1 },
  'grace-okafor': { patience: 'high', nudge_style: 'gentle', silence_threshold_sec: 540, max_proactive_nudges_per_question: 1 },
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
  resumeId?: string;
  targetJd?: string;
  targetJdId?: string;
  targetJdTitle?: string;
  onClose: () => void;
  embedded?: boolean;
}

function toDisplayText(value: unknown): string {
  if (value == null) return '';
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return String(value);
  if (Array.isArray(value)) return value.map(toDisplayText).join(', ');
  if (typeof value === 'object') return Object.entries(value as Record<string,unknown>).map(([k,v]) => `${k}: ${toDisplayText(v)}`).join(' | ');
  return '';
}

function ResumePanelContent({ resumeObj }: { resumeObj: Record<string, unknown> }) {
  const sections = [
    { key: 'personalInfo', label: 'Personal Info' },
    { key: 'summary', label: 'Summary' },
    { key: 'workExperience', label: 'Work Experience' },
    { key: 'education', label: 'Education' },
    { key: 'personalProjects', label: 'Projects' },
    { key: 'research', label: 'Research' },
    { key: 'additional', label: 'Additional' },
  ];
  return (
    <>
      {sections.map(({ key, label }) => {
        const val = resumeObj[key];
        if (val == null || val === '' || (Array.isArray(val) && val.length === 0)) return null;
        return (
          <div key={key} className="rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface-soft)] p-3">
            <p className="font-sans text-[10px] font-semibold text-[var(--brand-ink-muted)] uppercase tracking-wide mb-1.5">{label}</p>
            {key === 'summary' || key === 'additional' ? (
              <p className="font-sans text-xs leading-relaxed text-[var(--brand-ink)]">{toDisplayText(val)}</p>
            ) : Array.isArray(val) ? (
              <div className="space-y-2">
                {(val as Array<Record<string,unknown>>).map((item, i) => (
                  <div key={i} className="text-xs text-[var(--brand-ink)]">
                    <p className="font-medium">{toDisplayText(item.name || item.title || item.institution || item.company || '')}</p>
                    <p className="text-[var(--brand-ink-muted)] mt-0.5">{toDisplayText(item.description || item.years || item.degree || item.role || '')}</p>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </>
  );
}

function DraggablePopup({ title, children, onClose, zoom, onZoomChange }: { title: string; children: React.ReactNode; onClose: () => void; zoom?: number; onZoomChange?: (z: number) => void }) {
  const [pos, setPos] = useState({ x: Math.max(40, window.innerWidth/2 - 320), y: 60 });
  const [size, setSize] = useState({ w: 640, h: 520 });
  const [dragging, setDragging] = useState(false);
  const [resizing, setResizing] = useState(false);
  const dragRef = useRef<{ sx: number; sy: number; px: number; py: number }>({ sx:0, sy:0, px:0, py:0 });

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (dragging) {
        setPos({ x: e.clientX - dragRef.current.sx, y: e.clientY - dragRef.current.sy });
      }
      if (resizing) {
        setSize({
          w: Math.max(360, e.clientX - dragRef.current.px),
          h: Math.max(280, e.clientY - dragRef.current.py),
        });
      }
    };
    const onMouseUp = () => { setDragging(false); setResizing(false); };
    if (dragging || resizing) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    }
    return () => { window.removeEventListener('mousemove', onMouseMove); window.removeEventListener('mouseup', onMouseUp); };
  }, [dragging, resizing]);

  return (
    <div className="fixed z-[60]" style={{ left: pos.x, top: pos.y, width: size.w, height: size.h }}>
      <div className="flex flex-col h-full rounded-xl border border-[var(--brand-line-strong)] bg-[var(--brand-surface)] shadow-2xl overflow-hidden">
        <div
          className="flex shrink-0 items-center justify-between bg-[var(--brand-surface-soft)] px-3 py-2 border-b border-[var(--brand-line)] cursor-move select-none"
          onMouseDown={e => { setDragging(true); dragRef.current = { sx: e.clientX - pos.x, sy: e.clientY - pos.y, px: pos.x, py: pos.y }; }}
        >
          <div className="flex items-center gap-2">
            <GripHorizontal className="size-3.5 text-[var(--brand-ink-muted)]" />
            <span className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">{title}</span>
          </div>
          <div className="flex items-center gap-2">
            {onZoomChange && (
              <div className="flex items-center gap-0.5">
                <button onClick={() => onZoomChange(Math.max(0.25, (zoom || 1) - 0.1))}
                  className="rounded px-1.5 py-0.5 font-mono text-[10px] text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] transition-colors">−</button>
                <span className="font-mono text-[10px] text-[var(--brand-ink-muted)] w-8 text-center">{Math.round((zoom || 1) * 100)}%</span>
                <button onClick={() => onZoomChange(Math.min(2, (zoom || 1) + 0.1))}
                  className="rounded px-1.5 py-0.5 font-mono text-[10px] text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] transition-colors">+</button>
              </div>
            )}
            <button onClick={onClose} className="rounded-full p-0.5 text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)] transition-colors">
              <X className="size-3.5" />
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-auto bg-[var(--brand-paper)]">
          <div style={zoom ? { transform: `scale(${zoom})`, transformOrigin: 'top left', width: `${100/zoom}%` } : undefined}>
            {children}
          </div>
        </div>
        <div
          className="absolute right-0 bottom-0 w-4 h-4 cursor-se-resize"
          onMouseDown={e => { e.stopPropagation(); setResizing(true); dragRef.current = { ...dragRef.current, px: e.clientX - size.w, py: e.clientY - size.h }; }}
        />
      </div>
    </div>
  );
}

export function InterviewModal({ resumeObj, resumeId, targetJd, targetJdId, targetJdTitle, onClose, embedded }: Props) {
  const { t } = useTranslation();
  const last = loadLastSetup();
  const [inProgress, setInProgress] = useState<InProgressSession | null>(() => loadInProgress(resumeId || ''));
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
  const [history, setHistory] = useState<InterviewRecord[]>(() => loadInterviewHistory(resumeId || ''));
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    setHistory(loadInterviewHistory(resumeId || ''));
    setInProgress(loadInProgress(resumeId || ''));
  }, [resumeId]);
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
  const [resumePopup, setResumePopup] = useState(false);
  const [resumeZoom, setResumeZoom] = useState(0.65);
  const [resumeHtml, setResumeHtml] = useState('');
  const [jdPopup, setJDPopup] = useState(false);
  const [codePanelOpen, setCodePanelOpen] = useState(false);
  const [editorLang, setEditorLang] = useState('python');
  const scrollRef = useRef<HTMLDivElement>(null);
  const filteredPresets = industryFilter === 'all'
    ? PRESETS
    : PRESETS.filter(p => hasIndustry(p, industryFilter));
  const recommendations = getRecommendations(resumeObj, targetJd);
  const activePreset = PRESETS.find(p => p.id === (config?.preset_id || selectedPreset)) || PRESETS[0];
  const interactionProfile = getInteractionProfile(activePreset.id);
  const lastAssistantMessage = [...messages].reverse().find(m => m.role === 'assistant');
  const effectiveThreshold = Math.max(120, Math.min(900, Number(lastAssistantMessage?.waitSeconds || interactionProfile.silence_threshold_sec || 300)));

  // ── Persist in-progress session on every state change ───────────────
  useEffect(() => {
    if (step === 'interview' && messages.length > 0) {
      saveInProgress(resumeId || '', {
        config, messages, report, reviewMode, currentRecordId, ivSessionId,
        resumeId: resumeId || '',
        updatedAt: new Date().toISOString(),
      });
    }
  }, [step, messages, report, reviewMode, currentRecordId, ivSessionId, config]);

  // Clear in-progress when interview ends (has report and no review)
  useEffect(() => {
    if (report && !reviewMode) {
      saveInProgress(resumeId || '', null);
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
    saveInProgress(resumeId || '', null);
    setInProgress(null);
  };

  const createSession = () => {
    setSessionReady(false);
    setIvSessionId('');
    toolSessionStart({
      doc_type: 'resume',
      resume_id: resumeId || '',
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
    saveInProgress(resumeId || '', null);
    createSession();
  };

  useEffect(() => { createSession(); }, []);

  // Fetch builder HTML resume when popup opens
  useEffect(() => {
    if (resumePopup && resumeObj && Object.keys(resumeObj).length > 0) {
      postJson<{html: string}>('/agent/v3/template:render', {
        resume_obj: resumeObj,
        active_style: {},
        page_count_mode: 'single-page',
        target_pages: 1,
      }, 'Render resume failed').then(d => setResumeHtml(d.html)).catch(() => {});
    }
  }, [resumePopup, resumeObj]);

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
        llm_config: { temperature: 0.5 },
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
              const starter = (q.starter_code || '') as string;
              setCodingCode(starter);
              setManualCode(starter);
              setCodingQuestionKey(key);
            }
            if (q.language) setEditorLang(String(q.language));
            setCodingQuestion(q);
            setCodingEditorOpen(true);
            setCodePanelOpen(true);
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
          sessionNum: loadInterviewHistory(resumeId || '').length+1,
          resumeId: resumeId || '',
          targetJdId: targetJdId || '',
          targetJdTitle: targetJdTitle || '',
        };
        setCurrentRecordId(record.id);
        const updated = [record, ...loadInterviewHistory(resumeId || '')];
        saveInterviewHistory(resumeId || '',updated); setHistory(updated);
        saveInProgress(resumeId || '', null);
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
    saveInProgress(resumeId || '', {
      config, messages, report, reviewMode: true, currentRecordId, ivSessionId,
      resumeId: resumeId || '',
      updatedAt: new Date().toISOString(),
    });
  };

  // ── Setup UI ──────────────────────────────────────────────────────────
  if (step==='setup') {
    return (
      <div className={embedded ? 'h-full w-full flex flex-col' : 'fixed inset-0 z-50 flex items-center justify-center bg-[var(--brand-ink)]/40 backdrop-blur-sm'} onClick={e => e.stopPropagation()}>
        <div className={embedded ? 'flex-1 flex flex-col overflow-hidden' : 'flex max-h-[92vh] w-[95vw] max-w-6xl flex-col overflow-hidden rounded-2xl border-[var(--brand-line)] bg-[var(--brand-paper)] shadow-[var(--shadow-sw-card)]'}>

          {/* Header */}
          <header className="flex shrink-0 items-center justify-between rounded-t-2xl border-b border-[var(--brand-line)] bg-[var(--brand-surface)] px-5 py-3">
            <div className="flex items-center gap-3">
              <button onClick={onClose} className="rounded-full p-1.5 text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface-soft)] hover:text-[var(--brand-ink)] transition-colors"><ChevronLeft className="size-4" /></button>
              <div>
                <h1 className="font-sans text-sm font-semibold text-[var(--brand-ink)]">{t('interview.setup')}</h1>
                <p className="font-sans text-[10px] text-[var(--brand-ink-muted)]">{t('interview.configureHint')}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => setShowHistory(!showHistory)}
                className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${showHistory ? 'bg-[var(--brand-surface)] text-[var(--brand-ink)]' : 'text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)]'}`}>
                <History className="size-3.5" /> {t('interview.history')}
              </button>
              <span className="rounded-full bg-[var(--brand-signal-soft)] px-3 py-1 font-sans text-[10px] font-medium text-[var(--brand-signal)]">{t('interview.settings')}</span>
            </div>
          </header>

          {/* Body */}
          <div className={`grid min-h-0 flex-1 overflow-hidden ${showHistory ? 'grid-cols-[1fr_280px]' : 'grid-cols-[1fr]'}`}>
            <div className="grid min-h-0 grid-cols-[1fr_340px] overflow-hidden">
            <div className="min-h-0 overflow-auto">
            {/* Continue session banner */}
            {inProgress && inProgress.messages && inProgress.messages.length > 0 && (
              <div className="mx-5 mt-4 rounded-xl border-2 border-[var(--brand-signal-soft)] bg-[var(--brand-surface-soft)] p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--brand-signal-soft)]">
                    <RotateCcw className="size-4 text-[var(--brand-signal)]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-sans text-sm font-semibold text-[var(--brand-ink)]">{t('interview.inProgressTitle')}</p>
                    <p className="mt-0.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">
                      {t('interview.inProgressDesc', {n: inProgress.messages.length, time: new Date(inProgress.updatedAt).toLocaleTimeString('zh-CN')})}
                      {inProgress.config?.preset_id ? ` • ${PRESETS.find(p => p.id === inProgress.config?.preset_id)?.name || ''}` : ''}
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                      <Button onClick={handleContinueInterview} size="sm"><Play className="size-3.5" /> {t('interview.continue')}</Button>
                      <Button onClick={handleDiscardInProgress} variant="ghost" size="sm">{t('interview.discard')}</Button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Recommended */}
            <div className="px-5 pt-4 pb-3">
              <div className="mb-4 rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface-soft)] p-4">
                <div className="mb-2 flex items-center justify-between">
                  <div>
                    <p className="font-sans text-xs font-semibold text-[var(--brand-ink)]">Recommended for this role</p>
                    <p className="mt-0.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">Based on your resume{targetJd ? ' and target JD' : ''}</p>
                  </div>
                  <span className="rounded-full bg-[var(--brand-surface)] px-2 py-0.5 font-sans text-[10px] text-[var(--brand-ink-muted)]">top 3</span>
                </div>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  {recommendations.map(({preset, reason}, idx) => {
                    const active = selectedPreset === preset.id;
                    return (
                      <button key={preset.id} onClick={() => { setSelectedPreset(preset.id); setIndustryFilter('all'); setLanguage(preset.language); }}
                        className={`rounded-lg border p-2.5 text-left transition-all ${active ? 'border-[var(--brand-signal)] bg-[var(--brand-signal-soft)] shadow-sm' : 'border-[var(--brand-line)] bg-[var(--brand-surface)] hover:border-[var(--brand-line-strong)]'}`}>
                        <div className="flex items-center gap-2">
                          <span className="h-8 w-8 shrink-0 rounded-full border border-[var(--brand-line)] bg-cover"
                            style={{ backgroundImage: `url(${avatarUrl(preset)})`, backgroundPosition: preset.avatarPosition, backgroundSize: '300% 200%' }} />
                          <div className="min-w-0">
                            <p className="truncate font-sans text-[11px] font-semibold text-[var(--brand-ink)]">{preset.name}</p>
                            <p className="font-sans text-[10px] text-[var(--brand-ink-muted)]">rank {idx + 1}</p>
                          </div>
                        </div>
                        <p className="mt-2 line-clamp-2 font-sans text-[10px] leading-relaxed text-[var(--brand-ink-muted)]">{reason}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="mb-3 flex items-end justify-between gap-3">
                <div>
                  <p className="font-sans text-sm font-semibold text-[var(--brand-ink)]">{t('interview.chooseInterviewer')}</p>
                  <p className="mt-0.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">{t('interview.chooseInterviewerHint')}</p>
                </div>
                <span className="shrink-0 rounded-full border border-[var(--brand-line)] px-2.5 py-1 font-sans text-[10px] text-[var(--brand-ink-muted)]">{t('interview.modesCount', {current: filteredPresets.length, total: PRESETS.length})}</span>
              </div>

              <div className="mb-3 flex gap-1.5 overflow-x-auto pb-1">
                {INDUSTRY_FILTER_IDS.map(filterId => {
                  const active = industryFilter === filterId;
                  return (
                    <button key={filterId} onClick={() => {
                      setIndustryFilter(filterId);
                      const next = filterId === 'all' ? PRESETS[0] : PRESETS.find(p => hasIndustry(p, filterId));
                      if (next && !hasIndustry(next, filterId) && filterId !== 'all') return;
                      if (next && (filterId !== industryFilter)) setSelectedPreset(next.id);
                    }}
                      className={`shrink-0 rounded-full border px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${active ? 'border-[var(--brand-ink)] bg-[var(--brand-ink)] text-[var(--brand-paper)]' : 'border-[var(--brand-line)] bg-[var(--brand-surface)] text-[var(--brand-ink-muted)] hover:border-[var(--brand-line-strong)]'}`}>
                      {(t as any)(`interview.industryFilters.${filterId}`)}</button>
                  );
                })}
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {filteredPresets.map(p => {
                  const active = selectedPreset === p.id;
                  return (
                    <button key={p.id} onClick={() => handlePreset(p.id)}
                      className={`min-h-[142px] rounded-xl border p-3 text-left transition-all ${active ? 'border-[var(--brand-signal)] bg-[var(--brand-signal)] text-white shadow-md' : 'border-[var(--brand-line)] bg-[var(--brand-surface)] text-[var(--brand-ink)] hover:border-[var(--brand-line-strong)] hover:shadow-sm'}`}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex min-w-0 items-start gap-2.5">
                          <span className={`h-11 w-11 shrink-0 rounded-full border bg-cover shadow-sm ${active ? 'border-white/30' : 'border-[var(--brand-line)]'}`}
                            style={{ backgroundImage: `url(${avatarUrl(p)})`, backgroundPosition: p.avatarPosition, backgroundSize: '300% 200%' }} />
                          <div className="min-w-0">
                            <p className="font-sans text-sm font-semibold leading-tight">{p.name}</p>
                            <p className={`mt-0.5 font-sans text-[11px] leading-snug ${active ? 'text-white/70' : 'text-[var(--brand-ink-muted)]'}`}>{p.title}</p>
                          </div>
                        </div>
                      </div>
                      <p className={`mt-3 font-sans text-xs leading-relaxed ${active ? 'text-white/85' : 'text-[var(--brand-ink)]'}`}>{p.desc}</p>
                      <p className={`mt-2 line-clamp-2 font-sans text-[11px] leading-relaxed ${active ? 'text-white/55' : 'text-[var(--brand-ink-muted)]'}`}>{p.bestFor}</p>
                      <div className="mt-3 flex flex-wrap gap-1.5">
                        {p.tags.map(tag => (
                          <span key={tag} className={`rounded-full px-2 py-0.5 font-sans text-[10px] font-medium ${active ? 'bg-white/15 text-white/80' : 'bg-[var(--brand-surface-soft)] text-[var(--brand-ink-muted)]'}`}>{tag}</span>
                        ))}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
            </div>

            {/* Config sidebar */}
            <aside className="min-h-0 overflow-auto border-l border-[var(--brand-line)] bg-[var(--brand-surface-soft)] p-4">
            <div className="mb-4 rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-4">
              {(() => {
                const picked = PRESETS.find(p => p.id === selectedPreset) || PRESETS[0];
                return (
                  <div className="flex items-start gap-3">
                    <span className="h-12 w-12 shrink-0 rounded-full border border-[var(--brand-line)] bg-cover shadow-sm"
                      style={{ backgroundImage: `url(${avatarUrl(picked)})`, backgroundPosition: picked.avatarPosition, backgroundSize: '300% 200%' }} />
                    <div className="min-w-0 flex-1">
                      <p className="font-sans text-xs font-semibold text-[var(--brand-ink)]">{t('interview.youWillMeet', {name: picked.name})}</p>
                      <p className="mt-1 font-sans text-[11px] leading-relaxed text-[var(--brand-ink-muted)]">{picked.bestFor}</p>
                      <div className="mt-2 flex flex-wrap gap-2 font-sans text-[10px] text-[var(--brand-ink-muted)]">
                        <span className="rounded-full bg-[var(--brand-surface-soft)] px-2 py-0.5">{picked.language === 'zh' ? t('interview.chineseInterview') : t('interview.englishInterview')}</span>
                        <span className="rounded-full bg-[var(--brand-surface-soft)] px-2 py-0.5">{t('interview.plannedRounds', {n: (LENGTH_OPTIONS.find(o => o.id === lengthId) || LENGTH_OPTIONS[2]).rounds})}</span>
                        {targetJd && <span className="rounded-full bg-[var(--brand-surface-soft)] px-2 py-0.5">{t('interview.jdAware')}</span>}
                      </div>
                    </div>
                  </div>
                );
              })()}
            </div>

            <div className="mb-4 space-y-4 rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-sans text-xs font-semibold text-[var(--brand-ink)]">{t('interview.interviewLength')}</p>
                  <span className="font-sans text-[10px] text-[var(--brand-ink-muted)]">{t('interview.roundsCount', {n: (LENGTH_OPTIONS.find(o => o.id === lengthId) || LENGTH_OPTIONS[2]).rounds})}</span>
                </div>
                <div className="grid grid-cols-5 gap-1.5">
                  {LENGTH_OPTIONS.map(option => {
                    const active = lengthId === option.id;
                    return (
                      <button key={option.id} onClick={() => { setLengthId(option.id); setRounds(option.rounds); }}
                        className={`rounded-lg border px-2 py-2 text-center transition-all ${active ? 'border-[var(--brand-signal)] bg-[var(--brand-signal)] text-white' : 'border-[var(--brand-line)] bg-[var(--brand-surface-soft)] text-[var(--brand-ink-muted)] hover:border-[var(--brand-line-strong)]'}`}>
                        <p className="font-sans text-[11px] font-semibold">{(t as any)(`interview.lengthOptions.${option.id}.label`)}</p>
                        <p className={`mt-0.5 font-sans text-[10px] ${active ? 'opacity-70' : 'text-[var(--brand-ink-muted)]'}`}>{option.rounds}r</p>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-sans text-xs font-semibold text-[var(--brand-ink)]">{t('interview.customPreference')}</p>
                  <span className="font-sans text-[10px] text-[var(--brand-ink-muted)]">{t('interview.sentToInterviewer')}</span>
                </div>
                <textarea value={userPreferences} onChange={e => setUserPreferences(e.target.value)}
                  rows={3} maxLength={600} placeholder={t('interview.preferencesPlaceholder')}
                  className="w-full resize-none rounded-lg border border-[var(--brand-line)] bg-[var(--brand-paper)] px-3 py-2 font-sans text-xs leading-5 text-[var(--brand-ink)] outline-none transition-colors placeholder:text-[var(--brand-ink-muted)] focus:border-[var(--brand-signal)] focus:shadow-[0_0_0_3px_var(--brand-signal-soft)]" />
              </div>
            </div>
            <Button onClick={handleStartInterview} size="lg" className="w-full">
              {t('interview.startInterviewBtn')} <ChevronRight className="size-4" />
            </Button>
            </aside>
            </div>

            {/* Toggleable history panel */}
            {showHistory && (
              <div className="flex flex-col border-l border-[var(--brand-line)] bg-[var(--brand-surface-soft)] min-h-0">
                <div className="flex shrink-0 items-center justify-between border-b border-[var(--brand-line)] px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <History className="size-3.5 text-[var(--brand-ink-muted)]" />
                    <span className="font-sans text-[10px] font-semibold text-[var(--brand-ink-muted)] uppercase tracking-wide">{t('interview.history')}</span>
                    <span className="font-sans text-[10px] text-[var(--brand-ink-muted)]/50">{history.length}</span>
                  </div>
                  <button onClick={() => setShowHistory(false)}
                    className="rounded-full p-0.5 text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)] transition-colors">
                    <X className="size-3.5" />
                  </button>
                </div>
                <div className="flex-1 overflow-auto p-3 space-y-2">
                  {/* In-progress pinned at top */}
                  {inProgress && inProgress.messages && inProgress.messages.length > 0 && (
                    <div
                      onClick={() => {
                        setConfig(inProgress.config); setMessages(inProgress.messages);
                        setReport(inProgress.report); setReviewMode(inProgress.reviewMode);
                        setCurrentRecordId(inProgress.currentRecordId); setIvSessionId(inProgress.ivSessionId);
                        setShowHistory(false); setStep('interview');
                        if (inProgress.report) setPhase('review');
                      }}
                      className="cursor-pointer rounded-lg border border-[var(--brand-signal)] bg-[var(--brand-signal-soft)]/30 p-2.5 hover:border-[var(--brand-signal)] hover:shadow-sm transition-all">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 rounded-full bg-[var(--status-running)] animate-pulse" />
                          <span className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">In Progress</span>
                        </div>
                        <span className="rounded-full bg-[var(--status-running)]/10 px-2 py-0.5 font-sans text-[10px] font-medium text-[var(--status-running)]">{inProgress.messages.length} msgs</span>
                      </div>
                      <p className="mt-1 font-sans text-[10px] text-[var(--brand-ink-muted)]">
                        {inProgress.config?.preset_id ? PRESETS.find(p => p.id === inProgress.config?.preset_id)?.name || 'Interview' : 'Interview'}
                        &middot; {new Date(inProgress.updatedAt).toLocaleDateString('zh-CN')}
                      </p>
                    </div>
                  )}
                  {history.length === 0 && !inProgress ? (
                    <div className="py-8 text-center">
                      <History className="mx-auto size-6 text-[var(--brand-ink-muted)]/20" />
                      <p className="mt-2 font-sans text-[11px] text-[var(--brand-ink-muted)]">{t('interview.noRecords')}</p>
                    </div>
                  ) : (
                    history.map(rec => {
                      const completed = Boolean(rec.report);
                      return (
                        <div key={rec.id}
                          onClick={() => {
                            setMessages(rec.messages); setReport(rec.report); setCurrentRecordId(rec.id);
                            setReviewMode(false); setShowHistory(false); setStep('interview');
                            setIvSessionId(''); setSessionReady(false);
                            if (rec.report) setPhase('review');
                          }}
                          className="cursor-pointer rounded-lg border border-[var(--brand-line)] bg-[var(--brand-surface)] p-2.5 hover:border-[var(--brand-line-strong)] hover:shadow-sm transition-all">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <span className={`h-1.5 w-1.5 rounded-full ${completed ? 'bg-[var(--status-done)]' : 'bg-[var(--status-running)]'}`} />
                              <span className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">#{rec.sessionNum}</span>
                            </div>
                            {completed ? (
                              <span className={`rounded-full px-2 py-0.5 font-sans text-[10px] font-semibold ${rec.score>=8?'bg-[var(--status-done)]/10 text-[var(--status-done)]':rec.score>=6?'bg-[var(--status-running)]/10 text-[var(--status-running)]':'bg-[var(--brand-surface-soft)] text-[var(--brand-ink-muted)]'}`}>
                                {t('interview.scoreFmt', {s: rec.score})}
                              </span>
                            ) : (
                              <span className="rounded-full bg-[var(--status-running)]/10 px-2 py-0.5 font-sans text-[10px] text-[var(--status-running)]">In progress</span>
                            )}
                          </div>
                          <p className="mt-1 font-sans text-[10px] text-[var(--brand-ink-muted)]">
                            {new Date(rec.date).toLocaleDateString('zh-CN')} {new Date(rec.date).toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'})}
                            {rec.targetJdTitle && <span> &middot; {rec.targetJdTitle}</span>}
                          </p>
                          <p className="mt-1 line-clamp-2 font-sans text-[10px] leading-relaxed text-[var(--brand-ink-muted)]">{rec.summary}</p>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            )}
          </div>

        </div>
      </div>
    );
  }

  // ── Interview UI ──────────────────────────────────────────────────────
  return (
    <div className={embedded ? 'h-full w-full flex flex-col' : 'fixed inset-0 z-50 flex items-center justify-center bg-[var(--brand-ink)]/40 backdrop-blur-sm'} onClick={e => e.stopPropagation()}>
      <div className={embedded ? 'flex-1 flex flex-col overflow-hidden' : 'flex h-screen w-screen flex-col overflow-hidden bg-[var(--brand-paper)] shadow-[var(--shadow-sw-card)]'}>

        {/* Header */}
        <header className="flex shrink-0 items-center justify-between border-b border-[var(--brand-line)] bg-[var(--brand-surface)] px-5 py-2.5">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2.5 rounded-lg bg-[var(--brand-surface-soft)] px-3 py-1.5">
              <span className="relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full ring-2 ring-[var(--brand-signal)]">
                <span
                  className="h-full w-full bg-cover"
                  style={{ backgroundImage: `url(${avatarUrl(activePreset)})`, backgroundPosition: activePreset.avatarPosition, backgroundSize: '300% 200%' }}
                />
              </span>
              <div>
                <p className="font-sans text-xs font-semibold text-[var(--brand-ink)]">{activePreset.name}</p>
                <p className="font-sans text-[10px] text-[var(--brand-ink-muted)]">{activePreset.title}</p>
              </div>
            </div>
            <span className="flex items-center gap-1.5 rounded-full bg-[var(--status-done)]/10 px-2.5 py-0.5 font-sans text-[10px] font-medium text-[var(--status-done)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--status-done)]" />
              {showHistory ? t('interview.history') : report ? 'Completed' : reviewMode ? 'Review Mode' : running ? t('interview.running') : 'Live'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="font-sans text-xs text-[var(--brand-ink-muted)]">
              {reviewMode ? 'Session Ended' : t('interview.sessionNum', {n: history.length+1})}
            </span>
            <Button variant="ghost" size="sm" className="text-[var(--status-failed)] hover:bg-[var(--status-failed)]/10" onClick={handleClose}>
              {report ? 'Exit Review' : t('interview.endInterview')}
            </Button>
          </div>
        </header>

        {/* Toolbar */}
        <div className="flex shrink-0 items-center justify-between border-b border-[var(--brand-line)] bg-[var(--brand-surface-soft)] px-5 py-1.5">
          <div className="flex items-center gap-4">
            <p className="font-sans text-[11px] text-[var(--brand-ink-muted)]">
              <span className="font-sans font-semibold text-[var(--brand-ink)] mr-1">Target:</span> {targetJd ? 'JD Specific' : 'General Resume'}
            </p>
            {!showHistory && (
              <p className="font-sans text-[11px] text-[var(--brand-ink-muted)]">
                <span className="font-sans font-semibold text-[var(--brand-ink)] mr-1">Round:</span> {t('interview.sessionNum', {n: history.length+1})}
              </p>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => setResumePopup(!resumePopup)}
              className={`rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${resumePopup ? 'bg-[var(--brand-surface)] text-[var(--brand-ink)]' : 'text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)]'}`}
            >Resume</button>
            <button onClick={() => setJDPopup(!jdPopup)}
              className={`rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${jdPopup ? 'bg-[var(--brand-surface)] text-[var(--brand-ink)]' : 'text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)]'}`}
            >JD</button>
            <button onClick={() => setCodePanelOpen(!codePanelOpen)}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${codePanelOpen ? 'bg-[var(--brand-surface)] text-[var(--brand-ink)]' : 'text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)]'}`}
            >Code{codingQuestion && !codePanelOpen && <span className="ml-0.5 size-1.5 rounded-sm bg-[var(--status-warning)]" />}</button>
            <div className="w-px h-4 bg-[var(--brand-line)] mx-1" />
            <button className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${showHistory ? 'bg-[var(--brand-surface)] text-[var(--brand-ink)]' : 'text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)]'}`}
              onClick={() => setShowHistory(!showHistory)}>
              <History className="size-3.5" /> {t('interview.history')}
            </button>
            <button className={`rounded-md px-2.5 py-1 font-sans text-[11px] font-medium transition-colors ${messages.length===0?'text-[var(--brand-ink-muted)] cursor-not-allowed opacity-40':'text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface)] hover:text-[var(--brand-ink)]'}`}
              onClick={startNewSession} disabled={messages.length===0}>{t('interview.new')}</button>
          </div>
        </div>

        <div className={`grid min-h-0 flex-1 overflow-hidden ${codePanelOpen ? 'grid-cols-[1fr_1fr_260px]' : 'grid-cols-[1fr_260px]'}`}>
        <div ref={scrollRef} className="min-h-0 overflow-auto">
          {showHistory ? (
            <div className="space-y-2">
              {history.length===0 ? (
                <div className="py-12 text-center">
                  <History className="mx-auto size-8 text-[var(--brand-ink-muted)]/30" />
                  <p className="mt-3 font-sans text-sm text-[var(--brand-ink-muted)]">{t('interview.noRecords')}</p>
                  <p className="mt-1 font-sans text-xs text-[var(--brand-ink-muted)]">{t('interview.startFirst')}</p>
                </div>
              ) : (
                history.map(rec => (
                  <div key={rec.id} className="cursor-pointer rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-3.5 hover:border-[var(--brand-line-strong)] hover:shadow-sm transition-all"
                    onClick={() => { setMessages(rec.messages); setReport(rec.report); setCurrentRecordId(rec.id); setReviewMode(false); setShowHistory(false); }}>
                    <div className="flex items-center justify-between">
                      <span className="font-sans text-xs font-semibold text-[var(--brand-ink)]">{t('interview.sessionNum', {n: rec.sessionNum})}</span>
                      <span className={`rounded-full px-2.5 py-0.5 font-sans text-[11px] font-semibold ${
                        rec.score>=8?'bg-[var(--status-done)]/10 text-[var(--status-done)]':rec.score>=6?'bg-[var(--status-running)]/10 text-[var(--status-running)]':'bg-[var(--brand-surface-soft)] text-[var(--brand-ink-muted)]'
                      }`}>{t('interview.scoreFmt', {s: rec.score})}</span>
                    </div>
                    <p className="mt-1 font-sans text-[11px] text-[var(--brand-ink-muted)]">
                      {new Date(rec.date).toLocaleString('zh-CN')}
                      {rec.targetJdTitle && <span> &middot; {rec.targetJdTitle}</span>}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs text-[var(--brand-ink-muted)]">{rec.summary}</p>
                  </div>
                ))
              )}
            </div>
          ) : (
          <>
          {messages.length===0 && !report && (
            <div className="mx-auto mt-12 max-w-lg rounded-2xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-8 text-center shadow-sm">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--brand-signal-soft)]">
                <MessageCircle className="size-7 text-[var(--brand-signal)]" />
              </div>
              <h2 className="mb-2 font-sans text-lg font-semibold text-[var(--brand-ink)]">{t('interview.mockInterviewMode')}</h2>
              <p className="mb-6 font-sans text-sm leading-relaxed text-[var(--brand-ink-muted)]">
                {t('interview.welcomeDesc', {jd: targetJd ? t('interview.welcomeDescJd') : ''})}
              </p>
              <div className="grid grid-cols-3 gap-3 rounded-xl bg-[var(--brand-surface-soft)] p-4">
                <div>
                  <p className="font-sans text-[10px] font-semibold text-[var(--brand-ink-muted)] uppercase tracking-wide">{t('interview.pressEnter')}</p>
                  <p className="mt-0.5 font-sans text-xs font-medium text-[var(--brand-ink)]">{t('interview.toSend')}</p>
                </div>
                <div>
                  <p className="font-sans text-[10px] font-semibold text-[var(--brand-ink-muted)] uppercase tracking-wide">{t('interview.sayEnd')}</p>
                  <p className="mt-0.5 font-sans text-xs font-medium text-[var(--brand-ink)]">{t('interview.toFinish')}</p>
                </div>
                <div>
                  <p className="font-sans text-[10px] font-semibold text-[var(--brand-ink-muted)] uppercase tracking-wide">{t('interview.shiftEnter')}</p>
                  <p className="mt-0.5 font-sans text-xs font-medium text-[var(--brand-ink)]">{t('interview.newLine')}</p>
                </div>
              </div>
            </div>
          )}
          <div className="mx-auto w-full max-w-3xl space-y-4 px-4 py-6">
            {messages.map((m, i) => {
              if (m.role === 'system') {
                return (
                  <div key={i} className="flex justify-center py-1">
                    <span className="rounded-full bg-[var(--brand-surface-soft)] px-3 py-1 font-sans text-[10px] text-[var(--brand-ink-muted)]">{m.text}</span>
                  </div>
                );
              }
              if (m.role === 'user') {
                return (
                  <div key={i} className="flex justify-end">
                    <div className="max-w-[75%] rounded-2xl rounded-br-md bg-[var(--brand-signal)] px-4 py-3 shadow-sm">
                      <p className="font-sans text-sm leading-relaxed text-white whitespace-pre-wrap">{m.text}</p>
                    </div>
                  </div>
                );
              }
              return (
                <div key={i} className="flex justify-start gap-3">
                  <span
                    className="mt-1 flex h-8 w-8 shrink-0 overflow-hidden rounded-full bg-[var(--brand-surface-soft)] ring-1 ring-[var(--brand-line)] bg-cover"
                    style={{ backgroundImage: `url(${avatarUrl(activePreset)})`, backgroundPosition: activePreset.avatarPosition, backgroundSize: '300% 200%' }}
                  />
                  <div className="max-w-[75%] rounded-2xl rounded-bl-md bg-[var(--brand-surface)] px-4 py-3 shadow-sm border border-[var(--brand-line)]">
                    <div className="mb-1 flex items-center gap-2">
                      <span className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">{activePreset.name}</span>
                    </div>
                    <div className="font-sans text-sm leading-relaxed text-[var(--brand-ink)] whitespace-pre-wrap">
                      {m.blocks && m.blocks.length > 1
                        ? <div className="space-y-3">{m.blocks.map((block, bi) => <div key={bi}>{renderAssistantMarkdown(block)}</div>)}</div>
                        : renderAssistantMarkdown(m.text)}
                    </div>
                  </div>
                </div>
              );
            })}
            {running && (
              <div className="flex justify-start gap-3">
                <span
                  className="mt-1 flex h-8 w-8 shrink-0 overflow-hidden rounded-full bg-[var(--brand-surface-soft)] ring-1 ring-[var(--brand-line)] bg-cover"
                  style={{ backgroundImage: `url(${avatarUrl(activePreset)})`, backgroundPosition: activePreset.avatarPosition, backgroundSize: '300% 200%' }}
                />
                <div className="flex items-center gap-1.5 rounded-2xl rounded-bl-md bg-[var(--brand-surface)] px-4 py-3 border border-[var(--brand-line)]">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--brand-ink-muted)]" style={{animationDelay:'0ms'}} />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--brand-ink-muted)]" style={{animationDelay:'150ms'}} />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-[var(--brand-ink-muted)]" style={{animationDelay:'300ms'}} />
                </div>
              </div>
            )}
          </div>
          {report && (
            <div className="mx-4 mt-4 rounded-2xl border-2 border-[var(--brand-signal-soft)] bg-[var(--brand-surface-soft)] p-6 max-w-3xl mx-auto">
              <div className="mb-3 flex items-center justify-center gap-2">
                <Check className="size-4 text-[var(--status-done)]" />
                <p className="font-sans text-base font-bold text-[var(--brand-ink)]">{t('interview.report')}</p>
              </div>
              <div className="font-sans text-sm leading-6 text-[var(--brand-ink)]">
                {renderAssistantMarkdown((report.assistant_message as string)||'')}
              </div>
              {!reviewMode && (
                <div className="mt-4 text-center">
                  <Button onClick={enterReviewMode}>{t('interview.enterReviewMode')}</Button>
                  <p className="mt-1.5 font-sans text-[11px] text-[var(--brand-ink-muted)]">{t('interview.discussCoach')}</p>
                </div>
              )}
            </div>
          )}
          </>
          )}
        </div>

        {/* Right Code Editor Panel */}
        {codePanelOpen && (
          <div className="flex flex-col border-l-2 border-[var(--brand-signal)] bg-[var(--brand-paper)] min-h-0">
            <div className="flex shrink-0 items-center justify-between border-b border-[var(--brand-line)] bg-[var(--brand-surface)] px-3 py-1.5">
              <div className="flex items-center gap-2">
                <span className="font-sans text-[10px] font-semibold text-[var(--brand-ink)] uppercase tracking-wide">Editor</span>
                {codingQuestion ? (
                  <span className="font-sans text-[10px] text-[var(--brand-ink-muted)]">{codingQuestion.difficulty} &middot; {codingQuestion.language}</span>
                ) : (
                  <select value={editorLang} onChange={e => setEditorLang(e.target.value)}
                    className="rounded border border-[var(--brand-line)] bg-[var(--brand-surface)] px-1.5 py-0.5 font-sans text-[10px] text-[var(--brand-ink)] outline-none focus:border-[var(--brand-signal)]">
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="java">Java</option>
                    <option value="cpp">C++</option>
                    <option value="c">C</option>
                    <option value="go">Go</option>
                  </select>
                )}
              </div>
              <div className="flex items-center gap-1">
                {codingQuestion && (
                  <button onClick={() => setCodingEditorOpen(true)}
                    className="flex items-center gap-1 rounded px-2 py-0.5 font-sans text-[10px] text-[var(--brand-signal)] hover:bg-[var(--brand-signal-soft)] transition-colors">
                    <Code2 className="size-3" /> Full Editor
                  </button>
                )}
                <button onClick={() => setManualCode('')}
                  className="rounded px-2 py-0.5 font-sans text-[10px] text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface-soft)] transition-colors">Clear</button>
                <button onClick={() => { if (manualCode.trim() && !running) { sendTurn(manualCode); setManualCode(''); } }}
                  disabled={!manualCode.trim() || running}
                  className="flex items-center gap-1 rounded px-2 py-0.5 font-sans text-[10px] font-medium text-[var(--brand-signal)] hover:bg-[var(--brand-signal-soft)] transition-colors disabled:opacity-30">
                  <Send className="size-3" /> Send
                </button>
                <button onClick={() => setCodePanelOpen(false)}
                  className="ml-1 rounded p-0.5 text-[var(--brand-ink-muted)] hover:bg-[var(--brand-surface-soft)] transition-colors">
                  <X className="size-3.5" />
                </button>
              </div>
            </div>
            <Editor
              value={manualCode}
              onValueChange={setManualCode}
              highlight={code => {
                try { return highlight(code, (languages as any)[editorLang] || languages.python, editorLang); }
                catch { return code; }
              }}
              padding={12}
              placeholder="// Draft answers, take notes, or work through problems here..."
              style={{
                fontFamily: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'SF Mono', Consolas, monospace",
                fontSize: 13,
                lineHeight: 1.6,
                minHeight: '100%',
                background: '#fafafa',
                color: '#1d1d1f',
              }}
            />
          </div>
        )}

        {/* Sidebar */}
        {!showHistory && (
          <aside className="hidden min-h-0 w-[260px] border-l border-[var(--brand-line)] bg-[var(--brand-surface-soft)] md:flex flex-col">
            <div className="flex flex-col items-center border-b border-[var(--brand-line)] px-4 py-4">
              <span
                className="h-16 w-16 shrink-0 rounded-full border-2 border-[var(--brand-line)] bg-cover shadow-sm"
                style={{
                  backgroundImage: `url(${avatarUrl(activePreset)})`,
                  backgroundPosition: activePreset.avatarPosition,
                  backgroundSize: '300% 200%',
                }}
              />
              <p className="mt-2 font-sans text-sm font-bold text-[var(--brand-ink)]">{activePreset.name}</p>
              <p className="mt-0.5 font-sans text-[10px] text-[var(--brand-ink-muted)] text-center leading-tight">{activePreset.title}</p>
            </div>
            <div className="flex-1 overflow-auto p-3 space-y-2.5">
              <div className="rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-2.5">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Signal className="size-3 text-[var(--brand-ink-muted)]" />
                  <span className="font-sans text-[10px] font-medium text-[var(--brand-ink-muted)] uppercase tracking-wide">Attitude</span>
                </div>
                <p className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">{attitudeLabel(attitude)}</p>
              </div>
              <div className="rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-2.5">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <MessageCircle className="size-3 text-[var(--brand-ink-muted)]" />
                  <span className="font-sans text-[10px] font-medium text-[var(--brand-ink-muted)] uppercase tracking-wide">Phase</span>
                </div>
                <p className="font-sans text-[11px] font-semibold text-[var(--brand-ink)] truncate">{String(phase || 'Interview').toUpperCase()}</p>
              </div>
              <div className="rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-2.5">
                <div className="flex items-center justify-between mb-0.5">
                  <div className="flex items-center gap-1.5">
                    <Clock className="size-3 text-[var(--brand-ink-muted)]" />
                    <span className="font-sans text-[10px] font-medium text-[var(--brand-ink-muted)] uppercase tracking-wide">Timer</span>
                  </div>
                  <span className="font-sans text-[10px] text-[var(--brand-ink-muted)]">{effectiveThreshold}s</span>
                </div>
                <p className="font-sans text-[11px] font-semibold">
                  <span className={waitingSeconds > effectiveThreshold * 0.8 ? 'text-[var(--status-warning)]' : 'text-[var(--brand-ink)]'}>{waitingSeconds}s</span>
                  <span className="text-[var(--brand-ink-muted)]"> elapsed</span>
                </p>
              </div>
              <div className="rounded-xl border border-[var(--brand-line)] bg-[var(--brand-surface)] p-2.5">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <RotateCcw className="size-3 text-[var(--brand-ink-muted)]" />
                  <span className="font-sans text-[10px] font-medium text-[var(--brand-ink-muted)] uppercase tracking-wide">Context</span>
                </div>
                <p className="font-sans text-[11px] font-semibold text-[var(--brand-ink)]">{targetJd ? 'JD + Resume' : 'Resume Only'}</p>
              </div>
            </div>
          </aside>
        )}
        </div>

        {/* Draggable Resume Popup */}
        {resumePopup && (
          <DraggablePopup title="Resume" onClose={() => setResumePopup(false)} zoom={resumeZoom} onZoomChange={setResumeZoom}>
            <div className="bg-white">
              {resumeHtml ? (
                <div dangerouslySetInnerHTML={{ __html: resumeHtml }} />
              ) : (
                <p className="text-[var(--brand-ink-muted)] text-xs text-center py-8">Loading resume...</p>
              )}
            </div>
          </DraggablePopup>
        )}

        {/* Draggable JD Popup */}
        {jdPopup && (
          <DraggablePopup title="Job Description" onClose={() => setJDPopup(false)}>
            <div className="font-sans text-sm">
              {targetJd ? (() => {
                const lines = targetJd.split('\n').filter(Boolean);
                const sections: {title: string; items: string[]}[] = [];
                let currentTitle = 'Overview';
                let currentItems: string[] = [];
                for (const line of lines) {
                  const trimmed = line.trim();
                  if (/^[A-Z][A-Za-z\s&/]{3,40}$/.test(trimmed) && trimmed.length < 50 && !trimmed.includes('.')) {
                    if (currentItems.length > 0) {
                      sections.push({title: currentTitle, items: [...currentItems]});
                      currentItems = [];
                    }
                    currentTitle = trimmed;
                  } else {
                    currentItems.push(trimmed);
                  }
                }
                if (currentItems.length > 0) sections.push({title: currentTitle, items: currentItems});
                if (sections.length <= 1) sections[0] = {title: '', items: lines.map(l => l.trim()).filter(Boolean)};
                return (
                  <div className="space-y-4">
                    {sections.map((sec, si) => (
                      <div key={si}>
                        {sec.title && (
                          <div className="flex items-center gap-2 mb-2">
                            <span className="h-px flex-1 bg-[var(--brand-line)]" />
                            <span className="shrink-0 font-sans text-[10px] font-semibold text-[var(--brand-signal)] uppercase tracking-wide">{sec.title}</span>
                            <span className="h-px flex-1 bg-[var(--brand-line)]" />
                          </div>
                        )}
                        <ul className="space-y-1.5">
                          {sec.items.map((item, ii) => (
                            <li key={ii} className="flex items-start gap-2 text-[13px] leading-relaxed text-[var(--brand-ink)]">
                              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--brand-signal)]/40" />
                              <span>{item}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                );
              })() : (
                <p className="text-[var(--brand-ink-muted)] text-xs text-center py-8">No JD loaded.</p>
              )}
            </div>
          </DraggablePopup>
        )}

        {!showHistory && (!report || reviewMode) && (
          <div className="shrink-0 border-t border-[var(--brand-line)] bg-[var(--brand-surface)] px-4 py-3">
            {/* Pending coding question indicator */}
            {codingQuestion && !codingEditorOpen && (
              <button
                onClick={() => setCodingEditorOpen(true)}
                className="mb-2 flex w-full items-center gap-2 rounded-lg border border-[var(--status-warning)]/20 bg-[var(--status-warning)]/5 px-4 py-2 text-left transition-colors hover:bg-[var(--status-warning)]/10"
              >
                <Code2 className="size-3.5 text-[var(--status-warning)]" />
                <span className="flex-1 font-sans text-xs font-medium text-[var(--status-warning)] truncate">
                  {t('interview.codingPending', {d: codingQuestion.difficulty})}
                </span>
                <span className="font-sans text-[10px] text-[var(--status-warning)]">{t('interview.openArrow')}</span>
              </button>
            )}
            <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-[var(--brand-line)] bg-[var(--brand-paper)] px-4 py-2 shadow-sm transition-all focus-within:border-[var(--brand-signal)] focus-within:shadow-[0_0_0_3px_var(--brand-signal-soft)]">
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
                className="flex-1 resize-none border-none bg-transparent px-0 py-1.5 font-sans text-sm outline-none focus:ring-0 text-[var(--brand-ink)] placeholder:text-[var(--brand-ink-muted)]"
                disabled={!sessionReady} />
              <button onClick={() => sendTurn(input)}
                disabled={running || !sessionReady || !input.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[var(--brand-signal)] text-white transition-all hover:brightness-110 active:scale-95 disabled:opacity-30">
                <Send className="size-4" />
              </button>
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
      </div>
    </div>
  );
}
