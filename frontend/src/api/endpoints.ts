// Typed endpoint functions, one per API route the app uses. Thin wrappers over
// request() so screens never build URLs or shapes by hand.
import { request } from "./client";
import type {
  CheckinCreate,
  CheckinOut,
  DailyMetricOut,
  DailyRead,
  IllnessCreate,
  IllnessHint,
  IllnessOut,
  MiniTestBaseline,
  MiniTestCreate,
  MiniTestOut,
  MiniTestType,
  NiggleCreate,
  NiggleOut,
  NiggleWithReports,
  ReportCreate,
  ReportOut,
  Timeseries,
  TokenOut,
  UserOut,
} from "./types";

// --- Auth ------------------------------------------------------------------
export function login(email: string, password: string): Promise<TokenOut> {
  return request<TokenOut>("/api/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export function register(email: string, password: string): Promise<UserOut> {
  return request<UserOut>("/api/auth/register", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export function getMe(): Promise<UserOut> {
  return request<UserOut>("/api/auth/me");
}

// --- Checkin ---------------------------------------------------------------
export function upsertCheckin(payload: CheckinCreate): Promise<CheckinOut> {
  return request<CheckinOut>("/api/checkin", { method: "POST", body: payload });
}

export function getCheckinToday(): Promise<CheckinOut> {
  return request<CheckinOut>("/api/checkin/today");
}

export function listCheckins(from: string, to: string): Promise<CheckinOut[]> {
  return request<CheckinOut[]>("/api/checkin", { query: { from, to, limit: 200 } });
}

// --- Insights --------------------------------------------------------------
export function getToday(): Promise<DailyRead> {
  return request<DailyRead>("/api/insights/today");
}

export function getTimeseries(
  from: string,
  to: string,
  metrics: string[] = ["form"],
): Promise<Timeseries> {
  const params = new URLSearchParams({ from, to });
  for (const m of metrics) params.append("metrics", m);
  return request<Timeseries>(`/api/insights/timeseries?${params.toString()}`);
}

// --- Garmin / daily metrics ------------------------------------------------
export function listDailyMetrics(from: string, to: string): Promise<DailyMetricOut[]> {
  return request<DailyMetricOut[]>("/api/garmin/daily", { query: { from, to, limit: 200 } });
}

// --- Niggles ---------------------------------------------------------------
export function listNiggles(active = false): Promise<NiggleOut[]> {
  return request<NiggleOut[]>("/api/niggles", { query: { active: active ? "true" : "false" } });
}

export function getNiggle(id: string): Promise<NiggleWithReports> {
  return request<NiggleWithReports>(`/api/niggles/${id}`);
}

export function createNiggle(payload: NiggleCreate): Promise<NiggleWithReports> {
  return request<NiggleWithReports>("/api/niggles", { method: "POST", body: payload });
}

export function addReport(niggleId: string, payload: ReportCreate): Promise<ReportOut> {
  return request<ReportOut>(`/api/niggles/${niggleId}/reports`, { method: "POST", body: payload });
}

// --- Mini-tests ------------------------------------------------------------
export function createMiniTest(payload: MiniTestCreate): Promise<MiniTestOut> {
  return request<MiniTestOut>("/api/mini-tests", { method: "POST", body: payload });
}

export function getBaseline(type: MiniTestType): Promise<MiniTestBaseline> {
  return request<MiniTestBaseline>("/api/mini-tests/baseline", { query: { type } });
}

export function listMiniTests(
  from: string,
  to: string,
  type?: MiniTestType,
): Promise<MiniTestOut[]> {
  return request<MiniTestOut[]>("/api/mini-tests", { query: { from, to, type, limit: 200 } });
}

// --- Illness ---------------------------------------------------------------
export function getIllnessHint(date: string): Promise<IllnessHint> {
  return request<IllnessHint>("/api/illness/hint", { query: { date } });
}

export function postIllness(payload: IllnessCreate): Promise<IllnessOut> {
  return request<IllnessOut>("/api/illness", { method: "POST", body: payload });
}
