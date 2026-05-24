import { useCallback, useRef, useState } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';

export function useRefSyncedState<T>(
  initial: T,
): [T, Dispatch<SetStateAction<T>>, MutableRefObject<T>] {
  const [state, setState] = useState<T>(initial);
  const ref = useRef<T>(state);

  const setter = useCallback((action: SetStateAction<T>) => {
    setState((prev) => {
      const next =
        typeof action === 'function' ? (action as (prev: T) => T)(prev) : action;
      ref.current = next;
      return next;
    });
  }, []) as Dispatch<SetStateAction<T>>;

  return [state, setter, ref];
}
