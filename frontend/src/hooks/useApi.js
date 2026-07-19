import { useState, useEffect, useCallback } from 'react';

/**
 * Generic hook for API calls with loading / error / data states.
 * @param {Function} apiFn - async function to call
 * @param {Array} deps - dependency array to auto-trigger (pass null to skip auto)
 */
export function useApi(apiFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err.message || 'Something went wrong');
      return null;
    } finally {
      setLoading(false);
    }
  }, [apiFn]);

  useEffect(() => {
    if (deps !== null) {
      execute();
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading, error, execute, setData };
}
