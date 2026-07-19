import { useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useCondition } from '../components/layout/Layout';
import { CONDITION_DATA } from '../data/conditionData';
import CanvasMap from '../components/CanvasMap';

/**
 * Get CPCB severity color for an AQI value.
 */
function getAqiColor(aqi) {
  if (aqi <= 50) return '#00c853';
  if (aqi <= 100) return '#92D14F';
  if (aqi <= 200) return '#FF7E00';
  if (aqi <= 300) return '#FF7E00';
  if (aqi <= 400) return '#FF0000';
  return '#99004C';
}

function getAqiLabel(aqi) {
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Satisfactory';
  if (aqi <= 200) return 'Moderate';
  if (aqi <= 300) return 'Poor';
  if (aqi <= 400) return 'Very Poor';
  return 'Severe';
}

function getAqiBadgeBg(aqi) {
  if (aqi <= 50) return 'rgba(0,200,83,0.15)';
  if (aqi <= 100) return 'rgba(146,209,79,0.15)';
  if (aqi <= 200) return 'rgba(255,126,0,0.15)';
  if (aqi <= 300) return 'rgba(255,126,0,0.15)';
  if (aqi <= 400) return 'rgba(255,0,0,0.15)';
  return 'rgba(153,0,76,0.15)';
}

export default function DashboardPage() {
  const { conditionKey, condition } = useCondition();
  const data = CONDITION_DATA[conditionKey];
  const context = useOutletContext() || {};
  const { wardTrends } = context;

  // Merge mock data with real backend data if available
  const displayWards = useMemo(() => {
    return data.wards.map(w => {
      // the backend returns names as keys, e.g. "Anand Vihar"
      const realData = wardTrends ? wardTrends[w.name] : null;
      return {
        ...w,
        aqi: realData ? Math.round(realData.avg_aqi) : w.aqi
      };
    });
  }, [data.wards, wardTrends]);

  const sortedWards = useMemo(
    () => [...displayWards].sort((a, b) => b.aqi - a.aqi),
    [displayWards]
  );

  const cityAqi = useMemo(() => {
    if (wardTrends && Object.keys(wardTrends).length > 0) {
      const vals = Object.values(wardTrends);
      return Math.round(vals.reduce((sum, v) => sum + v.avg_aqi, 0) / vals.length);
    }
    return data.aqi;
  }, [wardTrends, data.aqi]);

  const now = new Date();
  const timestamp = now.toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });

  return (
    <div>
      {/* Section A: Page header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Air Quality Overview</h1>
          <p className="page-subtitle">
            Real-time monitoring across {displayWards.length} wards in New Delhi
          </p>
        </div>
        <span className="page-timestamp">Last updated: {timestamp}</span>
      </div>

      {/* Section B: 3 stat cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-card-label">Current AQI</div>
          <div className="stat-card-value" style={{ color: getAqiColor(cityAqi) }}>
            {cityAqi}
          </div>
          <div className="stat-card-sub">{getAqiLabel(cityAqi)} — city-wide average</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Top Hotspot</div>
          <div className="stat-card-value" style={{ color: getAqiColor(sortedWards[0].aqi) }}>
            {sortedWards[0].aqi}
          </div>
          <div className="stat-card-sub">{sortedWards[0].name}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Active Advisories</div>
          <div className="stat-card-value" style={{ color: condition.color }}>
            {data.activeAdvisories}
          </div>
          <div className="stat-card-sub">Health alerts issued today</div>
        </div>
      </div>

      {/* Section C: Two-column lower grid */}
      <div className="dashboard-lower">
        {/* Left: Ward list */}
        <div className="ward-panel">
          <div className="ward-panel-title">Wards by Severity</div>
          <div className="ward-list">
            {sortedWards.map((ward) => (
              <div key={ward.id} className="ward-row">
                <div className="ward-row-left">
                  <span className="ward-row-name">{ward.name}</span>
                  <span
                    className="ward-row-badge"
                    style={{
                      color: getAqiColor(ward.aqi),
                      background: getAqiBadgeBg(ward.aqi),
                    }}
                  >
                    {getAqiLabel(ward.aqi)}
                  </span>
                </div>
                <span className="ward-row-aqi" style={{ color: getAqiColor(ward.aqi) }}>
                  {ward.aqi}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Map + Actions */}
        <div className="right-column">
          {/* Map panel */}
          <div className="map-panel">
            <CanvasMap wards={displayWards} conditionColor={condition.color} />
          </div>

          {/* Actions strip */}
          <div className="actions-panel">
            <div className="actions-title">Recommended Actions Today</div>
            {data.actions.map((item, i) => (
              <div key={i} className="action-item">
                <span className="action-rank">0{i + 1}</span>
                <span className="action-text">{item.text}</span>
                <span className="action-tag">{item.source} · {item.confidence}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
