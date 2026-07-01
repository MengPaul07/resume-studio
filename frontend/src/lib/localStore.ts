/**
 * localStorage-based resume & chat history store.
 * Primary store for user data — no backend DB dependency.
 * Backend API is still called as fallback/backup.
 */
import type { RecentResumeRecord } from '../types';

const RESUMES_KEY = 'resume_studio_resumes';
const CHAT_KEY_PREFIX = 'resume_studio_chat_';

// ── Resume CRUD ──────────────────────────────────────────────────────

export function loadResumes(): RecentResumeRecord[] {
  try {
    const raw = localStorage.getItem(RESUMES_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveResumes(list: RecentResumeRecord[]): void {
  try {
    localStorage.setItem(RESUMES_KEY, JSON.stringify(list));
  } catch (e) {
    // localStorage full — remove oldest resumes
    if (list.length > 5) {
      const trimmed = list.slice(-5);
      try { localStorage.setItem(RESUMES_KEY, JSON.stringify(trimmed)); } catch {}
    }
  }
}

export function getResume(resumeId: string): RecentResumeRecord | null {
  return loadResumes().find(r => r.id === resumeId) ?? null;
}

export function upsertResume(record: RecentResumeRecord): void {
  const list = loadResumes();
  const idx = list.findIndex(r => r.id === record.id);
  if (idx >= 0) {
    list[idx] = { ...list[idx], ...record, updated_at: new Date().toISOString() };
  } else {
    list.unshift({ ...record, created_at: record.created_at || new Date().toISOString(), updated_at: new Date().toISOString() });
  }
  saveResumes(list);
}

export function deleteResume(resumeId: string): void {
  saveResumes(loadResumes().filter(r => r.id !== resumeId));
}

// ── Chat History (per resume) ────────────────────────────────────────

interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export function loadChatHistory(resumeId: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(CHAT_KEY_PREFIX + resumeId);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function appendChatMessage(resumeId: string, msg: ChatMessage): void {
  const history = loadChatHistory(resumeId);
  history.push({ ...msg, timestamp: msg.timestamp || new Date().toISOString() });
  // Keep last 200 messages max
  const trimmed = history.length > 200 ? history.slice(-200) : history;
  try {
    localStorage.setItem(CHAT_KEY_PREFIX + resumeId, JSON.stringify(trimmed));
  } catch {}
}

export function clearChatHistory(resumeId: string): void {
  localStorage.removeItem(CHAT_KEY_PREFIX + resumeId);
}

// ── Helpers ──────────────────────────────────────────────────────────

export function generateResumeId(): string {
  return crypto.randomUUID();
}

export function storageUsedMB(): number {
  let total = 0;
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key) total += (localStorage.getItem(key) || '').length * 2; // UTF-16
  }
  return Math.round(total / (1024 * 1024) * 100) / 100;
}
