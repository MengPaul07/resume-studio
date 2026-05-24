const LIST_CACHE_TTL_MS = 180_000; // 3 minutes

type ListCacheEntry<T> = {
  expiresAt: number;
  value: T;
};

const listCache = new Map<string, ListCacheEntry<unknown>>();
const listInFlight = new Map<string, Promise<unknown>>();

export function readListCache<T>(key: string): T | null {
  const hit = listCache.get(key);
  if (!hit) return null;
  if (Date.now() > hit.expiresAt) {
    listCache.delete(key);
    return null;
  }
  return hit.value as T;
}

export function writeListCache<T>(key: string, value: T): void {
  listCache.set(key, {
    expiresAt: Date.now() + LIST_CACHE_TTL_MS,
    value,
  });
}

export function withListDedup<T>(
  key: string,
  loader: () => Promise<T>,
  force = false,
): Promise<T> {
  if (!force) {
    const cached = readListCache<T>(key);
    if (cached !== null) return Promise.resolve(cached);
    const inFlight = listInFlight.get(key);
    if (inFlight) return inFlight as Promise<T>;
  }

  const task = loader()
    .then((result) => {
      writeListCache(key, result);
      return result;
    })
    .finally(() => {
      listInFlight.delete(key);
    });
  listInFlight.set(key, task as Promise<unknown>);
  return task;
}

export function invalidateListCache(keyPrefix?: string): void {
  if (!keyPrefix) {
    listCache.clear();
    listInFlight.clear();
    return;
  }
  for (const key of listCache.keys()) {
    if (key.startsWith(keyPrefix)) listCache.delete(key);
  }
}
