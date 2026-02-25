export type SessionItem = {
  contract_id: string;
  filename: string;
  num_clauses?: number;
  createdAt: number;
};

const KEY = "contract_analyzer_sessions_v1";
const ACTIVE_KEY = "contract_analyzer_active_contract_id_v1";

export function loadSessions(): SessionItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: SessionItem[]) {
  localStorage.setItem(KEY, JSON.stringify(sessions));
}

export function upsertSession(item: SessionItem) {
  const sessions = loadSessions();
  const idx = sessions.findIndex((s) => s.contract_id === item.contract_id);
  if (idx >= 0) sessions[idx] = item;
  else sessions.unshift(item);
  saveSessions(sessions);
}

export function deleteSession(contractId: string) {
  const sessions = loadSessions().filter((s) => s.contract_id !== contractId);
  saveSessions(sessions);
  const active = getActiveContractId();
  if (active === contractId) setActiveContractId(sessions[0]?.contract_id ?? "");
}

export function getActiveContractId(): string {
  return localStorage.getItem(ACTIVE_KEY) || "";
}

export function setActiveContractId(contractId: string) {
  localStorage.setItem(ACTIVE_KEY, contractId);
}