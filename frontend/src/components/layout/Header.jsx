import { useEffect, useState, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { CITY_AQI } from '../../data/mockData';
import { getAqiColor } from '../../utils/aqi';
import { IconMenu } from '../Icons';
import { useTheme } from '../../hooks/useTheme';

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/forecast': 'Forecast',
  '/hotspots': 'Hotspots & Attribution',
  '/admin': 'Enforcement Queue',
  '/citizen': 'Citizen Portal',
};

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" /><path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" /><path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  );
}

export default function Header({ onMenuToggle }) {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const [time, setTime] = useState(new Date());
  const [aqiValue, setAqiValue] = useState(CITY_AQI);
  const [flash, setFlash] = useState(false);

  // Clock
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Simulate live AQI updates
  useEffect(() => {
    const interval = setInterval(() => {
      setAqiValue((prev) => {
        const delta = Math.floor(Math.random() * 7) - 3;
        const next = Math.max(50, Math.min(400, prev + delta));
        if (next !== prev) {
          setFlash(true);
          setTimeout(() => setFlash(false), 400);
        }
        return next;
      });
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const title = PAGE_TITLES[location.pathname] || 'ClearSkies';

  return (
    <header className="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button className="mobile-menu-btn" onClick={onMenuToggle} aria-label="Toggle menu">
          <IconMenu />
        </button>
        <span className="header-city">New Delhi</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>·</span>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>{title}</span>
      </div>
      <div className="header-actions">
        <div className="aqi-ticker">
          <span className="aqi-ticker-label">AQI</span>
          <span
            className={`aqi-ticker-value${flash ? ' flash' : ''}`}
            style={{ color: getAqiColor(aqiValue) }}
          >
            {aqiValue}
          </span>
        </div>
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <MoonIcon /> : <SunIcon />}
        </button>
        <div className="header-time">
          {time.toLocaleDateString('en-IN', {
            weekday: 'short',
            day: 'numeric',
            month: 'short',
          })}{' '}
          {time.toLocaleTimeString('en-IN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </header>
  );
}
