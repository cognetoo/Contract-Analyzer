import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";

import { ScrollArea } from "@radix-ui/react-scroll-area";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import ResultView from "@/components/ResultView";
import type { QueryResponse,HistoryItem } from "src/api";
import type { CheckedState } from "@radix-ui/react-checkbox";
import ExecutiveSnapshot from "../ExecutiveSnapshot";

export type RunMode =
  | "qa"
  | "summary_only"
  | "key_clauses_only"
  | "risk_only"
  | "structured_only"
  | "unclear_only"
  | "lawyer_questions_only"
  | "full_report";

function modeLabel(m: RunMode) {
  switch (m) {
    case "qa":
      return "Query (QA)";
    case "summary_only":
      return "Summary";
    case "key_clauses_only":
      return "Key clauses";
    case "risk_only":
      return "Risk report";
    case "structured_only":
      return "Structured analysis";
    case "unclear_only":
      return "Unclear / missing";
    case "lawyer_questions_only":
      return "Questions for lawyer";
    case "full_report":
      return "Full report";
    default:
      return m;
  }
}

function explainMode(m: RunMode) {
  switch (m) {
    case "qa":
      return "Ask a specific question. Uses retrieval + QA.";
    case "summary_only":
      return "One-page summary of the contract.";
    case "key_clauses_only":
      return "Extract the most important clauses.";
    case "risk_only":
      return "Find risks and red flags with mitigation suggestions.";
    case "structured_only":
      return "Organized analysis (termination, IP, payment, confidentiality, etc).";
    case "unclear_only":
      return "Detect vague / missing clauses and ambiguity.";
    case "lawyer_questions_only":
      return "Generate questions to ask a lawyer before signing.";
    case "full_report":
      return "Everything combined into one report.";
    default:
      return "";
  }
}

// Human-readable audit formatting
function formatPlan(plan: any): string {
  if (!plan) return "No plan yet.";
  const intent = plan.intent ? `Intent: ${plan.intent}` : "Intent: —";
  const k = typeof plan.k === "number" ? `k: ${plan.k}` : "k: —";
  const steps = Array.isArray(plan.steps)
    ? plan.steps
        .map((s: any, i: number) => {
          const tool = s?.tool ?? "—";
          const args = s?.args ? JSON.stringify(s.args) : "{}";
          return `${i + 1}. ${tool} ${args !== "{}" ? args : ""}`.trim();
        })
        .join("\n")
    : "—";
  const notes = plan.notes ? `\n\nNotes:\n${plan.notes}` : "";
  return `${intent}\n${k}\n\nSteps:\n${steps}${notes}`;
}

function formatEvidence(result: any): string {
  if (!result) return "Citations: —\n\nEvidence: —";

  // Collect clause ids from many possible shapes
  const clauseIds = new Set<number>();

  const add = (x: any) => {
    const n = Number(x);
    if (Number.isFinite(n)) clauseIds.add(n);
  };

  const walk = (node: any) => {
    if (!node) return;

    // arrays
    if (Array.isArray(node)) {
      for (const it of node) walk(it);
      return;
    }

    if (typeof node === "object") {
      // common patterns
      if (Array.isArray((node as any).citations)) (node as any).citations.forEach(add);
      if (Array.isArray((node as any).key_citations)) (node as any).key_citations.forEach(add);

      if ((node as any).clause_id != null) add((node as any).clause_id);

      for (const v of Object.values(node)) walk(v);
    }
  };

  const obj = result?.qa ?? result;
  walk(obj);
  const ids = Array.from(clauseIds).sort((a, b) => a - b).slice(0, 25);

  const cLine = ids.length ? `Citations: ${ids.join(", ")}` : "Citations: —";
  const eLines =
    ids.length
      ? "Evidence:\n" + ids.map((c) => `- Clause ${c}`).join("\n")
      : "Evidence: —";

  return `${cLine}\n\n${eLines}`;
}

function cleanQueryLabel(q?: string){
    if(!q) return "";

    return q.replace(/^__MODE__[:\w-]+\s*/i,"");
}

export default function Workspace(props: {
  // Upload
  selectedFile: File | null;
  setSelectedFile: (f: File | null) => void;
  uploading: boolean;
  onUpload: () => void;

  // Run
  activeId: string;
  mode: RunMode;
  setMode: (m: RunMode) => void;

  query: string;
  setQuery: (s: string) => void;
  k: number;
  setK: (n: number) => void;

  asking: boolean;
  onAsk: () => void;

  // Results
  lastQueryResp: QueryResponse | null;
  result: any;
  auditMode: boolean;
  setAuditMode: (b: boolean) => void;

  history: HistoryItem[];
  historyLoading: boolean;
  onLoadHistoryItem: (item: HistoryItem)=> void;

  onOpenClause: (clauseId: number)=> void;

  onExportJSON: () => void;
}) {
  const { selectedFile, setSelectedFile } = props;

  const isQA = props.mode === "qa";
  const canRun =
    !!props.activeId &&
    !props.asking &&
    (isQA ? props.query.trim().length > 0 : true);

  const runButtonLabel = useMemo(() => {
    if (props.mode === "qa") return props.asking ? "Asking..." : "Ask";
    return props.asking ? "Running..." : "Run";
  }, [props.mode, props.asking]);

  const queryLabel = isQA ? "Question" : "Extra focus (optional)";
  const queryPlaceholder = isQA
    ? 'e.g. "Can I terminate early?"'
    : 'Optional: e.g. "Focus on termination + liability"';

  return (
    <div className="h-full flex flex-col gap-4 min-h-0">
        {/* Executive Snapshot (top of page) */}
        {props.activeId && (
        <ExecutiveSnapshot result={props.result} onOpenClause={props.onOpenClause} />
        )}
      {/* Upload */}
      <Card className="bg-white/[0.04] border-white/15">
        <CardHeader>
          <CardTitle className="text-base">1) Upload</CardTitle>
          <div className="text-xs text-white/60">
            Upload a PDF to create a new contract session.
          </div>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="rounded-xl border border-white/10 bg-white/5 p-3">
            <div className="flex flex-col gap-3">
              <Input
                type="file"
                accept="application/pdf"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                className="bg-transparent border-white/10 file:bg-white/10 file:text-white file:border-0 file:rounded-lg file:px-3 file:py-2 file:mr-3"
              />

              <Separator className="bg-white/10" />

              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-white/60">Selected file</span>
                <span className="text-white/85 truncate max-w-[70%]">
                  {selectedFile ? selectedFile.name : "None"}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-white/60 truncate">
              Session status:{" "}
              <span className="text-white/80">
                {props.activeId ? "Active" : "No session"}
              </span>
            </div>

            <Badge
              className="bg-white/10 border border-white/10"
              variant="secondary"
            >
              {props.activeId ? "active" : "no session"}
            </Badge>
          </div>

          <Button
            onClick={props.onUpload}
            disabled={!selectedFile || props.uploading}
            className="w-full bg-indigo-500/90 hover:bg-indigo-500 text-white"
          >
            {props.uploading ? "Uploading & indexing..." : "Upload & Index"}
          </Button>

          {props.activeId ? (
            <div className="text-xs text-white/60">
              Active contract_id:{" "}
              <span className="text-white/80">{props.activeId}</span>
            </div>
          ) : (
            <div className="text-xs text-white/60">No active session yet.</div>
          )}
        </CardContent>
      </Card>

      {/* Run */}
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="text-base">2) Run</CardTitle>
          <div className="text-xs text-white/60">
            Choose what you want (QA / Summary / Risk report / etc).
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Mode block */}
          <div className="space-y-2">
            <div className="text-xs text-white/60">Mode</div>
            <Select
              value={props.mode}
              onValueChange={(v) => props.setMode(v as RunMode)}
              disabled={!props.activeId}
            >
              <SelectTrigger className="bg-white/5 border-white/10">
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent className="bg-slate-950 border-white/10 text-white">
                <SelectItem value="qa">{modeLabel("qa")}</SelectItem>
                <SelectItem value="summary_only">
                  {modeLabel("summary_only")}
                </SelectItem>
                <SelectItem value="key_clauses_only">
                  {modeLabel("key_clauses_only")}
                </SelectItem>
                <SelectItem value="risk_only">{modeLabel("risk_only")}</SelectItem>
                <SelectItem value="structured_only">
                  {modeLabel("structured_only")}
                </SelectItem>
                <SelectItem value="unclear_only">
                  {modeLabel("unclear_only")}
                </SelectItem>
                <SelectItem value="lawyer_questions_only">
                  {modeLabel("lawyer_questions_only")}
                </SelectItem>
                <SelectItem value="full_report">{modeLabel("full_report")}</SelectItem>
              </SelectContent>
            </Select>

            <div className="text-xs text-white/60">{explainMode(props.mode)}</div>
          </div>

          <Separator className="bg-white/10" />

          {/* Query / Focus block */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="text-xs text-white/60">{queryLabel}</div>
              {!isQA && (
                <Badge className="bg-white/10" variant="secondary">
                  optional
                </Badge>
              )}
            </div>

            <Textarea
              placeholder={queryPlaceholder}
              value={props.query}
              onChange={(e) => props.setQuery(e.target.value)}
              disabled={!props.activeId}
              className="min-h-[92px] bg-white/5 border-white/10"
            />

            {isQA ? (
              <div className="text-xs text-white/60">
                Tip: ask a precise question for best answers.
              </div>
            ) : (
              <div className="text-xs text-white/60">
                Optional: add extra focus (e.g., “termination + liability”) to steer the report.
              </div>
            )}
          </div>

          <Separator className="bg-white/10" />

          {/* Top-k block (visible always, disabled outside QA) */}
          <div className={isQA ? "space-y-2" : "space-y-2 opacity-60"}>
            <div className="flex items-center justify-between">
              <div className="text-xs text-white/60">Top-k</div>
              <Badge className="bg-white/10" variant="secondary">
                {props.k}
              </Badge>
            </div>

            <div className="rounded-md bg-white/5 border border-white/10 px-3 py-3">
              <Slider
                value={[props.k]}
                min={1}
                max={10}
                step={1}
                onValueChange={(v) => props.setK(v[0])}
                disabled={!props.activeId || !isQA}
              />
            </div>

            <div className="text-xs text-white/60">
              {isQA
                ? "Top-k controls how many relevant clauses we retrieve before answering. Higher k = more context, slightly slower."
                : "Top-k applies only to QA mode (retrieval). Reports use the full contract pipeline."}
            </div>
          </div>

          {/* Run button */}
          <Button onClick={props.onAsk} disabled={!canRun} className="w-full">
            {runButtonLabel}
          </Button>
        </CardContent>
      </Card>

      {/* Response */}
      <Card className="bg-white/5 border-white/10 flex-1 flex flex-col min-h-0">
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-1">
              <CardTitle className="text-base">Response</CardTitle>
              <div className="text-xs text-white/60">
                Clean answer by default. Audit mode shows plan + evidence + export.
              </div>
            </div>

            <label className="flex items-center gap-2 text-xs text-white/70 cursor-pointer select-none mt-1">
              <Checkbox
                checked={props.auditMode}
                onCheckedChange={(v: CheckedState) => props.setAuditMode(v === true)}
              />
              Audit mode
            </label>
          </div>
        </CardHeader>

        <CardContent className="flex-1 flex flex-col gap-4 min-h-0">
        {/* Run history */}
        {props.activeId && (
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="flex items-center justify-between">
            <div className="text-xs text-white/70">Run history (last 10)</div>
            <div className="text-xs text-white/50">
                {props.historyLoading ? "Loading..." : `${props.history.length} items`}
            </div>
            </div>

            <div className="mt-2 space-y-2">
            {props.history.length === 0 && !props.historyLoading ? (
                <div className="text-xs text-white/50">No previous runs yet.</div>
            ) : (
                props.history.slice(0, 10).map((h, idx) => (
                <button
                    key={idx}
                    onClick={() => props.onLoadHistoryItem(h)}
                    className="w-full text-left rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 px-3 py-2"
                >
                 <div className="flex items-center justify-between gap-3">
                    <div className="text-xs text-white/80 truncate">
                      {h?.plan?.intent ?? "run"}
                      {h?.query ? ` · ${cleanQueryLabel(h.query)}` : ""}
                    </div>
                    <div className="text-[11px] text-white/50 whitespace-nowrap">
                        {h?.perf_ms?.total != null ? `${Math.round(h.perf_ms.total)}ms` : ""}
                    </div>
                    </div>
                </button>
                ))
            )}
            </div>
        </div>
        )}

        {/* Clean user view */}
        <div className = "flex-1 min-h-0">
          <ScrollArea className="h-full pr-3">
          <ResultView mode={props.mode} 
          result = {props.result}
          onOpenClause={props.onOpenClause} />
          </ScrollArea>
        </div>

          {/* Audit view */}
          {props.auditMode && (
            <>
              <Separator className="bg-white/10" />

              <div className="space-y-3">
                <div>
                  <div className="text-xs text-white/60 mb-1">Planner plan</div>
                  <Card className="bg-white/5 border-white/10">
                    <CardContent className="p-3 text-xs whitespace-pre-wrap text-white/80 leading-5">
                      {formatPlan(props.lastQueryResp?.plan)}
                    </CardContent>
                  </Card>
                </div>

                <div>
                  <div className="text-xs text-white/60 mb-1">Evidence</div>
                  <Card className="bg-white/5 border-white/10">
                    <CardContent className="p-3 text-xs whitespace-pre-wrap text-white/80 leading-5">
                      {formatEvidence(props.result)}
                    </CardContent>
                  </Card>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs text-white/60">
                    Raw JSON is available for export (useful for debugging / demos).
                  </div>
                  <Button
                    variant="secondary"
                    className="bg-white/10"
                    onClick={props.onExportJSON}
                    disabled={!props.activeId}
                  >
                    Export JSON
                  </Button>
                </div>
              </div>
            </>
          )}

        </CardContent>
      </Card>
    </div>
  );
}