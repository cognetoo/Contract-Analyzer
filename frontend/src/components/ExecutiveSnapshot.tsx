import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

type RiskLevel = "low" | "medium" | "high" | "critical" | string;

type PresentRisk = {
  risk_type?: string;
  title?: string;
  risk_level?: RiskLevel;
  confidence?: number;
  clause_id?: number | string | null;
  explanation?: string;
  mitigation?: string;
};

type MissingRisks = {
  risk_level?: RiskLevel;
  risk_score?: number;
  findings?: any[];
};

type RiskReport = {
  overall_risk_score?: number; // usually 0..1 (or 0..100)
  present_risks?: PresentRisk[];
  missing_risks?: MissingRisks;
  additional_risks?: any[];
};

function isObj(v: any) {
  return v != null && typeof v === "object" && !Array.isArray(v);
}

function looksLikeRiskReport(v: any): v is RiskReport {
  return (
    isObj(v) &&
    (Array.isArray(v.present_risks) ||
      isObj(v.missing_risks) ||
      Array.isArray(v.additional_risks)) &&
    typeof v.overall_risk_score !== "undefined"
  );
}

function extractRiskReport(result: any): RiskReport | null {
  if (!result) return null;
  if (looksLikeRiskReport(result)) return result;
  if (looksLikeRiskReport(result?.risk_report)) return result.risk_report;
  if (looksLikeRiskReport(result?.full_report?.risk_report)) return result.full_report.risk_report;
  if (looksLikeRiskReport(result?.full_report)) return result.full_report;
  if (looksLikeRiskReport(result?.result?.risk_report)) return result.result.risk_report;
  if (looksLikeRiskReport(result?.result)) return result.result;
  return null;
}

function normalizeLevel(lvl: any): "low" | "medium" | "high" | "critical" | "unknown" {
  const s = String(lvl ?? "").toLowerCase();
  if (s.includes("critical")) return "critical";
  if (s.includes("high")) return "high";
  if (s.includes("medium") || s.includes("med")) return "medium";
  if (s.includes("low")) return "low";
  return "unknown";
}

function levelRank(lvl: string) {
  return lvl === "critical" ? 4 : lvl === "high" ? 3 : lvl === "medium" ? 2 : lvl === "low" ? 1 : 0;
}

function scoreTo01(x: any): number | null {
  if (typeof x !== "number" || Number.isNaN(x)) return null;
  return x > 1.5 ? Math.max(0, Math.min(1, x / 100)) : Math.max(0, Math.min(1, x));
}

function recLabel(score01: number, missingCount: number) {
  const bumped = Math.min(1, score01 + (missingCount >= 4 ? 0.12 : missingCount >= 2 ? 0.06 : 0));
  if (bumped >= 0.67) return { label: "HIGH RISK", tone: "bg-red-500/20 border-red-500/30 text-red-200" };
  if (bumped >= 0.34) return { label: "REVIEW", tone: "bg-amber-500/20 border-amber-500/30 text-amber-200" };
  return { label: "SAFE", tone: "bg-emerald-500/20 border-emerald-500/30 text-emerald-200" };
}

function pct01(score01: number | null) {
  if (score01 == null) return "—";
  return `${Math.round(score01 * 100)}%`;
}

export default function ExecutiveSnapshot(props: {
  result: any;
  onOpenClause?: (clauseId: number) => void;
}) {
  const rr = useMemo(() => extractRiskReport(props.result), [props.result]);

  const derived = useMemo(() => {
    const present = Array.isArray(rr?.present_risks) ? rr!.present_risks! : [];
    const missingCount = Array.isArray(rr?.missing_risks?.findings) ? rr!.missing_risks!.findings!.length : 0;

    const score01 = scoreTo01(rr?.overall_risk_score);

    const topRedFlags = present
      .slice()
      .sort((a, b) => {
        const ra = levelRank(normalizeLevel(a?.risk_level));
        const rb = levelRank(normalizeLevel(b?.risk_level));
        if (rb !== ra) return rb - ra;
        const ca = typeof a?.confidence === "number" ? a.confidence : 0;
        const cb = typeof b?.confidence === "number" ? b.confidence : 0;
        return cb - ca;
      })
      .slice(0, 3);

    // pull lawyer questions if present 
    const lawyerQs =
      props.result?.questions_to_ask_lawyer ??
      props.result?.full_report?.questions_to_ask_lawyer ??
      props.result?.lawyer_questions ??
      props.result?.full_report?.lawyer_questions ??
      null;

    const lawyerTop = Array.isArray(lawyerQs) ? lawyerQs.slice(0, 4) : null;

    const rec = score01 == null ? null : recLabel(score01, missingCount);

    return {
      score01,
      presentCount: present.length,
      missingCount,
      topRedFlags,
      lawyerTop,
      rec,
    };
  }, [rr, props.result]);

  if (!derived || (derived.score01 == null && derived.presentCount === 0 && derived.missingCount === 0)) {
    return (
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="text-base">Executive snapshot</CardTitle>
          <div className="text-xs text-white/60">Run Risk report or Full report to populate this.</div>
        </CardHeader>
        <CardContent className="text-sm text-white/60">
          No data yet.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-white/5 border-white/10">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">📊 Executive risk snapshot</CardTitle>
            <div className="text-xs text-white/60">Boardroom-style summary from latest run.</div>
          </div>

          {derived.rec ? (
            <Badge className={`border ${derived.rec.tone}`}>
              {derived.rec.label}
            </Badge>
          ) : (
            <Badge variant="secondary" className="bg-white/10">—</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* KPIs */}
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="text-xs text-white/60">Risk score</div>
            <div className="text-lg font-semibold text-white/90">{pct01(derived.score01)}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="text-xs text-white/60">Red flags</div>
            <div className="text-lg font-semibold text-white/90">{derived.presentCount}</div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
            <div className="text-xs text-white/60">Missing items</div>
            <div className="text-lg font-semibold text-white/90">{derived.missingCount}</div>
          </div>
        </div>

        <Separator className="bg-white/10" />

        {/* Top 3 red flags */}
        <div className="space-y-2">
          <div className="text-sm text-white/80">Top red flags</div>

          {derived.topRedFlags.length === 0 ? (
            <div className="text-sm text-white/60">No present risks detected.</div>
          ) : (
            <div className="space-y-2">
              {derived.topRedFlags.map((r, idx) => {
                const lvl = normalizeLevel(r?.risk_level);
                const clauseId = r?.clause_id != null ? Number(r.clause_id) : null;
                const clickable = clauseId != null && !!props.onOpenClause;

                return (
                  <div key={idx} className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-sm font-medium text-white/90">
                        {r?.risk_type ?? r?.title ?? `Risk ${idx + 1}`}
                      </div>

                      <Badge variant="secondary" className="bg-white/10">
                        {lvl}
                      </Badge>

                      {typeof r?.confidence === "number" ? (
                        <Badge variant="secondary" className="bg-white/10">
                          {Math.round(r.confidence * 100)}%
                        </Badge>
                      ) : null}

                      {clauseId != null ? (
                        <Badge
                          variant="secondary"
                          className={
                            "bg-white/10 border border-white/10 " +
                            (clickable ? "cursor-pointer hover:bg-white/15" : "")
                          }
                          onClick={() => clickable && props.onOpenClause?.(clauseId)}
                        >
                          Clause {clauseId}
                        </Badge>
                      ) : null}
                    </div>

                    {r?.explanation ? (
                      <div className="mt-2 text-sm text-white/75 whitespace-pre-wrap">
                        {r.explanation}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Lawyer pack */}
        {Array.isArray(derived.lawyerTop) && derived.lawyerTop.length > 0 && (
          <>
            <Separator className="bg-white/10" />
            <div className="space-y-2">
              <div className="text-sm text-white/80">Lawyer pack (top questions)</div>
              <ol className="list-decimal pl-5 space-y-1 text-sm text-white/75">
                {derived.lawyerTop.map((q: any, i: number) => (
                  <li key={i} className="whitespace-pre-wrap">
                    {typeof q === "string" ? q : q?.question ?? q?.text ?? String(q)}
                  </li>
                ))}
              </ol>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}