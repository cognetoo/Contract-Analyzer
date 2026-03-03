import axios from "axios";
import { clearToken, getToken } from "@/lib/auth";

// ---- Base URL ----
function normalizeBaseUrl(url: string) {
  return (url || "").trim().replace(/\/+$/, "");
}

export const API_BASE = normalizeBaseUrl(
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000"
);

// ---- Axios instance ----
export const api = axios.create({
  baseURL: API_BASE,
  // Default timeout for normal requests 
  timeout: 30_000,
});


api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    (config.headers as any).Authorization = `Bearer ${token}`;
  }
  return config;
});


api.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err?.response?.status;
    if (status === 401) {
      clearToken();
    }
    return Promise.reject(err);
  }
);

// ---------------- Retry + Warmup helpers ----------------

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * Retry only for:
 * - network errors 
 * - 502/503/504 (Render cold start / gateway / upstream restart)
 * - optionally 429 (rate limit) if you want
 */
function shouldRetry(err: any) {
  const status = err?.response?.status;
  if (!status) return true; // network / CORS / DNS / blocked / 502 with no body etc.
  return status === 502 || status === 503 || status === 504;
}

async function requestWithRetry<T>(
  fn: () => Promise<T>,
  opts?: { retries?: number; baseDelayMs?: number; label?: string }
): Promise<T> {
  const retries = opts?.retries ?? 5;
  const baseDelayMs = opts?.baseDelayMs ?? 1000;

  let lastErr: any = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (err: any) {
      lastErr = err;

     
      if (!shouldRetry(err)) throw err;

      // last attempt -> throw
      if (attempt === retries) break;

      // exponential backoff: 1s,2s,4s,8s,16s...
      const delay = baseDelayMs * Math.pow(2, attempt);

      await sleep(delay);
    }
  }

  throw lastErr;
}

/**
 * Warm up backend so first real request doesn't hit cold-start 502.
 */
export async function warmupBackend() {
  return requestWithRetry(
    async () => {
      const { data } = await api.get("/health", { timeout: 10_000 });
      return data;
    },
    { label: "warmup", retries: 5, baseDelayMs: 1000 }
  );
}

// ---------------- Types ----------------
export type UploadResponse = {
  contract_id: string;
  status: string;
  filename: string;
  num_clauses: number;
  tmp_path?: string;
};

export type UploadStatusResponse = {
  contract_id: string;
  status: "queued" | "processing" | "indexed" | "failed" | "unknown" | string;
  num_clauses?: number;
  error?: string | null;
};

export type RunMode =
  | "qa"
  | "summary_only"
  | "key_clauses_only"
  | "risk_only"
  | "structured_only"
  | "unclear_only"
  | "lawyer_questions_only"
  | "full_report";

export type QueryRequest = {
  query: string;
  k?: number;
  mode?: RunMode;
};

export type QueryResponse = {
  contract_id: string;
  plan: any;
  result: any;
  perf_ms: { planner: number; executor: number; total: number };
};

export type HistoryItem = {
  id: number;
  created_at: string;
  query: string;
  plan: any;
  result: any;
  perf_ms: { planner: number; executor: number; total: number } | any;
};

export type HistoryResponse = {
  contract_id: string;
  runs: HistoryItem[];
};

export type ClauseResponse = {
  contract_id: string;
  clause_id: number;
  clause_type?: string | null;
  text: string;
};

// ---- Auth types ----
export type AuthResponse = {
  access_token: string;
  token_type: "bearer" | string;
};

export type MeResponse = {
  id: number;
  email: string;
};

// ---------------- APIs ----------------
export async function health(): Promise<{ status: string }> {
  const { data } = await api.get("/health");
  return data;
}

export async function dbHealth(): Promise<{ db: string }> {
  const { data } = await api.get("/db/health");
  return data;
}

export async function uploadContract(file: File): Promise<UploadResponse> {
  // Warm up first 
  await warmupBackend();

  const form = new FormData();
  form.append("file", file);

  return requestWithRetry(
    async () => {
      const { data } = await api.post("/contracts/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120_000,
      });
      return data;
    },
    { label: "upload", retries: 5, baseDelayMs: 1000 }
  );
}

export async function getUploadStatus(
  contractId: string
): Promise<UploadStatusResponse> {
  return requestWithRetry(
    async () => {
      const { data } = await api.get(`/contracts/${contractId}/upload_status`, {
        timeout: 15_000,
      });
      return data;
    },
    { label: "upload_status", retries: 5, baseDelayMs: 1000 }
  );
}

export async function queryContract(
  contractId: string,
  req: QueryRequest
): Promise<QueryResponse> {
  return requestWithRetry(
    async () => {
      const { data } = await api.post(`/contracts/${contractId}/query`, req, {
        timeout: 300_000, 
      });
      return data;
    },
    { label: "query", retries: 3, baseDelayMs: 1000 }
  );
}

export async function getLastResult(contractId: string): Promise<any> {
  const { data } = await api.get(`/contracts/${contractId}/last_result`);
  return data;
}

export async function exportLastResult(contractId: string): Promise<any> {
  const { data } = await api.get(`/contracts/${contractId}/export_last_result`);
  return data;
}


export async function getHistory(
  contractId: string,
  limit = 10
): Promise<HistoryResponse> {
  try {
    const { data } = await api.get(`/contracts/${contractId}/history`, {
      params: { limit },
      timeout: 20_000,
    });
    return data;
  } catch (err: any) {
    const status = err?.response?.status;
    if (status === 404) {
      return { contract_id: contractId, runs: [] };
    }
    throw err;
  }
}

export async function getClause(
  contractId: string,
  clauseId: number
): Promise<ClauseResponse> {
  const { data } = await api.get(`/contracts/${contractId}/clauses/${clauseId}`);
  return data;
}

// ---------------- Auth APIs ----------------
export async function registerUser(email: string, password: string) {
  // Warmup helps prevent first-time OPTIONS/POST weirdness on cold start
  await warmupBackend();

  const { data } = await api.post("/auth/register", { email, password }, { timeout: 30_000 });
  return data;
}

export async function loginUser(email: string, password: string) {
  await warmupBackend();

  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const { data } = await api.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    timeout: 30_000,
  });

  return data;
}

export async function me(): Promise<MeResponse> {
  const { data } = await api.get("/auth/me", { timeout: 20_000 });
  return data;
}