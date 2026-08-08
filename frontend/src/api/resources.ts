import type {
  AgentRunResponse,
  ImportedFileRecord,
  JobDescriptionRecord,
  RecentResumeRecord,
  ResumeGenerationPreferences,
} from '../types';
import { postJson, postForm, requestJson } from './http';
import { getEffectiveLLMConfig, type LLMConfigPayload } from './llm';
import { loadResumes, upsertResume as localUpsert, deleteResume as localDelete, getResume as localGet } from '../lib/localStore';
import {
  deleteLocalImportedFile,
  deleteLocalJobDescription,
  getLocalImportedFile,
  getLocalJobDescription,
  listLocalImportedFiles,
  listLocalJobDescriptions,
  saveImportedFile,
  saveLocalJobDescription,
} from '../lib/personalDataStore';

// ── Agent Run (v1/v2 legacy) ──────────────────────────────────────

// ── Imports ────────────────────────────────────────────────────────

export async function importFileOnly(file: File): Promise<ImportedFileRecord> {
  const form = new FormData();
  form.append('file', file);
  const record = await postForm<ImportedFileRecord>('/agent/import-file', form, 'Import failed');
  await saveImportedFile(record);
  return record;
}

export async function listImportedFiles(limit = 50, force = false): Promise<ImportedFileRecord[]> {
  void force;
  return listLocalImportedFiles(limit);
}

export async function deleteImportedFile(importId: string): Promise<void> {
  await deleteLocalImportedFile(importId);
}

// ── Job Descriptions ──────────────────────────────────────────────

export async function listJobDescriptions(limit = 50): Promise<JobDescriptionRecord[]> {
  const local = await listLocalJobDescriptions(limit);
  try {
    const data = await requestJson<{ items: JobDescriptionRecord[] }>(
      `/agent/job-descriptions?limit=${limit}`,
      { method: 'GET' },
      'List sample job descriptions failed',
    );
    const localIds = new Set(local.map((item) => item.id));
    return [...local, ...(data.items || []).filter((item) => !localIds.has(item.id))].slice(0, limit);
  } catch {
    return local;
  }
}

export async function getJobDescription(jobDescriptionId: string): Promise<JobDescriptionRecord> {
  const local = await getLocalJobDescription(jobDescriptionId);
  if (local) return local;
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
  const now = new Date().toISOString();
  const content = params.content.trim();
  const existing = params.job_description_id ? await getLocalJobDescription(params.job_description_id) : undefined;
  const result: JobDescriptionRecord = {
    id: params.job_description_id || crypto.randomUUID(),
    title: params.title?.trim() || 'Job Description',
    char_count: content.length,
    content_preview: content.slice(0, 300),
    content_path: '',
    content,
    created_at: existing?.created_at || now,
    updated_at: now,
  };
  await saveLocalJobDescription(result);
  return result;
}

export async function deleteJobDescription(jobDescriptionId: string): Promise<void> {
  await deleteLocalJobDescription(jobDescriptionId);
}

// ── Import → Agent ────────────────────────────────────────────────

export async function runAgentFromImport(params: {
  import_id: string;
  max_iterations?: number;
  use_llm?: boolean;
  llm_config?: LLMConfigPayload;
  layout_preferences?: ResumeGenerationPreferences;
}): Promise<AgentRunResponse> {
  const imported = await getLocalImportedFile(params.import_id);
  if (!imported?.raw_text) throw new Error('Imported resume text is unavailable in this browser.');
  return postJson<AgentRunResponse>(
    '/agent/run-import',
    {
      raw_text: imported.raw_text,
      file_name: imported.file_name,
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
  void force;
  return local.slice(0, limit);
}

export async function getRecentResume(resumeId: string): Promise<RecentResumeRecord> {
  const local = localGet(resumeId);
  if (local) return local;
  throw new Error('Resume not found in this browser.');
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
  void params.llm_config;
  void params.prefer_llm_html;
  const existing = params.resume_id ? localGet(params.resume_id) : null;
  const now = new Date().toISOString();
  const result = {
    id: params.resume_id || crypto.randomUUID(), title: params.title,
    status: params.status ?? 'ready', source: params.source ?? 'builder',
    tags: params.tags ?? [], resume_obj: params.resume_obj,
    output_markdown: params.output_markdown ?? '', output_html: params.output_html ?? '',
    template_name: params.template_name ?? 'modern_pro.html',
    layout_preferences: params.layout_preferences,
    resume_obj_path: '', output_markdown_path: '', output_html_path: '',
    created_at: existing?.created_at || now, updated_at: now,
  } as RecentResumeRecord;
  localUpsert(result);
  return result;
}

export async function renderRecentResume(params: {
  resume_id: string;
  llm_config?: LLMConfigPayload;
  layout_preferences?: ResumeGenerationPreferences;
}): Promise<RecentResumeRecord> {
  const existing = localGet(params.resume_id);
  if (!existing?.resume_obj) throw new Error('Resume not found in this browser.');
  const rendered = await postJson<RecentResumeRecord>(
    '/agent/render-resume',
    {
      resume_id: params.resume_id,
      resume_obj: existing.resume_obj,
      template_name: existing.template_name,
      llm_config: getEffectiveLLMConfig(params.llm_config),
      layout_preferences: params.layout_preferences,
    },
    'Render recent resume failed',
  );
  const updated = { ...existing, ...rendered, id: existing.id, updated_at: new Date().toISOString() };
  localUpsert(updated);
  return updated;
}

export async function deleteRecentResume(resumeId: string): Promise<void> {
  localDelete(resumeId);
}
