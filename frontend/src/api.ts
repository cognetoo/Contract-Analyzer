import axios from "axios";

export const API_BASE =
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({ baseURL: API_BASE });

export type UploadResponse = {
  contract_id: string;
  status: string;
  filename: string;
  num_clauses: number;
  tmp_path?: string;
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
    created_at:string;
    query: string;
    plan: any;
    result: any;
    perf_ms: {
        planner:number;
        executor: number;
        total: number;
    } | any;
};

export type HistoryResponse = {
    contract_id : string;
    runs: HistoryItem[];
}

export async function health(): Promise<{ status: string }> {
  const { data } = await api.get("/health");
  return data;
}

export async function dbHealth(): Promise<{ db: string }> {
  const { data } = await api.get("/db/health");
  return data;
}

export async function uploadContract(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const { data } = await api.post("/contracts/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function queryContract(
  contractId: string,
  req: QueryRequest
): Promise<QueryResponse> {
  const { data } = await api.post(`/contracts/${contractId}/query`, req);
  return data;
}

export async function getLastResult(contractId: string): Promise<any> {
  const { data } = await api.get(`/contracts/${contractId}/last_result`);
  return data;
}

export async function exportLastResult(contractId: string): Promise<any> {
  const { data } = await api.get(`/contracts/${contractId}/export_last_result`);
  return data;
}

export async function getHistory(contractId: string, limit = 10):Promise<HistoryResponse>{
    const { data } = await api.get(`/contracts/${contractId}/history`,{
        params: { limit },
    });
    return data;
}

export type ClauseResponse ={
    contract_id: string;
    clause_id: number;
    clause_type?: string | null;
    text: string;
};

export async function getClause(contractId: string, clauseId: number): Promise<ClauseResponse>{
    const { data } = await api.get(`/contracts/${contractId}/clauses/${clauseId}`);
    return data;
}

