// Mirrors backend/schemas.py: the WebSocket contract between the server and this dashboard.

export type Level = 'green' | 'yellow' | 'red'

export interface SourceInfo {
  id: string
  label: string
  kind: 'webcam' | 'video'
  available: boolean
}

export interface ZoneConfig {
  id: string
  name: string
  area_m2: number
  polygon: [number, number][] // normalized 0-1
}

export interface ConfigMsg {
  type: 'config'
  sources: SourceInfo[]
  active_source: string
  thresholds: { warn: number; critical: number }
  zones: ZoneConfig[]
}

export interface ZoneState {
  id: string
  count: number
  density: number // people per m2, smoothed
  level: Level
  trend_per_min: number
  eta_critical_s: number | null
  history: number[] // last 60 s at 1 Hz, oldest first
}

export interface StateMsg {
  type: 'state'
  seq: number
  ts: number
  source_id: string
  fps: number
  inference_ms: number
  mode: 'live' | 'replay'
  frame: { w: number; h: number }
  total_count: number
  overall_level: Level
  zones: ZoneState[]
  overlay: { boxes: boolean; heatmap: boolean }
}

export interface AlertMsg {
  type: 'alert'
  id: string
  ts: number
  zone_id: string
  zone_name: string
  kind: 'level_change' | 'prediction' | 'cleared'
  level: Level
  density: number
  message: string
}

export interface PlanAction {
  role: string
  instruction: string
}

export interface PlanMsg {
  type: 'plan'
  id: string
  alert_id: string | null
  zone_id: string
  zone_name: string
  level: Level
  ts: number
  status: 'generating' | 'ready'
  origin?: 'gemini' | 'cached'
  model?: string | null
  latency_ms?: number
  headline?: string
  actions?: PlanAction[]
  pa_announcement?: string
}

export interface ErrorMsg {
  type: 'error'
  ts: number
  message: string
}

export type ServerMsg = ConfigMsg | StateMsg | AlertMsg | PlanMsg | ErrorMsg

export type ClientMsg =
  | { type: 'set_source'; source_id: string }
  | { type: 'set_overlay'; boxes?: boolean; heatmap?: boolean }
  | { type: 'restart' }
  | { type: 'request_plan'; zone_id: string }
