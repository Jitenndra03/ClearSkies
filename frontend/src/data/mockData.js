/**
 * Mock data for ClearSkies — realistic New Delhi AQI data
 * All data is static for demo purposes; in production this comes from the API.
 */

// --- Ward definitions with coordinates for Leaflet ---
export const WARDS = [
  { id: 'anand-vihar', name: 'Anand Vihar', lat: 28.6469, lng: 77.3164, aqi: 287 },
  { id: 'ito', name: 'ITO', lat: 28.6289, lng: 77.2414, aqi: 198 },
  { id: 'dwarka', name: 'Dwarka Sec-8', lat: 28.5733, lng: 77.0651, aqi: 142 },
  { id: 'rohini', name: 'Rohini', lat: 28.7324, lng: 77.1108, aqi: 231 },
  { id: 'connaught-place', name: 'Connaught Place', lat: 28.6315, lng: 77.2167, aqi: 165 },
  { id: 'nehru-nagar', name: 'Nehru Nagar', lat: 28.6507, lng: 77.2723, aqi: 312 },
  { id: 'okhla', name: 'Okhla Phase-II', lat: 28.5308, lng: 77.2713, aqi: 254 },
  { id: 'patel-nagar', name: 'Patel Nagar', lat: 28.6512, lng: 77.1639, aqi: 178 },
  { id: 'shahdara', name: 'Shahdara', lat: 28.6736, lng: 77.2905, aqi: 341 },
  { id: 'kidwai-nagar', name: 'Kidwai Nagar', lat: 28.5795, lng: 77.2090, aqi: 189 },
];

export const CITY_AQI = 224;

// --- Dashboard data ---
export const DASHBOARD = {
  cityAqi: CITY_AQI,
  topHotspot: { name: 'Shahdara', aqi: 341 },
  activeAdvisories: 4,
  actions: [
    {
      text: 'Deploy water sprinklers at Kidwai Nagar construction site before 6 AM',
      source: 'Construction',
      confidence: 82,
    },
    {
      text: 'Reroute heavy vehicles from Anand Vihar corridor between 7–10 AM',
      source: 'Vehicular',
      confidence: 76,
    },
    {
      text: 'Inspect Okhla industrial stack emissions — anomalous PM2.5 spike detected',
      source: 'Industrial',
      confidence: 68,
    },
  ],
};

// --- Forecast data (mock 24/48/72hr) ---
function generateForecast(baseAqi, hours) {
  const data = [];
  for (let i = 0; i <= hours; i++) {
    const time = new Date();
    time.setHours(time.getHours() + i);
    const drift = Math.sin(i / 6) * 30 + (Math.random() - 0.5) * 20;
    const aqi = Math.max(20, Math.min(450, baseAqi + drift));
    const upper = aqi + 15 + Math.random() * 20;
    const lower = aqi - 15 - Math.random() * 20;
    data.push({
      hour: i,
      time: time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }),
      predicted: Math.round(aqi),
      upper: Math.round(upper),
      lower: Math.round(Math.max(0, lower)),
    });
  }
  return data;
}

export const FORECAST = {};
for (const ward of WARDS) {
  FORECAST[ward.id] = {
    '24h': generateForecast(ward.aqi, 24),
    '48h': generateForecast(ward.aqi, 48),
    '72h': generateForecast(ward.aqi, 72),
  };
}

// Health implications by AQI range
export const HEALTH_IMPLICATIONS = {
  good: 'Air quality is satisfactory. No health risk from air pollution.',
  satisfactory: 'Air quality is acceptable. Sensitive individuals may experience minor breathing discomfort during prolonged outdoor exposure.',
  moderate: 'Breathing discomfort may occur for people with lung disease, asthma, and heart conditions. Limit prolonged outdoor exertion.',
  poor: 'Breathing discomfort is likely for most people on prolonged exposure. Children, elderly, and those with respiratory conditions should avoid outdoor activity.',
  'very-poor': 'Respiratory illness on prolonged exposure is very likely. Avoid outdoor physical activities. Stay indoors and keep windows closed.',
  severe: 'Health emergency. Everyone should avoid all outdoor physical activities. Use N95 masks if going outside is unavoidable. Seek medical attention if experiencing breathing difficulty.',
};

// --- Hotspot data ---
export const HOTSPOTS = [
  { id: 1, zone: 'Shahdara Industrial Belt', source: 'industrial', confidence: 91, aqi: 341, lat: 28.6736, lng: 77.2905 },
  { id: 2, zone: 'Nehru Nagar Construction', source: 'construction', confidence: 87, aqi: 312, lat: 28.6507, lng: 77.2723 },
  { id: 3, zone: 'Anand Vihar Bus Terminal', source: 'vehicular', confidence: 82, aqi: 287, lat: 28.6469, lng: 77.3164 },
  { id: 4, zone: 'Okhla Industrial Area', source: 'industrial', confidence: 79, aqi: 254, lat: 28.5308, lng: 77.2713 },
  { id: 5, zone: 'Rohini Sec-22 Construction', source: 'construction', confidence: 74, aqi: 231, lat: 28.7324, lng: 77.1108 },
  { id: 6, zone: 'ITO Traffic Corridor', source: 'vehicular', confidence: 71, aqi: 198, lat: 28.6289, lng: 77.2414 },
  { id: 7, zone: 'Kidwai Nagar Metro Site', source: 'construction', confidence: 65, aqi: 189, lat: 28.5795, lng: 77.2090 },
  { id: 8, zone: 'Mundka Agricultural Burn', source: 'agricultural', confidence: 58, aqi: 176, lat: 28.6831, lng: 77.0311 },
];

// --- Enforcement queue ---
export const ENFORCEMENT_QUEUE = [
  {
    id: 1,
    priority: 9.4,
    location: 'Kidwai Nagar Construction Site',
    source: 'construction',
    action: 'Deploy water sprinklers at Kidwai Nagar construction site before 6 AM',
    status: 'pending',
    beforeAqi: null,
    afterAqi: null,
  },
  {
    id: 2,
    priority: 8.7,
    location: 'Shahdara Industrial Belt',
    source: 'industrial',
    action: 'Issue notice to Shahdara Chemicals Ltd for exceeding PM2.5 stack emission limits by 34%',
    status: 'dispatched',
    beforeAqi: null,
    afterAqi: null,
  },
  {
    id: 3,
    priority: 8.1,
    location: 'Anand Vihar Bus Terminal',
    source: 'vehicular',
    action: 'Reroute heavy vehicles from Anand Vihar corridor between 7–10 AM peak hours',
    status: 'pending',
    beforeAqi: null,
    afterAqi: null,
  },
  {
    id: 4,
    priority: 7.6,
    location: 'Okhla Phase-II Industrial',
    source: 'industrial',
    action: 'Conduct surprise inspection at Okhla textile units — thermal anomaly detected at 3 AM',
    status: 'resolved',
    beforeAqi: 254,
    afterAqi: 187,
  },
  {
    id: 5,
    priority: 7.2,
    location: 'Rohini Sec-22 Metro Construction',
    source: 'construction',
    action: 'Mandate anti-smog gun deployment at Rohini metro construction site during demolition phase',
    status: 'resolved',
    beforeAqi: 231,
    afterAqi: 162,
  },
  {
    id: 6,
    priority: 6.8,
    location: 'Nehru Nagar Flyover Project',
    source: 'construction',
    action: 'Ensure wind barriers are installed around Nehru Nagar flyover construction perimeter',
    status: 'pending',
    beforeAqi: null,
    afterAqi: null,
  },
  {
    id: 7,
    priority: 6.3,
    location: 'ITO Traffic Junction',
    source: 'vehicular',
    action: 'Deploy traffic police at ITO junction to enforce odd-even compliance between 8–11 AM',
    status: 'dispatched',
    beforeAqi: null,
    afterAqi: null,
  },
  {
    id: 8,
    priority: 5.9,
    location: 'Mundka Agricultural Zone',
    source: 'agricultural',
    action: 'Alert Mundka farmers on stubble burning ban — satellite detected 3 active fire points',
    status: 'resolved',
    beforeAqi: 176,
    afterAqi: 128,
  },
];

// --- Citizen portal data ---
export const CITIZEN = {
  en: {
    wardName: 'Connaught Place',
    aqi: 165,
    message: 'The air in your area is moderately polluted today. People with respiratory conditions may experience discomfort during prolonged outdoor activity.',
    groups: [
      {
        icon: '👶',
        title: 'Children',
        advice: 'Limit outdoor playtime to 30 minutes. Keep school windows closed during recess hours.',
      },
      {
        icon: '👴',
        title: 'Elderly',
        advice: 'Avoid morning walks before 9 AM when pollution levels peak. Use an air purifier indoors if available.',
      },
      {
        icon: '👷',
        title: 'Outdoor Workers',
        advice: 'Wear a mask rated N95 or above. Take 15-minute indoor breaks every 2 hours.',
      },
    ],
  },
  hi: {
    wardName: 'कनॉट प्लेस',
    aqi: 165,
    message: 'आपके क्षेत्र में आज हवा की गुणवत्ता मध्यम रूप से प्रदूषित है। श्वसन रोगों वाले लोगों को लंबे समय तक बाहरी गतिविधियों में असुविधा हो सकती है।',
    groups: [
      {
        icon: '👶',
        title: 'बच्चे',
        advice: 'बाहर खेलने का समय 30 मिनट तक सीमित रखें। छुट्टी के समय स्कूल की खिड़कियाँ बंद रखें।',
      },
      {
        icon: '👴',
        title: 'बुज़ुर्ग',
        advice: 'सुबह 9 बजे से पहले सैर से बचें जब प्रदूषण का स्तर चरम पर होता है। इनडोर एयर प्यूरीफायर का उपयोग करें।',
      },
      {
        icon: '👷',
        title: 'बाहरी कर्मचारी',
        advice: 'N95 या उससे ऊपर का मास्क पहनें। हर 2 घंटे में 15 मिनट इनडोर ब्रेक लें।',
      },
    ],
  },
  chatResponse: {
    en: 'The moderate AQI in Connaught Place is primarily driven by vehicular emissions from the high traffic density in the central business district. PM2.5 levels measured at 78 µg/m³ indicate fine particle concentrations from diesel exhaust and road dust resuspension. Wind speed is low at 4 km/h, limiting pollutant dispersion.',
    hi: 'कनॉट प्लेस में मध्यम AQI मुख्य रूप से केंद्रीय व्यापार जिले में उच्च यातायात घनत्व से वाहन उत्सर्जन के कारण है। PM2.5 का स्तर 78 µg/m³ मापा गया है।',
  },
  chatCitation: 'Source: CPCB Real-time AQI Monitoring, Delhi Pollution Control Committee hourly bulletin, SAFAR-India forecast model v3.2',
};
