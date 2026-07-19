/**
 * API Client for ClearSkies (AirPulse) Backend
 * Wraps fetch calls to the FastAPI endpoints.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const errorBody = await res.text();
      throw new Error(`API ${res.status}: ${errorBody}`);
    }
    return await res.json();
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error('Backend is unreachable. Make sure the FastAPI server is running on ' + API_BASE);
    }
    throw err;
  }
}

// ---- Feature 10: Trends ----
export async function getAllTrends() {
  return request('/api/trends');
}

export async function getWardTrends(ward) {
  return request(`/api/trends/${encodeURIComponent(ward)}`);
}

// ---- Feature 2: Attribution ----
export async function postAttribution(hotspot) {
  return request('/api/attribution', {
    method: 'POST',
    body: JSON.stringify(hotspot),
  });
}

export async function getModelReport() {
  return request('/api/attribution/model-report');
}

// ---- Feature 5: Advisory ----
export async function postAdvisory(profile) {
  return request('/api/advisory', {
    method: 'POST',
    body: JSON.stringify(profile),
  });
}

// ---- Root health check ----
export async function getHealth() {
  return request('/');
}

// ---- Feature: Admin Enforcement Queue ----
export async function getEnforcementQueue() {
  return request('/api/enforcement-queue');
}

export const postEnforcementOutcome = (data) =>
  fetch(`${API_BASE}/api/enforcement-outcome`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json());

export const postChatQuery = (data) =>
  fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json());

