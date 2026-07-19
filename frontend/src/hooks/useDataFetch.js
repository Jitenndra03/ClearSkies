import { useState, useEffect, useCallback, useRef } from 'react';

const CACHE_PREFIX = 'clearskies_cache_';
const FETCH_TIMEOUT = 8000;

/**
 * Custom data-fetching hook with stale-while-revalidate caching.
 * Returns cached data instantly on mount, revalidates in the background.
 * On failure, serves stale data + error flag rather than a blank page.
 */
export function useDataFetch(fetchFn, cacheKey, deps = []) {
  const [data, setData] = useState(() => {
    if (!cacheKey) return null;
    try {
      const cached = sessionStorage.getItem(CACHE_PREFIX + cacheKey);
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isStale, setIsStale] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  const doFetch = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT);

    try {
      const result = await fetchFn({ signal: controller.signal });
      clearTimeout(timeoutId);
      if (!controller.signal.aborted) {
        setData(result);
        setIsStale(false);
        setIsLoading(false);
        if (cacheKey) {
          try {
            sessionStorage.setItem(CACHE_PREFIX + cacheKey, JSON.stringify(result));
          } catch { /* storage full — ignore */ }
        }
      }
    } catch (err) {
      clearTimeout(timeoutId);
      if (controller.signal.aborted) return;

      // If we have cached data, serve it as stale
      const cached = cacheKey ? sessionStorage.getItem(CACHE_PREFIX + cacheKey) : null;
      if (cached) {
        try {
          setData(JSON.parse(cached));
          setIsStale(true);
        } catch {
          setData(null);
        }
      }
      setError(err.message || 'Failed to load data');
      setIsLoading(false);
    }
  }, [fetchFn, cacheKey]);

  useEffect(() => {
    doFetch();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [doFetch, ...deps]);

  return { data, isLoading, isStale, error, retry: doFetch };
}
