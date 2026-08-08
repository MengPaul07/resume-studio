import type { ImportedFileRecord, JobDescriptionRecord } from '../types';

const DB_NAME = 'resume-studio-personal-data';
const DB_VERSION = 1;

type StoreName = 'imports' | 'jobDescriptions';

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains('imports')) {
        db.createObjectStore('imports', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('jobDescriptions')) {
        db.createObjectStore('jobDescriptions', { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('Unable to open browser storage'));
  });
}

async function runRequest<T>(storeName: StoreName, mode: IDBTransactionMode, operation: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const request = operation(transaction.objectStore(storeName));
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error('Browser storage request failed'));
    transaction.oncomplete = () => db.close();
    transaction.onerror = () => reject(transaction.error ?? new Error('Browser storage transaction failed'));
  });
}

async function listRecords<T extends { updated_at?: string; created_at: string }>(storeName: StoreName, limit: number): Promise<T[]> {
  const records = await runRequest<T[]>(storeName, 'readonly', (store) => store.getAll());
  return records
    .sort((a, b) => String(b.updated_at || b.created_at).localeCompare(String(a.updated_at || a.created_at)))
    .slice(0, Math.max(1, limit));
}

export function saveImportedFile(record: ImportedFileRecord): Promise<IDBValidKey> {
  return runRequest('imports', 'readwrite', (store) => store.put(record));
}

export function listLocalImportedFiles(limit = 50): Promise<ImportedFileRecord[]> {
  return listRecords<ImportedFileRecord>('imports', limit);
}

export function getLocalImportedFile(id: string): Promise<ImportedFileRecord | undefined> {
  return runRequest('imports', 'readonly', (store) => store.get(id));
}

export function deleteLocalImportedFile(id: string): Promise<undefined> {
  return runRequest('imports', 'readwrite', (store) => store.delete(id));
}

export function saveLocalJobDescription(record: JobDescriptionRecord): Promise<IDBValidKey> {
  return runRequest('jobDescriptions', 'readwrite', (store) => store.put(record));
}

export function listLocalJobDescriptions(limit = 50): Promise<JobDescriptionRecord[]> {
  return listRecords<JobDescriptionRecord>('jobDescriptions', limit);
}

export function getLocalJobDescription(id: string): Promise<JobDescriptionRecord | undefined> {
  return runRequest('jobDescriptions', 'readonly', (store) => store.get(id));
}

export function deleteLocalJobDescription(id: string): Promise<undefined> {
  return runRequest('jobDescriptions', 'readwrite', (store) => store.delete(id));
}
