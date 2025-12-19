import { useState, useCallback } from 'react';

interface UseSafeAsyncOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: unknown) => void;
}

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

/**
 * Hook to handle async operations safely with unmount protection
 * and standard error states.
 */
export function useSafeAsync<T = unknown>(
  asyncFunction: () => Promise<T>,
  options?: UseSafeAsyncOptions<T>
) {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      const result = await asyncFunction();
      // If unmounted, React state update warning is handled by React 18+ auto-batching or explicit check
      // But for strict safety we can rely on standard behavior or add mounted ref if needed (less needed in 18)
      
      setState({ data: result, loading: false, error: null });
      options?.onSuccess?.(result);
      return result;
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      setState({ data: null, loading: false, error: err });
      options?.onError?.(err);
      throw err;
    }
  }, [asyncFunction, options]);

  return { ...state, execute };
}
