export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';
export type AlertSeverity = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE';
export type AlertStatus = 'ACTIVE' | 'ACKNOWLEDGED' | 'RESOLVED';
export type MonitoringStatus = 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE';

export interface LocationItem {
  location_id: string;
  name: string;
  state: string;
  district: string;
  latitude: number;
  longitude: number;
  elevation: number;
  slope: number;
  aspect?: string;
  terrain_roughness?: number;
  geology_type?: string;
  vegetation_type?: string;
  monitoring_status: MonitoringStatus;
  risk_level: RiskLevel;
  current_risk_score: number;
  alert_status: string;
  latest_measurements?: {
    rainfall_1h?: number;
    rainfall_24h?: number;
    rainfall_7d?: number;
    soil_moisture?: number;
    vegetation_index?: number;
    temperature?: number;
    humidity?: number;
    timestamp?: string;
  };
  latest_prediction?: {
    risk_score: number;
    risk_level: RiskLevel;
    probability: number;
    confidence: number;
    recommendation?: string;
    explanation?: string;
  };
  created_at: string;
  updated_at: string;
}

export interface RiskFactor {
  factor: string;
  impact: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  weight: number;
  description: string;
}

export interface PredictionInput {
  location_id: string;
  latitude: number;
  longitude: number;
  rainfall_1h: number;
  rainfall_24h: number;
  rainfall_7d: number;
  soil_moisture: number;
  slope: number;
  elevation: number;
  terrain_roughness: number;
  vegetation_index: number;
}

export interface PredictionOutput {
  location_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  probability: number;
  confidence: number;
  risk_factors: RiskFactor[];
  timestamp: string;
  recommendation: string;
  explanation?: string;
  input_features?: Record<string, number>;
}

export interface AlertItem {
  id: number;
  alert_id: string;
  location_id: string;
  severity: AlertSeverity;
  status: AlertStatus;
  risk_score: number;
  title: string;
  message: string;
  triggering_factors: RiskFactor[];
  recommended_action: string;
  sop_actions?: string[];
  created_at: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_notes?: string;
  location_name?: string;
  state?: string;
  district?: string;
}

export interface HistoricalLandslide {
  id: number;
  event_id: string;
  location_name: string;
  state: string;
  district: string;
  latitude: number;
  longitude: number;
  event_date: string;
  severity: string;
  triggering_rainfall_24h?: number;
  triggering_rainfall_7d?: number;
  slope?: number;
  elevation?: number;
  estimated_volume_m3?: number;
  casualties: number;
  infrastructure_damage?: string;
  geological_formation?: string;
  data_source?: string;
  notes?: string;
}

export interface ThresholdSettings {
  threshold_low: number;
  threshold_moderate: number;
  threshold_high: number;
  updated_at: string;
  updated_by: string;
  notes?: string;
}

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  service: string;
  version: string;
  database: string;
  ml_engine: string;
  weather_provider: string;
}

export interface TrendDataPoint {
  timestamp: string;
  location_id: string;
  risk_score: number;
  risk_level: RiskLevel;
  rainfall_24h: number;
  rainfall_1h: number;
  soil_moisture: number;
}
