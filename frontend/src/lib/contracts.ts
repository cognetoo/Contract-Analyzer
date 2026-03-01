import { api } from "../api";

export async function uploadContract(file: File) {
  const form = new FormData();
  form.append("file", file);

  const res = await api.post("/contracts/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return res.data as {
    contract_id: string;
    status: string;
    filename: string;
    num_clauses: number;
    tmp_path?: string;
  };
}

export async function getUploadStatus(contractId: string) {
  const res = await api.get(`/contracts/${contractId}/upload_status`);
  return res.data as {
    contract_id: string;
    status: "queued" | "processing" | "indexed" | "failed" | "unknown";
    error?: string | null;
    num_clauses?: number;
  };
}

export async function queryContract(contractId: string, payload: { query: string; k?: number; mode?: string }) {
  const res = await api.post(`/contracts/${contractId}/query`, payload);
  return res.data;
}