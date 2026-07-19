/**
 * Condition-specific data for each AQI band.
 * When user switches condition tabs, ALL data in the UI updates.
 */

export const CONDITIONS = [
  { key: 'good',          label: 'Good',          min: 0,   max: 50,   aqi: 38,  color: '#00c853' },
  { key: 'satisfactory',  label: 'Satisfactory',  min: 51,  max: 100,  aqi: 78,  color: '#92D14F' },
  { key: 'moderate',      label: 'Moderate',       min: 101, max: 200,  aqi: 156, color: '#FF7E00' },
  { key: 'poor',          label: 'Poor',           min: 201, max: 300,  aqi: 247, color: '#FF7E00' },
  { key: 'very-poor',     label: 'Very Poor',      min: 301, max: 400,  aqi: 358, color: '#FF0000' },
  { key: 'severe',        label: 'Severe',         min: 401, max: 500,  aqi: 462, color: '#99004C' },
];

export const CONDITION_PALETTES = {
  good:         { text: '#1a5c2a', textMuted: 'rgba(26,92,42,0.55)',  gradStart: '#87ceeb', gradEnd: '#c8f5c8' },
  satisfactory: { text: '#3a5c1a', textMuted: 'rgba(58,92,26,0.55)',  gradStart: '#a8d8a0', gradEnd: '#ddf0b0' },
  moderate:     { text: '#2a4a6a', textMuted: 'rgba(42,74,106,0.55)', gradStart: '#8ab8d8', gradEnd: '#b8d8f0' },
  poor:         { text: '#4a2a5c', textMuted: 'rgba(74,42,92,0.55)',  gradStart: '#9878b8', gradEnd: '#c8a8e0' },
  'very-poor':  { text: '#5c2a1a', textMuted: 'rgba(92,42,26,0.55)', gradStart: '#c07850', gradEnd: '#e0a878' },
  severe:       { text: '#3a2a1a', textMuted: 'rgba(58,42,26,0.55)', gradStart: '#806040', gradEnd: '#a08060' },
};

const WARD_NAMES = [
  'Anand Vihar', 'ITO', 'Dwarka Sec-8', 'Rohini', 'Connaught Place',
  'Nehru Nagar', 'Okhla Phase-II', 'Patel Nagar', 'Shahdara', 'Kidwai Nagar',
];

function generateWardsForCondition(condition) {
  const { min, max } = condition;
  const range = max - min;
  // Deterministic-ish AQI spread across wards
  const spreads = [0.85, 0.55, 0.35, 0.70, 0.45, 0.92, 0.65, 0.40, 0.95, 0.50];
  return WARD_NAMES.map((name, i) => ({
    id: name.toLowerCase().replace(/[\s-]+/g, '-'),
    name,
    aqi: Math.round(min + range * spreads[i]),
    lat: 28.5 + i * 0.025,
    lng: 77.05 + (i % 5) * 0.06,
  }));
}

export const CONDITION_DATA = {};

CONDITIONS.forEach((cond) => {
  const wards = generateWardsForCondition(cond);
  const sortedByAqi = [...wards].sort((a, b) => b.aqi - a.aqi);
  const topWard = sortedByAqi[0];

  const advisoryCounts = { good: 0, satisfactory: 1, moderate: 2, poor: 4, 'very-poor': 6, severe: 9 };
  const actionsMap = {
    good: [
      { text: 'Continue routine air quality monitoring across all stations', source: 'Monitoring', confidence: 95 },
      { text: 'Schedule preventive maintenance on industrial scrubbers in Okhla zone', source: 'Industrial', confidence: 88 },
      { text: 'Update public awareness dashboard with seasonal pollen forecasts', source: 'Public Health', confidence: 82 },
    ],
    satisfactory: [
      { text: 'Increase monitoring frequency at construction sites near residential areas', source: 'Construction', confidence: 84 },
      { text: 'Issue advisory for sensitive groups regarding outdoor exercise timing', source: 'Health', confidence: 78 },
      { text: 'Review dust suppression compliance at active road projects', source: 'Infrastructure', confidence: 72 },
    ],
    moderate: [
      { text: 'Deploy water sprinklers at Kidwai Nagar construction site before 6 AM', source: 'Construction', confidence: 82 },
      { text: 'Reroute heavy vehicles from Anand Vihar corridor between 7–10 AM', source: 'Vehicular', confidence: 76 },
      { text: 'Inspect Okhla industrial stack emissions — anomalous PM2.5 spike detected', source: 'Industrial', confidence: 68 },
    ],
    poor: [
      { text: 'Activate Stage-II GRAP measures across NCR — restrict diesel generators', source: 'GRAP', confidence: 91 },
      { text: 'Deploy anti-smog guns at 12 high-density construction zones', source: 'Construction', confidence: 85 },
      { text: 'Issue school advisory — outdoor activities suspended for primary schools', source: 'Education', confidence: 88 },
    ],
    'very-poor': [
      { text: 'Activate Stage-III GRAP — ban non-essential construction activity', source: 'GRAP', confidence: 94 },
      { text: 'Deploy emergency medical teams at 5 high-exposure wards', source: 'Emergency', confidence: 89 },
      { text: 'Enforce odd-even vehicle restrictions across all NCR zones immediately', source: 'Transport', confidence: 92 },
    ],
    severe: [
      { text: 'ACTIVATE STAGE-IV GRAP — Full construction ban, truck entry ban in effect', source: 'GRAP', confidence: 98 },
      { text: 'Order closure of all brick kilns and industrial units without scrubbers', source: 'Industrial', confidence: 96 },
      { text: 'Issue public health emergency — advise all citizens to remain indoors', source: 'Emergency', confidence: 99 },
    ],
  };

  CONDITION_DATA[cond.key] = {
    aqi: cond.aqi,
    wards,
    topHotspot: { name: topWard.name, aqi: topWard.aqi },
    activeAdvisories: advisoryCounts[cond.key],
    actions: actionsMap[cond.key],
  };
});
