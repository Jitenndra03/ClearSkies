import { useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useCondition } from '../components/layout/Layout';
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
  const { dashboardData } = useOutletContext();

const {
    wardTrends,
    hotspots,
    cityAqi
} = dashboardData;

  // Merge mock data with real backend data if available
  const displayWards = useMemo(() =>

    hotspots.map(h => ({

        id: h.id,

        name: h.zone,

        aqi: h.aqi,

        lat: h.lat,

        lng: h.lng,

        confidence: h.confidence,

        source: h.source

    }))

, [hotspots]);  

  const sortedWards = useMemo(
    () => [...displayWards].sort((a, b) => b.aqi - a.aqi),
    [displayWards]
  );


  const topHotspot =
displayWards.length
    ? displayWards.reduce(
        (a,b)=>a.aqi>b.aqi?a:b
      )
    : null;
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
          <div className="stat-card-value" style={{ color: getAqiColor(topHotspot?.aqi) }}>
            {topHotspot?.aqi}
          </div>
          <div className="stat-card-sub">{topHotspot?.name}</div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Active Advisories</div>
          <div className="stat-card-value" style={{ color: condition.color }}>
            {0}
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
            <CanvasMap hotspots={displayWards} conditionColor={condition.color} />
          </div>

          {/* Actions strip */}
          <div className="actions-panel">
            <div className="actions-title">"No live recommendations available"</div>
            
          </div>
        </div>
      </div>
    </div>
  );
}
