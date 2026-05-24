export interface ResumeBrief {
  targetRole: string;
  industry: string;
  seniority: string;
  skills: string[];
  background: string;
  language: 'en' | 'zh';
}

export function buildResumeSkeleton(params: ResumeBrief): Record<string, unknown> {
  return {
    personalInfo: {
      title: params.targetRole,
    },
    summary: params.background,
    workExperience: [
      { title: '', company: '', years: '', description: [''] },
    ],
    education: [
      { institution: '', degree: '', years: '' },
    ],
    personalProjects: [
      { name: '', description: [''] },
    ],
    research: [],
    additional: {
      technicalSkills: params.skills,
    },
    _brief: {
      target_role: params.targetRole,
      industry: params.industry,
      seniority: params.seniority,
      language: params.language,
    },
  };
}

export function buildTailorHint(params: ResumeBrief): string {
  const lang = params.language === 'zh' ? 'zh' : 'en';

  if (lang === 'zh') {
    return [
      `请基于摘要中的背景信息，为我生成详细的工作经历条目。`,
      `目标岗位：${params.targetRole}，行业：${params.industry}`,
      `请使用与${params.industry}行业相关的关键词和量化成果。`,
    ].join('\n');
  }

  return [
    `Based on my background in the summary, please generate detailed work experience entries.`,
    `Target role: ${params.targetRole}, industry: ${params.industry}.`,
    `Use industry-relevant keywords and quantify achievements where possible.`,
  ].join('\n');
}
