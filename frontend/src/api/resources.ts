import type {
  AgentRunResponse,
  ImportedFileRecord,
  JobDescriptionRecord,
  RecentResumeRecord,
  ResumeGenerationPreferences,
} from '../types';
import { withListDedup, invalidateListCache } from './cache';
import { postJson, postForm, requestJson, deleteRequest } from './http';
import { getEffectiveLLMConfig, type LLMConfigPayload } from './llm';
import { loadResumes, upsertResume as localUpsert, deleteResume as localDelete, getResume as localGet } from '../lib/localStore';

// ── Agent Run (v1/v2 legacy) ──────────────────────────────────────

// ── Imports ────────────────────────────────────────────────────────

export async function importFileOnly(file: File): Promise<ImportedFileRecord> {
  const form = new FormData();
  form.append('file', file);
  return postForm<ImportedFileRecord>('/agent/import-file', form, 'Import failed');
}

export async function listImportedFiles(limit = 50, force = false): Promise<ImportedFileRecord[]> {
  const cacheKey = `imports:${limit}`;
  return withListDedup<ImportedFileRecord[]>(
    cacheKey,
    async () => {
      const data = await requestJson<{ items: ImportedFileRecord[] }>(
        `/agent/imports?limit=${limit}`,
        { method: 'GET' },
        'List imports failed',
      );
      return Array.isArray(data.items) ? data.items : [];
    },
    force,
  );
}

export async function deleteImportedFile(importId: string): Promise<void> {
  await deleteRequest(`/agent/imports/${encodeURIComponent(importId)}`, 'Delete import failed');
  invalidateListCache('imports');
}

// ── Job Descriptions ──────────────────────────────────────────────

export async function listJobDescriptions(limit = 50): Promise<JobDescriptionRecord[]> {
  const data = await requestJson<{ items: JobDescriptionRecord[] }>(
    `/agent/job-descriptions?limit=${limit}`,
    { method: 'GET' },
    'List job descriptions failed',
  );
  return Array.isArray(data.items) ? data.items : [];
}

export async function getJobDescription(jobDescriptionId: string): Promise<JobDescriptionRecord> {
  return requestJson<JobDescriptionRecord>(
    `/agent/job-descriptions/${encodeURIComponent(jobDescriptionId)}`,
    { method: 'GET' },
    'Get job description failed',
  );
}

export async function saveJobDescription(params: {
  job_description_id?: string;
  title?: string;
  content: string;
}): Promise<JobDescriptionRecord> {
  const result = await postJson<JobDescriptionRecord>(
    '/agent/job-descriptions/save',
    {
      job_description_id: params.job_description_id ?? '',
      title: params.title ?? '',
      content: params.content,
    },
    'Save job description failed',
  );
  invalidateListCache('job-descriptions');
  return result;
}

export async function deleteJobDescription(jobDescriptionId: string): Promise<void> {
  await deleteRequest(
    `/agent/job-descriptions/${encodeURIComponent(jobDescriptionId)}`,
    'Delete job description failed',
  );
  invalidateListCache('job-descriptions');
}

// ── Import → Agent ────────────────────────────────────────────────

export async function runAgentFromImport(params: {
  import_id: string;
  max_iterations?: number;
  use_llm?: boolean;
  llm_config?: LLMConfigPayload;
  layout_preferences?: ResumeGenerationPreferences;
}): Promise<AgentRunResponse> {
  return postJson<AgentRunResponse>(
    '/agent/run-import',
    {
      import_id: params.import_id,
      max_iterations: params.max_iterations ?? 2,
      use_llm: params.use_llm ?? true,
      llm_config: getEffectiveLLMConfig(params.llm_config),
      layout_preferences: params.layout_preferences,
    },
    'Build from import failed',
  );
}

// ── Recent Resumes ────────────────────────────────────────────────

export async function listRecentResumes(limit = 20, force = false): Promise<RecentResumeRecord[]> {
  const local = loadResumes();
  if (local.length > 0 && !force) return local.slice(0, limit);
  try {
    const data = await requestJson<{ items: RecentResumeRecord[] }>(
      `/agent/recent-resumes?limit=${limit}`, { method: 'GET' }, 'List recent resumes failed',
    );
    for (const item of (Array.isArray(data.items) ? data.items : [])) {
      if (!local.find(r => r.id === item.id)) localUpsert(item);
    }
    return loadResumes().slice(0, limit);
  } catch { return local.slice(0, limit); }
}

export async function getRecentResume(resumeId: string): Promise<RecentResumeRecord> {
  const local = localGet(resumeId);
  if (local) return local;
  const r = await requestJson<RecentResumeRecord>(
    `/agent/recent-resumes/${encodeURIComponent(resumeId)}`, { method: 'GET' }, 'Get recent resume failed',
  );
  localUpsert(r);
  return r;
}

export async function saveRecentResume(params: {
  resume_id?: string;
  title: string;
  status?: string;
  source?: string;
  tags?: string[];
  resume_obj: Record<string, unknown>;
  output_markdown?: string;
  output_html?: string;
  llm_config?: LLMConfigPayload;
  prefer_llm_html?: boolean;
  template_name?: string;
  layout_preferences?: ResumeGenerationPreferences;
}): Promise<RecentResumeRecord> {
  let result: RecentResumeRecord;
  try {
    result = await postJson<RecentResumeRecord>('/agent/recent-resumes/save', {
      resume_id: params.resume_id ?? '', title: params.title, status: params.status ?? 'ready',
      source: params.source ?? 'builder', tags: params.tags ?? [], resume_obj: params.resume_obj,
      output_markdown: params.output_markdown ?? '', output_html: params.output_html ?? '',
      llm_config: getEffectiveLLMConfig(params.llm_config), prefer_llm_html: params.prefer_llm_html ?? false,
      template_name: params.template_name ?? 'modern_pro.html', layout_preferences: params.layout_preferences,
    }, 'Save recent resume failed');
    invalidateListCache('recent-resumes');
  } catch {
    result = {
      id: params.resume_id || crypto.randomUUID(), title: params.title,
      status: params.status ?? 'ready', source: params.source ?? 'builder',
      tags: params.tags ?? [], resume_obj: params.resume_obj,
      output_markdown: params.output_markdown ?? '', output_html: params.output_html ?? '',
      template_name: params.template_name ?? '',
      layout_preferences: params.layout_preferences,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    } as RecentResumeRecord;
  }
  localUpsert(result);
  return result;
}

export async function renderRecentResume(params: {
  resume_id: string;
  llm_config?: LLMConfigPayload;
  layout_preferences?: ResumeGenerationPreferences;
}): Promise<RecentResumeRecord> {
  return postJson<RecentResumeRecord>(
    `/agent/recent-resumes/${encodeURIComponent(params.resume_id)}/render`,
    {
      llm_config: getEffectiveLLMConfig(params.llm_config),
      layout_preferences: params.layout_preferences,
    },
    'Render recent resume failed',
  );
}

export async function deleteRecentResume(resumeId: string): Promise<void> {
  localDelete(resumeId);
  try {
    await deleteRequest(`/agent/recent-resumes/${encodeURIComponent(resumeId)}`, 'Delete recent resume failed');
    invalidateListCache('recent-resumes');
  } catch { /* already deleted locally */ }
}
