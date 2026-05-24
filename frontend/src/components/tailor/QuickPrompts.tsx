import { useMemo } from 'react';
import { Zap } from 'lucide-react';

interface Prompt {
  label: string;
  text: string;
  reason: string;
}

/**
 * Analyze the resume object and generate contextual quick-action prompts.
 * Pure function — no backend call.
 */
function analyzeResumeForPrompts(obj: Record<string, unknown> | null | undefined, lang: string): Prompt[] {
  if (!obj || Object.keys(obj).length === 0) return [];

  const isEn = lang === 'en';
  const prompts: Prompt[] = [];
  const summary = typeof obj.summary === 'string' ? obj.summary : '';
  const workExperience = Array.isArray(obj.workExperience) ? obj.workExperience : [];
  const personalProjects = Array.isArray(obj.personalProjects) ? obj.personalProjects : [];
  const additional = (obj.additional || {}) as Record<string, unknown>;
  const skills = Array.isArray(additional.technicalSkills) ? additional.technicalSkills : [];

  if (!summary || summary.length < 60) {
    prompts.push({
      label: isEn ? 'Write Summary' : '完善 Summary',
      text: isEn ? 'Write a professional summary highlighting my core strengths and business impact.' : '帮我写一段专业的个人总结，突出核心技术优势和业务影响力。',
      reason: 'summary too short or missing',
    });
  } else if (summary.length > 300) {
    prompts.push({
      label: isEn ? 'Trim Summary' : '精简 Summary',
      text: isEn ? 'Trim my summary to under 100 words, keeping only the strongest points.' : '精简个人总结，控制在 100 字以内，保留最核心的亮点。',
      reason: 'summary too long',
    });
  }

  const hasMetrics = workExperience.some((exp: Record<string, unknown>) => {
    const descs = Array.isArray(exp.description) ? exp.description : [];
    return descs.some((d: string) => /\d+%|\d+\s*倍|\d+\s*万|\d+\s*k|\d+\s*M|\d+\s*ms|\d+\s*QPS|\d+\s*users|\d+\s*DAU/gim.test(d));
  });
  if (!hasMetrics && workExperience.length > 0) {
    prompts.push({
      label: isEn ? 'Add Metrics' : '量化成果',
      text: isEn ? 'Add quantified metrics to my work experience — percentages, numbers, scale.' : '为每段工作经历补充量化指标，让成果更具体可衡量。',
      reason: 'missing metrics',
    });
  }

  const hasWeakDesc = workExperience.some((exp: Record<string, unknown>) => {
    const descs = Array.isArray(exp.description) ? exp.description : [];
    return descs.length < 2 || descs.some((d: string) => d.length < 30);
  });
  if (hasWeakDesc) {
    prompts.push({
      label: isEn ? 'STAR Rewrite' : 'STAR 改写',
      text: isEn ? 'Rewrite my work experience using the STAR method (Situation, Task, Action, Result).' : '用 STAR 方法改写工作经历，确保每条要点有情境、行动和结果。',
      reason: 'weak descriptions',
    });
  }

  if (skills.length < 5) {
    prompts.push({
      label: isEn ? 'Add Skills' : '补充技能',
      text: isEn ? 'Suggest relevant technical and tool skills based on my work experience.' : '根据我的工作经历，帮我补充相关技术和工具技能。',
      reason: 'too few skills',
    });
  }

  if (personalProjects.length === 0) {
    prompts.push({
      label: isEn ? 'Add Projects' : '添加项目',
      text: isEn ? 'Suggest 2-3 representative projects based on my work experience.' : '根据工作经历，帮我补充 2-3 个有代表性的项目经历。',
      reason: 'missing projects',
    });
  }

  const allText = JSON.stringify(obj);
  const hasChinese = /[一-鿿]/.test(allText);
  const hasEnglish = /[a-zA-Z]{3,}/.test(allText);
  if (hasChinese && hasEnglish) {
    prompts.push({
      label: isEn ? 'Normalize Format' : '统一格式',
      text: isEn ? 'Normalize language style and punctuation for professional consistency.' : '统一简历中的语言风格和标点格式，保持专业一致性。',
      reason: 'mixed language',
    });
  }

  prompts.push({
    label: isEn ? 'ATS Check' : '风险检查',
    text: isEn ? 'Check my resume for ATS compatibility, formatting issues, and risky phrasing.' : '检查简历中是否有表达风险、格式问题或 ATS 不友好的地方。',
    reason: 'full audit',
  });

  return prompts.slice(0, 6);
}

interface Props {
  resumeObj: Record<string, unknown> | null | undefined;
  onSelect: (text: string) => void;
  disabled?: boolean;
  dynamicPrompts?: Array<{ label: string; text: string }>;
  language?: string;
}

export function QuickPrompts({ resumeObj, onSelect, disabled, dynamicPrompts, language }: Props) {
  const lang = language || 'zh';
  const staticPrompts = useMemo(() => analyzeResumeForPrompts(resumeObj, lang), [resumeObj, lang]);
  const hasDynamic = dynamicPrompts && dynamicPrompts.length > 0;

  if (staticPrompts.length === 0 && !hasDynamic) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 px-3 pt-2">
      <Zap className="size-3 text-amber-500 dark:text-amber-400 shrink-0" />

      {/* Dynamic guide prompts (from LLM — show first) */}
      {hasDynamic && dynamicPrompts!.map((p) => (
        <button
          key={`guide-${p.label}`}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(p.text)}
          className="inline-flex items-center rounded-full border border-blue-400 dark:border-blue-600 bg-blue-50 dark:bg-blue-950 px-2.5 py-1 text-[11px] font-medium text-blue-700 dark:text-blue-400 transition-colors hover:border-blue-600 dark:hover:border-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900 disabled:pointer-events-none disabled:opacity-40"
        >
          {p.label}
        </button>
      ))}

      {/* Static analysis prompts (fallback) */}
      {staticPrompts.map((p) => (
        <button
          key={p.label}
          type="button"
          disabled={disabled}
          title={p.reason}
          onClick={() => onSelect(p.text)}
          className="inline-flex items-center rounded-full border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2.5 py-0.5 text-[11px] text-slate-600 dark:text-slate-400 transition-colors hover:border-slate-400 dark:hover:border-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-200 disabled:pointer-events-none disabled:opacity-40"
        >
          {p.label}
        </button>
      ))}
    </div>
  );
}
