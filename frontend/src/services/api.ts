import {
  LocationItem,
  PredictionInput,
  PredictionOutput,
  AlertItem,
  HistoricalLandslide,
  ThresholdSettings,
  SystemHealth
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_URL || '/api';

function authenticatedFetch(url: string, options: RequestInit = {}) {
  const token=sessionStorage.getItem('operations-token');
  return fetch(url,{...options,credentials:'include',headers:{...options.headers,...(token?{'X-Operations-Key':token}:{})},signal:AbortSignal.timeout(20000)});
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const err = await res.json();
      errorDetail = (typeof err.detail === 'string' ? err.detail : Array.isArray(err.detail) ? err.detail.map((e: any) => e.msg).join('; ') : err.message) || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Locations
  async getLocations(params?: { state?: string; district?: string; risk_level?: string }): Promise<LocationItem[]> {
    const query = new URLSearchParams();
    if (params?.state) query.append('state', params.state);
    if (params?.district) query.append('district', params.district);
    if (params?.risk_level) query.append('risk_level', params.risk_level);
    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await authenticatedFetch(`${API_BASE}/locations${qs}`);
    return handleResponse<LocationItem[]>(res);
  },

  async getLocationById(id: string): Promise<LocationItem> {
    const res = await authenticatedFetch(`${API_BASE}/locations/${id}`);
    return handleResponse<LocationItem>(res);
  },

  async createLocation(data: Partial<LocationItem>): Promise<LocationItem> {
    const res = await authenticatedFetch(`${API_BASE}/locations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<LocationItem>(res);
  },

  async updateLocation(id: string, data: Partial<LocationItem>): Promise<LocationItem> {
    const res = await authenticatedFetch(`${API_BASE}/locations/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<LocationItem>(res);
  },

  async deleteLocation(id: string): Promise<{ message: string }> {
    const res = await authenticatedFetch(`${API_BASE}/locations/${id}`, {
      method: 'DELETE',
    });
    return handleResponse<{ message: string }>(res);
  },

  async syncLocation(id: string): Promise<LocationItem> {
    const res = await authenticatedFetch(`${API_BASE}/locations/${id}/sync`, {
      method: 'POST',
    });
    return handleResponse<LocationItem>(res);
  },

  // Prediction Engine
  async predictLandslide(payload: PredictionInput): Promise<PredictionOutput> {
    const res = await authenticatedFetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, simulation: true }),
    });
    return handleResponse<PredictionOutput>(res);
  },

  async getPredictionStats(): Promise<{
    total_predictions: number;
    average_risk_score: number;
    maximum_risk_score: number;
    distribution_by_level: Record<string, number>;
  }> {
    const res = await authenticatedFetch(`${API_BASE}/predictions/stats`);
    return handleResponse(res);
  },

  // Alerts
  async getAlerts(params?: { severity?: string; status?: string; location_id?: string }): Promise<AlertItem[]> {
    const query = new URLSearchParams();
    if (params?.severity) query.append('severity', params.severity);
    if (params?.status) query.append('status', params.status);
    if (params?.location_id) query.append('location_id', params.location_id);
    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await authenticatedFetch(`${API_BASE}/alerts${qs}`);
    return handleResponse<AlertItem[]>(res);
  },

  async getAlertStats(): Promise<{
    active_alerts: number;
    severe_active: number;
    high_active: number;
    acknowledged_alerts: number;
    resolved_alerts: number;
    total_generated: number;
  }> {
    const res = await authenticatedFetch(`${API_BASE}/alerts/stats`);
    return handleResponse(res);
  },

  async acknowledgeAlert(alertId: string, acknowledgedBy: string = 'OFFICER_IN_CHARGE'): Promise<AlertItem> {
    const res = await authenticatedFetch(`${API_BASE}/alerts/${alertId}/acknowledge`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ acknowledged_by: acknowledgedBy }),
    });
    return handleResponse<AlertItem>(res);
  },

  async resolveAlert(alertId: string, resolvedBy: string = 'FIELD_DISASTER_TEAM', notes: string = 'Threat subsided'): Promise<AlertItem> {
    const res = await authenticatedFetch(`${API_BASE}/alerts/${alertId}/resolve`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolved_by: resolvedBy, resolution_notes: notes }),
    });
    return handleResponse<AlertItem>(res);
  },

  // Historical & Analysis
  async getHistoricalLandslides(params?: { state?: string; severity?: string }): Promise<HistoricalLandslide[]> {
    const query = new URLSearchParams();
    if (params?.state) query.append('state', params.state);
    if (params?.severity) query.append('severity', params.severity);
    const qs = query.toString() ? `?${query.toString()}` : '';
    const res = await authenticatedFetch(`${API_BASE}/analysis/historical${qs}`);
    return handleResponse<HistoricalLandslide[]>(res);
  },

  async getTrends(locationId?: string): Promise<{
    timeseries: any[];
    state_breakdown: Array<{ state: string; monitored_sites: number; avg_risk: number; critical_sites: number }>;
  }> {
    const qs = locationId ? `?location_id=${encodeURIComponent(locationId)}` : '';
    const res = await authenticatedFetch(`${API_BASE}/analysis/trends${qs}`);
    return handleResponse(res);
  },

  async getModelPerformance(): Promise<{
    status: string;
    model_architecture: string;
    accuracy: number;
    precision: number;
    recall: number;
    f1_score: number;
    roc_auc: number;
    confusion_matrix: number[][];
    feature_importances: [string, number][];
  }> {
    const res = await authenticatedFetch(`${API_BASE}/analysis/model-performance`);
    return handleResponse(res);
  },

  // Settings
  async getThresholds(): Promise<ThresholdSettings> {
    const res = await authenticatedFetch(`${API_BASE}/settings/thresholds`);
    return handleResponse<ThresholdSettings>(res);
  },

  async updateThresholds(data: { threshold_low: number; threshold_moderate: number; threshold_high: number; updated_by?: string }): Promise<ThresholdSettings> {
    const res = await authenticatedFetch(`${API_BASE}/settings/thresholds`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<ThresholdSettings>(res);
  },

  // System Health
  async getHealth(): Promise<SystemHealth> {
    const healthUrl = API_BASE === '/api' ? '/health' : `${API_BASE.replace(/\/api\/?$/, '')}/health`;
    const res = await authenticatedFetch(healthUrl);
    return handleResponse<SystemHealth>(res);
  },

  // Environmental Telemetry
  async getEnvironmentalTelemetry(latitude: number, longitude: number): Promise<any> {
    const res = await authenticatedFetch(`${API_BASE}/environmental/current?latitude=${latitude}&longitude=${longitude}`);
    return handleResponse(res);
  }
};
