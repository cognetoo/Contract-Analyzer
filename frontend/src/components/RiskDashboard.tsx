import React, { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

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
  overall_risk_score?: number;
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

  if (looksLikeRiskReport(result?.full_report?.risk_report))
    return result.full_report.risk_report;

  if (looksLikeRiskReport(result?.full_report)) return result.full_report;

  if (looksLikeRiskReport(result?.result?.risk_report)) return result.result.risk_report;
  if (looksLikeRiskReport(result?.result)) return result.result;

  if (looksLikeRiskReport(result?.report?.risk_report)) return result.report.risk_report;
  if (looksLikeRiskReport(result?.data?.risk_report)) return result.data.risk_report;

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

function cap(s: string) {
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

function pct(n?: number) {
  if (typeof n !== "number" || Number.isNaN(n)) return "—";
  if (n <= 1) return `${Math.round(n * 100)}%`;
  return `${Math.round(n)}%`;
}

const ORDER: Array<"low" | "medium" | "high" | "critical"> = [
  "low",
  "medium",
  "high",
  "critical",
];


const LEVEL_COLORS: Record<string, string> = {
  low: "#34D399",      // emerald
  medium: "#FBBF24",   // amber
  high: "#FB7185",     // rose
  critical: "#A78BFA", // violet
  unknown: "#94A3B8",  // slate
};

function levelBadgeClass(level: string) {
  switch (level) {
    case "low":
      return "bg-emerald-500/15 border-emerald-500/20";
    case "medium":
      return "bg-amber-500/15 border-amber-500/20";
    case "high":
      return "bg-rose-500/15 border-rose-500/20";
    case "critical":
      return "bg-violet-500/15 border-violet-500/20";
    default:
      return "bg-white/10 border-white/10";
  }
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null;
  const v = payload[0]?.value ?? 0;

  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/90 px-3 py-2 shadow-xl">
      <div className="text-xs text-white/60">{cap(String(label))}</div>
      <div className="text-sm text-white/90 font-medium">Count: {v}</div>
    </div>
  );
}

export default function RiskDashboard(props: {
  result: any;
  onOpenClause?: (clauseId: number) => void;
}) {
  const rr = useMemo(() => extractRiskReport(props.result), [props.result]);

  const derived = useMemo(() => {
    if (!rr) return null;

    const present = Array.isArray(rr.present_risks) ? rr.present_risks : [];
    const missing = rr.missing_risks ?? null;

    const levelCounts: Record<string, number> = {};
    for (const r of present) {
      const lvl = normalizeLevel(r?.risk_level);
      levelCounts[lvl] = (levelCounts[lvl] ?? 0) + 1;
    }

    const chartData = ORDER.map((level) => ({
      level,
      count: levelCounts[level] ?? 0,
      fill: LEVEL_COLORS[level],
    }));

    const rank = (x: string) =>
      x === "critical" ? 4 : x === "high" ? 3 : x === "medium" ? 2 : x === "low" ? 1 : 0;

    const topRisks = present
      .slice()
      .sort((a, b) => rank(normalizeLevel(b?.risk_level)) - rank(normalizeLevel(a?.risk_level)))
      .slice(0, 8);

    return {
      presentCount: present.length,
      missingCount: Array.isArray(missing?.findings) ? missing!.findings!.length : 0,
      overallScore: rr.overall_risk_score,
      chartData,
      topRisks,
    };
  }, [rr]);

  return (
    <Card className="bg-white/5 border-white/10">
      <CardHeader>
        <CardTitle className="text-base">Risk dashboard</CardTitle>
        <div className="text-xs text-white/60">KPIs + charts from latest risk/full report run.</div>
      </CardHeader>

      <CardContent className="space-y-4">
        {!rr || !derived ? (
          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-white/60">
            No risk report yet.
            <div className="mt-2 text-xs text-white/50">
              Run <span className="text-white/80">Risk report</span> or{" "}
              <span className="text-white/80">Full report</span> once to populate this.
            </div>
          </div>
        ) : (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs text-white/60">Overall risk</div>
                <div className="text-lg font-semibold text-white/90">
                  {pct(derived.overallScore)}
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs text-white/60">Present risks</div>
                <div className="text-lg font-semibold text-white/90">
                  {derived.presentCount}
                </div>
              </div>

              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-xs text-white/60">Missing findings</div>
                <div className="text-lg font-semibold text-white/90">
                  {derived.missingCount}
                </div>
              </div>
            </div>

            {/* Chart */}
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
              <div className="flex items-center justify-between">
                <div className="text-sm text-white/80">Risks by level</div>
                <Badge variant="secondary" className="bg-white/10">
                  {derived.presentCount} total
                </Badge>
              </div>

              <div className="mt-3 h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={derived.chartData}>
                    <XAxis
                      dataKey="level"
                      interval={0}
                      tickFormatter={(v) => cap(String(v))}
                      tick={{ fill: "rgba(255,255,255,0.65)", fontSize: 12 }}
                      axisLine={{ stroke: "rgba(255,255,255,0.15)" }}
                      tickLine={{ stroke: "rgba(255,255,255,0.15)" }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 12 }}
                      axisLine={{ stroke: "rgba(255,255,255,0.15)" }}
                      tickLine={{ stroke: "rgba(255,255,255,0.15)" }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" radius={[8, 8, 0, 0]}>
                      {derived.chartData.map((d, idx) => (
                        <Cell key={idx} fill={d.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <Separator className="bg-white/10" />

            {/* Top risks */}
            <div className="space-y-2">
              <div className="text-sm text-white/80">Top risks</div>

              {derived.topRisks.length === 0 ? (
                <div className="text-sm text-white/60">No risks detected.</div>
              ) : (
                <div className="space-y-2">
                  {derived.topRisks.map((r, idx) => {
                    const clauseId = r?.clause_id != null ? Number(r.clause_id) : null;
                    const clickable = clauseId != null && !!props.onOpenClause;
                    const lvl = normalizeLevel(r?.risk_level);

                    return (
                      <div
                        key={idx}
                        className="rounded-lg border border-white/10 bg-white/[0.03] p-3"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <div className="text-sm font-medium text-white/90">
                            {r?.risk_type ?? r?.title ?? `Risk ${idx + 1}`}
                          </div>

                          <Badge
                            variant="secondary"
                            className={"border " + levelBadgeClass(lvl)}
                          >
                            {cap(lvl)}
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
          </>
        )}
      </CardContent>
    </Card>
  );
}