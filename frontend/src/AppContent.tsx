import { useEffect, useMemo, useRef, useState } from "react";

import {
  dbHealth,
  exportLastResult,
  getLastResult,
  health,
  queryContract,
  uploadContract,
  getHistory,
  getClause,
  type QueryResponse,
  type UploadResponse,
  type HistoryItem,
  type ClauseResponse,
} from "./api";

import Sidebar from "./components/layout/Sidebar";
import Workspace, { type RunMode } from "./components/layout/Workspace";
import Insights from "./components/layout/Insights";
import ClauseDrawer from "./components/ClauseDrawer";
import RiskAnalyticsModal from "./components/RiskAnalyticsModal";

import { useToast } from "@/hooks/use-toast";
import {
  getActiveContractId,
  loadSessions,
  setActiveContractId,
  upsertSession,
  type SessionItem,
} from "./storage";

import { exportContractPDF } from "./lib/exportPdf";

type ApiStatus = "unknown" | "ok" | "down";

// ----- helper: prompt shim + STRONG mode marker  -----
function buildModePrompt(mode: RunMode, userText: string): string {
  const extra = userText?.trim() ? `\nUser focus: ${userText.trim()}` : "";
  const tag = `__MODE__:${mode}`;

  switch (mode) {
    case "qa":
      return `${tag}\n${
        userText.trim() || "Answer my question using the contract."
      }`;
    case "summary_only":
      return `${tag}\nProvide a concise contract summary.${extra}`;
    case "key_clauses_only":
      return `${tag}\nExtract the key clauses (top items) with brief notes.${extra}`;
    case "structured_only":
      return `${tag}\nProvide structured analysis (obligations, termination, IP, confidentiality, payments, etc).${extra}`;
    case "risk_only":
      return `${tag}\nAnalyze risks and red flags in this contract.${extra}`;
    case "unclear_only":
      return `${tag}\nFind unclear, missing, or ambiguous clauses / areas.${extra}`;
    case "lawyer_questions_only":
      return `${tag}\nGenerate questions I should ask a lawyer before signing.${extra}`;
    case "full_report":
      return `${tag}\nGenerate the full report (summary + key clauses + structured + risks + unclear + lawyer questions).${extra}`;
    default:
      return `${tag}\n${userText}`;
  }
}

function cleanQueryLabel(q?: string) {
  if (!q) return "";
  return q.replace(/^__MODE__[:\w-]+\s*/i, "");
}

export default function AppContent() {
  const { toast } = useToast();

  const [apiStatus, setApiStatus] = useState<ApiStatus>("unknown");
  const [dbStatus, setDbStatus] = useState<ApiStatus>("unknown");

  const [sessions, setSessions] = useState<SessionItem[]>(() => loadSessions());
  const [activeId, setActiveId] = useState<string>(() => getActiveContractId());

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const [mode, setMode] = useState<RunMode>("qa");
  const [auditMode, setAuditMode] = useState(false);

  const [query, setQuery] = useState("");
  const [k, setK] = useState(3);
  const [asking, setAsking] = useState(false);

  const [lastQueryResp, setLastQueryResp] = useState<QueryResponse | null>(null);
  const [lastResult, setLastResult] = useState<any>(null);

  // history
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const historyReqRef = useRef(0);

  // clause drawer
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerClause, setDrawerClause] = useState<ClauseResponse | null>(null);

  // risk analytics modal
  const [riskOpen, setRiskOpen] = useState(false);

  const activeSession = useMemo(
    () => sessions.find((s) => s.contract_id === activeId) ?? null,
    [sessions, activeId]
  );

  const qaMeta = useMemo(() => {
    if (mode !== "qa") return null;
    if (!lastResult) return null;
    const obj = lastResult?.qa ?? lastResult;
    return {
      method: obj?.method,
      confidence:
        typeof obj?.confidence === "number" ? obj.confidence : undefined,
      citations: Array.isArray(obj?.citations) ? obj.citations : undefined,
    };
  }, [lastResult, mode]);

 
  const hasFullReport = useMemo(() => {
    if (!lastResult) return false;

    if (lastResult?.full_report) return true;

    if (
      lastResult?.summary ||
      lastResult?.key_clauses ||
      lastResult?.structured_analysis ||
      lastResult?.unclear_or_missing ||
      lastResult?.lawyer_questions ||
      lastResult?.risk_report
    ) {
      return true;
    }

    return false;
  }, [lastResult]);

  useEffect(() => {
    (async () => {
      try {
        await health();
        setApiStatus("ok");
      } catch {
        setApiStatus("down");
      }

      try {
        await dbHealth();
        setDbStatus("ok");
      } catch {
        setDbStatus("down");
      }
    })();
  }, []);

  useEffect(() => {
    if (activeId) setActiveContractId(activeId);
  }, [activeId]);

  useEffect(() => {
    if (!activeId) return;
    refreshHistory(activeId);
  }, [activeId]);

  async function refreshHistory(contractId: string) {
    const reqId = ++historyReqRef.current;
    setHistoryLoading(true);

    try {
      const h = await getHistory(contractId, 10);
      if (reqId !== historyReqRef.current) return;
      setHistory(h.runs ?? []);
    } catch (e) {
      if (reqId !== historyReqRef.current) return;
      console.error("History fetch failed:", e);
      setHistory([]);
    } finally {
      if (reqId !== historyReqRef.current) return;
      setHistoryLoading(false);
    }
  }

  async function openClause(clauseId: number) {
    if (!activeId) return;

    setDrawerOpen(true);
    setDrawerLoading(true);
    setDrawerClause(null);

    try {
      const c = await getClause(activeId, clauseId);
      setDrawerClause(c);
    } catch (e) {
      setDrawerClause({
        contract_id: activeId,
        clause_id: clauseId,
        clause_type: null,
        text: "Failed to load clause.",
      });
    } finally {
      setDrawerLoading(false);
    }
  }

  // ---- Actions ----
  async function onUpload() {
    if (!selectedFile) {
      toast({ title: "Choose a PDF first" });
      return;
    }

    setUploading(true);
    try {
      const resp: UploadResponse = await uploadContract(selectedFile);

      const item: SessionItem = {
        contract_id: resp.contract_id,
        filename: resp.filename,
        num_clauses: resp.num_clauses,
        createdAt: Date.now(),
      };

      upsertSession(item);
      setSessions(loadSessions());
      setActiveId(resp.contract_id);

      toast({
        title: "Indexed",
        description: `${resp.filename} (${resp.num_clauses} clauses)`,
      });

      // reset UI
      setSelectedFile(null);
      setLastQueryResp(null);
      setLastResult(null);
      setQuery("");
      setMode("qa");
    } catch (e: any) {
      toast({
        title: "Upload failed",
        description: e?.response?.data?.detail ?? String(e),
        variant: "destructive",
      });
    } finally {
      setUploading(false);
    }
  }

  async function onAsk() {
    if (!activeId) {
      toast({ title: "Upload a contract first" });
      return;
    }

    if (mode === "qa" && !query.trim()) {
      toast({ title: "Enter a question" });
      return;
    }

    setAsking(true);
    try {
      const prompt = buildModePrompt(mode, query);
      const resp = await queryContract(activeId, { query: prompt, k });

      setLastQueryResp(resp);
      setLastResult(resp.result);

      await refreshHistory(activeId);

      toast({
        title: "Done",
        description: `Planner ${resp.perf_ms.planner}ms · Executor ${resp.perf_ms.executor}ms`,
      });
    } catch (e: any) {
      toast({
        title: "Run failed",
        description: e?.response?.data?.detail ?? String(e),
        variant: "destructive",
      });
    } finally {
      setAsking(false);
    }
  }

  async function onLastResult() {
    if (!activeId) return;

    try {
      const res = await getLastResult(activeId);
      const lr = res?.last_result ?? null;
      const loaded = lr?.result ?? lr;

      setLastResult(loaded);
      setLastQueryResp(null);

      toast({ title: "Loaded last result" });
    } catch (e: any) {
      toast({
        title: "Failed",
        description: e?.response?.data?.detail ?? String(e),
        variant: "destructive",
      });
    }
  }

  async function onExportJSON() {
    if (!activeId) return;

    try {
      const data = await exportLastResult(activeId);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `contract_${activeId}_result.json`;
      a.click();
      URL.revokeObjectURL(url);

      toast({ title: "Exported JSON" });
    } catch (e: any) {
      toast({
        title: "Export failed",
        description: e?.response?.data?.detail ?? String(e),
        variant: "destructive",
      });
    }
  }

 function onExportPDF() {
  if (!activeId) return;

  if (!hasFullReport) {
    toast({
      title: "Run Full Report first",
      description: "PDF export is available after running Full Report mode.",
      variant: "destructive",
    });
    return;
  }

  try {
    exportContractPDF({
      contractId: activeId,
      filename: activeSession?.filename,
      mode: "full_report",
      result: lastResult,
    });

    toast({ title: "Exported Full Report PDF" });
  } catch (e: any) {
    toast({
      title: "PDF export failed",
      description: String(e),
      variant: "destructive",
    });
  }
}

  function onSelectSession(contractId: string) {
    setActiveId(contractId);
    setLastQueryResp(null);
    setLastResult(null);
    setQuery("");
    setMode("qa");
  }


  return (
    <div className="min-h-screen w-full text-white bg-gradient-to-b from-slate-950 via-slate-950 to-slate-900 flex">
      <div className="mx-auto max-w-7xl w-full px-6 py-10 flex-1 flex flex-col">
        <div className="rounded-3xl border border-white/10 bg-white/[0.03] shadow-2xl shadow-black/40 backdrop-blur-xl p-6 md:p-8 flex-1 flex flex-col">
          {/* Header */}
          <header className="space-y-2">
            <h1 className="text-5xl font-bold tracking-tight">
              Contract Analyzer
            </h1>
            <p className="text-white/70">
              Upload → query clauses → get structured answers with citations &
              confidence.
            </p>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <span className="text-xs px-2 py-1 rounded-full bg-white/10 border border-white/10">
                API: {apiStatus}
              </span>
              <span className="text-xs px-2 py-1 rounded-full bg-white/10 border border-white/10">
                DB: {dbStatus}
              </span>
            </div>
          </header>

          {/* Layout */}
          <div className="grid grid-cols-12 gap-6 mt-8 flex-1 items-stretch">
            <div className="col-span-12 lg:col-span-3 h-full">
              <Sidebar
                sessions={sessions}
                activeId={activeId}
                activeSession={activeSession}
                onSelectSession={onSelectSession}
                onLastResult={onLastResult}
                onExportJSON={onExportJSON}
                onExportPDF={onExportPDF}
                canExportPDF = {hasFullReport}
              />
            </div>

            <div className="col-span-12 lg:col-span-6 h-full">
              <Workspace
                selectedFile={selectedFile}
                setSelectedFile={setSelectedFile}
                uploading={uploading}
                onUpload={onUpload}
                activeId={activeId}
                mode={mode}
                setMode={setMode}
                query={query}
                setQuery={setQuery}
                k={k}
                setK={setK}
                asking={asking}
                onAsk={onAsk}
                lastQueryResp={lastQueryResp}
                result={lastResult}
                auditMode={auditMode}
                setAuditMode={setAuditMode}
                onExportJSON={onExportJSON}
                onOpenClause={openClause}
                history={history}
                historyLoading={historyLoading}
                onLoadHistoryItem={(item) => {
                  const intent = (item?.plan?.intent as RunMode) ?? mode;
                  setMode(intent);

                  setLastQueryResp({
                    contract_id: activeId,
                    plan: item.plan,
                    result: item.result,
                    perf_ms: item.perf_ms,
                  } as any);

                  setLastResult(item.result);
                  setQuery(cleanQueryLabel(item.query ?? ""));
                }}
              />
            </div>

            <div className="col-span-12 lg:col-span-3 h-full">
              <Insights
                mode={mode}
                activeId={activeId}
                method={qaMeta?.method}
                confidence={qaMeta?.confidence}
                citations={qaMeta?.citations}
                onOpenRiskAnalytics={() => setRiskOpen(true)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Clause Drawer  */}
      <ClauseDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        loading={drawerLoading}
        clauseId={drawerClause?.clause_id ?? null}
        clauseType={drawerClause?.clause_type ?? null}
        text={drawerClause?.text ?? ""}
      />

      {/* Risk Analytics*/}
      <RiskAnalyticsModal
        open={riskOpen}
        onClose={() => setRiskOpen(false)}
        result={lastResult}
        onOpenClause={openClause}
      />
    </div>
  );
}