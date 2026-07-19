import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import SkyCanvas from '../SkyCanvas';
import { CONDITIONS, CONDITION_PALETTES } from '../../data/conditionData';
import { getAllTrends } from '../../api/client';

const ConditionContext = createContext();

export function useCondition() {
  return useContext(ConditionContext);
}

export default function Layout() {
  const [conditionKey, setConditionKey] = useState('moderate');
  const [time, setTime] = useState(new Date());

  // Backend state
  const [wardTrends, setWardTrends] = useState(null);
  const [cityAqi, setCityAqi] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Clock tick
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Fetch all trends once for the app
  useEffect(() => {
    let mounted = true;
    async function fetchData() {
      try {
        const data = await getAllTrends();
        if (mounted) {
          setWardTrends(data);
          
          // Calculate city average AQI
          const values = Object.values(data);
          if (values.length > 0) {
            const sum = values.reduce((acc, curr) => acc + curr.avg_aqi, 0);
            setCityAqi(Math.round(sum / values.length));
          } else {
            setCityAqi(null);
          }
          setIsLoading(false);
        }
      } catch (err) {
        if (mounted) {
          console.error("Failed to fetch trends", err);
          setError(err.message);
          setIsLoading(false);
        }
      }
    }
    fetchData();
    return () => { mounted = false; };
  }, []);

  // Swap CSS custom properties when condition changes
  useEffect(() => {
    const palette = CONDITION_PALETTES[conditionKey];
    if (!palette) return;
    const root = document.documentElement;
    root.style.setProperty('--text', palette.text);
    root.style.setProperty('--text-muted', palette.textMuted);
  }, [conditionKey]);

  const condition = CONDITIONS.find(c => c.key === conditionKey) || CONDITIONS[2];

  const handleConditionChange = useCallback((key) => {
    setConditionKey(key);
  }, []);

  return (
    <ConditionContext.Provider value={{ condition, conditionKey, setCondition: handleConditionChange }}>
      {/* Live canvas behind everything */}
      <SkyCanvas condition={conditionKey} />

      <div className="app-layout">
        <Sidebar />
        <Topbar time={time} cityAqi={cityAqi} />
        <main className="main-content">
          <Outlet context={{ wardTrends, isLoading, error }} />
        </main>
      </div>
    </ConditionContext.Provider>
  );
}
