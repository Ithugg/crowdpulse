// Mirrors backend/schemas.py: the WebSocket contract between the server and this dashboard.

export type Level = 'normal' | 'busy' | 'caution' | 'danger' | 'critical'

export interface SourceInfo {
  id: string
  label: string
  kind: 'webcam' | 'video' | 'drill'
  available: boolean
}

export interface ZoneConfig {
  id: string
  name: string
  area_m2: number | null // measured floor area; null when it cannot be measured reliably
  capacity: number | null // people the zone holds at the action level: area x 4 people/m2
  polygon: [number, number][] // normalized 0-1
}

export interface LevelInfo {
  id: Level
  label: string
  min: number // people per m2 where the level starts
  what: string
  source: string // research citation
}

export interface Calibration {
  mode: 'ground' | 'size' // ground = camera calibrated from people in view, size = distance from body size
  cam_height_m: number | null
  tilt_deg: number | null
  hfov_deg: number
}

export interface GateConfig {
  id: string
  name: string
  line: [[number, number], [number, number]] // normalized 0-1
  zone_id: string | null
}

export interface GateState {
  id: string
  in_per_min: number
  out_per_min: number
  total_in: number
  total_out: number
  eta_full_s: number | null // at the current net inflow, seconds until the gate's zone reaches that capacity
}

export interface ConfigMsg {
  type: 'config'
  sources: SourceInfo[]
  active_source: string
  run: number // goes up when a drill starts over: a new run is a new session with a clean log
  drill: boolean // the active source is a drill: every reading is simulated and must be labelled
  levels: LevelInfo[]
  exposure_alert_s: number
  calibration: Calibration
  flow: boolean // false on a moving camera: no walking speed or gate counts
  gates: GateConfig[]
  zones: ZoneConfig[]
}

export interface ZoneState {
  id: string
  count: number
  density: number // peak local density, people per m2, smoothed
  avg_density: number | null // count / measured zone area
  level: Level
  trend_per_min: number
  eta_s: number | null // forecast: seconds until eta_level
  eta_level: Level | null
  above_safe_s: number // seconds at or above the action level
  speed_mps: number | null // average walking speed of the people in the zone
  heading_deg: number | null // direction of travel on screen (0 = right, 90 = down); null when standing or mixed
  alignment: number | null // 1 = everyone going the same way, 0 = movement cancels out
  pressure: number | null // crowd pressure = density x velocity variance (Helbing 2007), 1/s2
  history: number[] // last 60 s at 1 Hz, oldest first
}

export interface StateMsg {
  type: 'state'
  seq: number
  ts: number
  source_id: string
  fps: number
  inference_ms: number
  mode: 'live' | 'replay' | 'drill'
  frame: { w: number; h: number }
  total_count: number
  overall_level: Level
  zones: ZoneState[]
  gates: GateState[]
  overlay: { boxes: boolean; heatmap: boolean; privacy: boolean; grid: boolean }
}

export interface AlertMsg {
  type: 'alert'
  id: string
  ts: number
  zone_id: string
  zone_name: string
  kind: 'level_change' | 'prediction' | 'exposure' | 'cleared'
  level: Level
  density: number
  message: string // starts with "DRILL: " when raised by a drill
  drill?: boolean
  status?: 'acknowledged' | 'dispatched'
  ack_s?: number // seconds from the alert to staff acknowledging it
  dispatch_s?: number | null
}

export interface AlertUpdateMsg {
  type: 'alert_update'
  id: string
  status: 'acknowledged' | 'dispatched'
  ack_s: number
  dispatch_s: number | null
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
  drill?: boolean
  status: 'generating' | 'ready'
  rewriting?: boolean // set by the console, not the server: a newer plan for this zone is being written
  origin?: 'gemini' | 'cached'
  model?: string | null
  latency_ms?: number
  headline?: string
  actions?: PlanAction[]
  pa_announcement?: string
  pa_announcement_es?: string
}

export interface ReportMsg {
  type: 'report'
  id: string
  ts: number
  camera: string
  drill?: boolean
  period: { from: string; to: string }
  zones: { name: string; peak_density_per_m2: number; people_at_peak: number; peak_time: string }[]
  status: 'generating' | 'ready'
  origin?: 'gemini' | 'cached'
  model?: string | null
  latency_ms?: number
  title?: string
  summary?: string
  timeline?: string[]
  recommendations?: string[]
}

export interface ErrorMsg {
  type: 'error'
  ts: number
  message: string
}

export type ServerMsg = ConfigMsg | StateMsg | AlertMsg | AlertUpdateMsg | PlanMsg | ReportMsg | ErrorMsg

export type ClientMsg =
  | { type: 'set_source'; source_id: string }
  | { type: 'set_overlay'; boxes?: boolean; heatmap?: boolean; privacy?: boolean; grid?: boolean }
  | { type: 'restart' }
  | { type: 'request_plan'; zone_id: string }
  | { type: 'ack_alert'; alert_id: string; status: 'acknowledged' | 'dispatched' }
  | { type: 'request_report' }
