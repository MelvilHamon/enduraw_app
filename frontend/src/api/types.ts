// Types mirroring the FastAPI backend schemas. Kept in one file so the API
// surface is easy to scan against app/schemas/* and app/models/enums.py.

// --- Auth ------------------------------------------------------------------
export interface TokenOut {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserOut {
  id: string;
  email: string;
  persona_id: string | null;
  is_active: boolean;
  created_at: string;
}

// --- Checkin ---------------------------------------------------------------
export interface CheckinCreate {
  date: string; // YYYY-MM-DD
  form_vs_normal: number; // -2..2
  motivation: number; // 1..5
  fatigue: number; // 1..5
}

export interface CheckinOut extends CheckinCreate {
  id: string;
  reported_at: string;
  created_at: string;
  updated_at: string;
}

// --- Insights (fusion) -----------------------------------------------------
export type Reco = "train_as_planned" | "lighten" | "rest" | "consult_physio";

export interface Signal {
  key: string;
  triggered: boolean;
  severity: number;
  value: number | null;
  reference: number | null;
  delta: number | null;
  direction: string | null;
  explanation: string;
  evidence: string[];
}

export type ReadinessHint = "low" | "neutral" | "high";

export interface EngineState {
  date: string;
  fitness: number;
  fatigue: number;
  form: number;
  acwr: number | null;
  load_7d: number;
  load_28d: number;
  trend_form_7d: number | null;
  readiness_hint: ReadinessHint;
}

export interface Readiness {
  reco: Reco;
  top_2: Signal[];
  explanation: string;
}

export interface DailyRead {
  date: string;
  engine_state: EngineState | null;
  composite_score: number;
  readiness: Readiness;
  signals: Signal[];
}

export interface EnginePoint {
  date: string;
  value: number | null;
}

export interface Timeseries {
  date_from: string;
  date_to: string;
  series: Record<string, EnginePoint[]>;
  form_vs_normal: EnginePoint[];
  divergence: EnginePoint[];
}

// --- Niggles ---------------------------------------------------------------
export type BodyRegion =
  | "foot_fore"
  | "foot_mid"
  | "foot_heel"
  | "ankle"
  | "achilles"
  | "calf"
  | "shin"
  | "knee_anterior"
  | "knee_medial"
  | "knee_lateral"
  | "knee_posterior"
  | "quad"
  | "hamstring"
  | "adductor"
  | "it_band"
  | "hip_flexor"
  | "glute"
  | "groin"
  | "lower_back"
  | "upper_back"
  | "neck"
  | "shoulder"
  | "other";

export type Side = "left" | "right" | "center" | "bilateral";
export type PainType = "sharp" | "dull" | "tension" | "burning" | "stabbing";
export type MechanicalPattern =
  | "uphill"
  | "downhill"
  | "push_off"
  | "impact"
  | "rest"
  | "constant";
export type Timing = "during" | "after" | "morning_stiffness" | "constant";
export type IsNewOrRecurrent = "new" | "recurrent" | "unknown";

export interface ReportCreate {
  date?: string | null;
  intensity: number; // 0..10
  pain_type?: PainType | null;
  mechanical_pattern?: MechanicalPattern | null;
  timing?: Timing | null;
  is_new_or_recurrent: IsNewOrRecurrent;
  linked_activity_id?: string | null;
  notes?: string | null;
}

export interface ReportOut {
  id: string;
  niggle_id: string;
  date: string;
  intensity: number;
  pain_type: PainType | null;
  mechanical_pattern: MechanicalPattern | null;
  timing: Timing | null;
  is_new_or_recurrent: string;
  linked_activity_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface NiggleCreate {
  region: BodyRegion;
  side: Side;
  structure?: string | null;
  notes?: string | null;
  opened_at?: string | null;
  initial_report?: ReportCreate | null;
}

export interface NiggleOut {
  id: string;
  opened_at: string;
  closed_at: string | null;
  region: BodyRegion;
  side: Side;
  structure: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface NiggleWithReports extends NiggleOut {
  reports: ReportOut[];
}

// --- Mini-tests ------------------------------------------------------------
export type MiniTestType = "jump" | "reaction";

export interface ReactionData {
  type: "reaction";
  mean_rt_ms: number;
  sd_rt_ms: number;
  n_taps: number;
}

export interface JumpData {
  type: "jump";
  flight_time_ms: number;
  height_cm: number;
}

export type MiniTestData = ReactionData | JumpData;

export interface MiniTestCreate {
  date: string;
  reported_at: string;
  data: MiniTestData;
}

export interface MiniTestOut {
  id: string;
  date: string;
  reported_at: string;
  type: MiniTestType;
  data: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface MiniTestBaseline {
  type: string;
  metric: string;
  n: number;
  mean: number | null;
  std: number | null;
  latest: number | null;
  latest_z: number | null;
}

// --- Illness ---------------------------------------------------------------
export type IllnessSymptom =
  | "sore_throat"
  | "congestion"
  | "fever"
  | "unusual_fatigue"
  | "cough"
  | "body_aches";

export interface IllnessHint {
  triggered: boolean;
  hrv_delta: number | null;
  rhr_delta: number | null;
  resp_delta: number | null;
  baseline_window_days: number;
}

export interface IllnessCreate {
  date?: string | null;
  symptoms: IllnessSymptom[];
  notes?: string | null;
}

export interface IllnessOut {
  id: string;
  date: string;
  symptoms: IllnessSymptom[];
  watch_hint_triggered: boolean;
  confirmed_by_user: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}
