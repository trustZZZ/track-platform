// Тонкий API-клиент. Базовый URL /api проксируется на backend
// (vite dev: proxy; прод: nginx в Docker).

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
}

export interface CatalogModule {
  id: string | null;
  module: string;
  title: string;
  time_est_min: number;
  rel_path: string | null;
  lessons: number;
}

export interface CatalogLevel {
  level: string;
  modules: CatalogModule[];
}

export interface LessonSummary {
  id: string;
  level: string;
  module: string;
  title: string;
  time_est_min: number;
  skills: string[];
}

export interface LessonFull extends LessonSummary {
  prerequisites: string[];
  rel_path: string;
  body: string;
}

export interface ModuleOverview {
  id: string;
  kind: "module";
  level: string;
  module: string;
  title: string;
  prerequisites: string[];
  skills: string[];
  time_est_min: number;
  rel_path: string;
  body: string;
}

export interface RouterTask {
  task_id: string;
  topic: string;
  question: string;
}

export interface RouterAnswer {
  task_id: string;
  value: string | number;
}

export interface RouterResult {
  score: number;
  total: number;
  recommended_level: string;
  bridge: string;
  text: string;
  details: { task_id: string; correct: boolean }[];
  saved: boolean;
}

export interface MeResponse {
  id: number;
  login: string;
  role: string;
  completed_lessons: string[];
  tasks: { task_id: string; lesson_id: string; verdict: string }[];
  badges: string[];
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path}: ${res.status}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`POST ${path}: ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export async function echoMessage(
  payload: Record<string, unknown>,
): Promise<unknown> {
  return postJson<unknown>("/v1/echo", payload);
}

// --- Контент (этап E2) ---

export async function getCatalog(): Promise<CatalogLevel[]> {
  return getJson<CatalogLevel[]>("/v1/catalog");
}

export async function getLessons(): Promise<LessonSummary[]> {
  return getJson<LessonSummary[]>("/v1/lessons");
}

export async function getLesson(id: string): Promise<LessonFull> {
  return getJson<LessonFull>(`/v1/lessons/${encodeURIComponent(id)}`);
}

export async function getModule(id: string): Promise<ModuleOverview> {
  return getJson<ModuleOverview>(`/v1/modules/${encodeURIComponent(id)}`);
}

// --- Прогресс (этап E3; 401 = не вошёл) ---

export async function getMe(): Promise<MeResponse> {
  return getJson<MeResponse>("/v1/me");
}

export async function completeLesson(
  lessonId: string,
): Promise<{ lesson_id: string; completed: boolean }> {
  const res = await fetch(
    `${BASE_URL}/v1/progress/${encodeURIComponent(lessonId)}/complete`,
    { method: "POST" },
  );
  if (!res.ok) {
    throw new Error(`POST /v1/progress: ${res.status}`);
  }
  return (await res.json()) as { lesson_id: string; completed: boolean };
}

export async function submitTask(payload: {
  lesson_id: string;
  task_id: string;
  proof_url?: string;
  kind?: "self_check" | "pyodide";
}): Promise<{ task_id: string; verdict: string }> {
  return postJson<{ task_id: string; verdict: string }>(
    "/v1/submissions",
    payload,
  );
}

export async function logout(): Promise<void> {
  const res = await fetch(`${BASE_URL}/v1/auth/logout`, { method: "POST" });
  if (!res.ok && res.status !== 204) {
    throw new Error(`POST /v1/auth/logout: ${res.status}`);
  }
}

// --- Роутер-диагностика (этап E5) ---

export async function getRouterTasks(): Promise<RouterTask[]> {
  return getJson<RouterTask[]>("/v1/router/tasks");
}

export async function submitRouter(
  answers: RouterAnswer[],
): Promise<RouterResult> {
  return postJson<RouterResult>("/v1/router", { answers });
}

// --- Бейджи и портфолио (этап E6) ---

export interface PortfolioLevel {
  level: string;
  done: number;
  total: number;
}

export interface Portfolio {
  login: string;
  github_url: string;
  levels: PortfolioLevel[];
  badges: string[];
}

export async function getPortfolio(): Promise<Portfolio> {
  return getJson<Portfolio>("/v1/portfolio");
}

export async function claimBadges(): Promise<{
  granted: string[];
  badges: string[];
}> {
  return postJson<{ granted: string[]; badges: string[] }>(
    "/v1/badges/claim",
    {},
  );
}
