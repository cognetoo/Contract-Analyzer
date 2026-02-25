import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

type RunMode =
  | "qa"
  | "summary_only"
  | "key_clauses_only"
  | "risk_only"
  | "structured_only"
  | "unclear_only"
  | "lawyer_questions_only"
  | "full_report";

function asString(v: any) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

function isPlainObject(v: any) {
  return v != null && typeof v === "object" && !Array.isArray(v);
}

function looksLikeRiskReport(v: any) {
  return (
    isPlainObject(v) &&
    (Array.isArray((v as any).present_risks) ||
      isPlainObject((v as any).missing_risks) ||
      Array.isArray((v as any).additional_risks)) &&
    typeof (v as any).overall_risk_score !== "undefined"
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-sm font-semibold text-white/90 mb-2">{children}</div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return <div className="text-sm text-white/60">{children}</div>;
}

function Pill(props: { children: React.ReactNode; onClick?: () => void }) {
  const clickable = !!props.onClick;

  return (
    <Badge
      variant="secondary"
      className={
        "bg-white/10 border border-white/10 " +
        (clickable ? "cursor-pointer hover:bg-white/15" : "")
      }
      onClick={props.onClick}
    >
      {props.children}
    </Badge>
  );
}

/** -------- Key Clauses -------- */
function renderKeyClauses(payload: any, onOpenClause?: (id: number) => void) {
  const obj = payload?.key_clauses ?? payload;

  if (Array.isArray(obj)) {
    if (obj.length === 0) return <Muted>No key clauses found.</Muted>;

    return (
      <div className="space-y-3">
        {obj.slice(0, 25).map((c: any, idx: number) => (
          <div
            key={idx}
            className="rounded-lg border border-white/10 bg-white/5 p-3"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="text-sm font-medium text-white/90">
                {c?.title ??
                  c?.clause_type ??
                  `Clause ${c?.clause_id ?? idx + 1}`}
              </div>

              {c?.clause_id != null && (
                <Pill onClick={() => onOpenClause?.(Number(c.clause_id))}>
                  Clause {c.clause_id}
                </Pill>
              )}
            </div>

            <div className="text-sm text-white/75 mt-2 whitespace-pre-wrap">
              {c?.summary ??
                c?.text ??
                c?.snippet ??
                c?.clause_text ??
                asString(c)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!isPlainObject(obj)) return <Muted>No key clauses found.</Muted>;

  const entries = Object.entries(obj);
  const hasAny = entries.some(([, v]) => Array.isArray(v) && (v as any).length > 0);
  if (!hasAny) return <Muted>No key clauses found.</Muted>;

  return (
    <div className="space-y-5">
      {entries.map(([section, arr]) => {
        const items = Array.isArray(arr) ? arr : [];
        if (items.length === 0) return null;

        return (
          <div key={section} className="space-y-2">
            <div className="text-sm font-semibold text-white/90 capitalize">
              {section.replaceAll("_", " ")}
            </div>

            <div className="space-y-3">
              {items.slice(0, 25).map((c: any, idx: number) => (
                <div
                  key={idx}
                  className="rounded-lg border border-white/10 bg-white/5 p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm font-medium text-white/90">
                      {c?.title ??
                        c?.clause_type ??
                        `Clause ${c?.clause_id ?? idx + 1}`}
                    </div>

                    {c?.clause_id != null && (
                      <Pill onClick={() => onOpenClause?.(Number(c.clause_id))}>
                        Clause {c.clause_id}
                      </Pill>
                    )}
                  </div>

                  <div className="text-sm text-white/75 mt-2 whitespace-pre-wrap">
                    {c?.summary ??
                      c?.text ??
                      c?.snippet ??
                      c?.clause_text ??
                      asString(c)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** -------- Risks -------- */
function renderRisks(payload: any, onOpenClause?: (id: number) => void) {
  const obj = payload?.risk_report ?? payload;
  const present = obj?.present_risks;

  if (!Array.isArray(present) || present.length === 0) {
    return <Muted>No risks detected.</Muted>;
  }

  return (
    <div className="space-y-4">
      <div className="space-y-3">
        {present.slice(0, 30).map((r: any, idx: number) => (
          <div
            key={idx}
            className="rounded-lg border border-white/10 bg-white/5 p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-sm font-medium text-white/90">
                {r?.risk_type ?? r?.title ?? `Risk ${idx + 1}`}
              </div>

              {r?.risk_level && <Pill>{r.risk_level}</Pill>}

              {r?.clause_id != null && (
                <Pill onClick={() => onOpenClause?.(Number(r.clause_id))}>
                  Clause {r.clause_id}
                </Pill>
              )}

              {typeof r?.confidence === "number" && (
                <Pill>{Math.round(r.confidence * 100)}%</Pill>
              )}
            </div>

            {r?.explanation && (
              <div className="text-sm text-white/80 mt-2 whitespace-pre-wrap">
                {r.explanation}
              </div>
            )}

            {r?.mitigation && (
              <div className="text-sm text-white/70 mt-2 whitespace-pre-wrap">
                <span className="text-white/85 font-medium">Mitigation: </span>
                {r.mitigation}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Missing risks */}
      {obj?.missing_risks && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-sm font-semibold text-white/90">Missing risks</div>

          {typeof obj.missing_risks?.risk_level === "string" && (
            <div className="mt-2 flex items-center gap-2">
              <Pill>{obj.missing_risks.risk_level}</Pill>
              {typeof obj.missing_risks?.risk_score === "number" && (
                <span className="text-xs text-white/70">
                  score: {obj.missing_risks.risk_score}
                </span>
              )}
            </div>
          )}

          {Array.isArray(obj.missing_risks?.findings) &&
          obj.missing_risks.findings.length > 0 ? (
            <ul className="mt-3 list-disc pl-5 space-y-1 text-sm text-white/80">
              {obj.missing_risks.findings.slice(0, 30).map((f: any, i: number) => (
                <li key={i} className="whitespace-pre-wrap">
                  {String(f)}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-sm text-white/80 mt-2 whitespace-pre-wrap">
              {asString(obj.missing_risks)}
            </div>
          )}
        </div>
      )}

      {/* Additional risks */}
      {Array.isArray(obj?.additional_risks) && obj.additional_risks.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-sm font-semibold text-white/90">Additional risks</div>

          <div className="mt-3 space-y-3">
            {obj.additional_risks.slice(0, 20).map((r: any, idx: number) => (
              <div
                key={idx}
                className="rounded-lg border border-white/10 bg-white/[0.03] p-3"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <div className="text-sm font-medium text-white/90">
                    {r?.risk_type ?? `Risk ${idx + 1}`}
                  </div>
                  {r?.risk_level && <Pill>{r.risk_level}</Pill>}
                </div>

                <div className="text-sm text-white/80 mt-2 whitespace-pre-wrap">
                  {r?.explanation ?? asString(r)}
                </div>

                {r?.mitigation && (
                  <div className="text-sm text-white/70 mt-2 whitespace-pre-wrap">
                    <span className="text-white/85 font-medium">Mitigation: </span>
                    {r.mitigation}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/** -------- Unclear / Missing -------- */
function renderUnclear(payload: any, onOpenClause?: (id: number) => void) {
  const items = Array.isArray(payload) ? payload : payload?.unclear_or_missing;

  if (!Array.isArray(items) || items.length === 0) {
    return <Muted>No unclear/missing issues found.</Muted>;
  }

  return (
    <div className="space-y-3">
      {items.slice(0, 40).map((it: any, idx: number) => (
        <div
          key={idx}
          className="rounded-lg border border-white/10 bg-white/5 p-3"
        >
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm font-medium text-white/90">
              {it?.issue_type ?? it?.type ?? "Issue"}
            </div>

            {it?.clause_id != null && (
              <Pill onClick={() => onOpenClause?.(Number(it.clause_id))}>
                Clause {it.clause_id}
              </Pill>
            )}
          </div>

          <div className="text-sm text-white/80 mt-2 whitespace-pre-wrap">
            {it?.snippet ?? it?.detail ?? it?.question ?? asString(it)}
          </div>
        </div>
      ))}
    </div>
  );
}

/** -------- Lawyer Questions -------- */
function renderLawyerQuestions(payload: any, onOpenClause?: (id: number) => void) {
  const items = Array.isArray(payload)
    ? payload
    : payload?.questions_to_ask_lawyer ??
      payload?.lawyer_questions ??
      payload?.questions;

  if (!Array.isArray(items) || items.length === 0) {
    return <Muted>No questions generated.</Muted>;
  }

  return (
    <ol className="space-y-3 list-decimal pl-5 text-white/85">
      {items.slice(0, 40).map((q: any, idx: number) => (
        <li key={idx} className="text-sm whitespace-pre-wrap">
          {typeof q === "string" ? q : q?.question ?? q?.text ?? asString(q)}

          {Array.isArray(q?.citations) && q.citations.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {q.citations.slice(0, 10).map((c: number) => (
                <Pill key={c} onClick={() => onOpenClause?.(Number(c))}>
                  Clause {c}
                </Pill>
              ))}
            </div>
          ) : null}
        </li>
      ))}
    </ol>
  );
}

/** -------- Structured Analysis -------- */
function renderStructured(payload: any, onOpenClause?: (id: number) => void) {
  const sections = payload?.structured_analysis ?? payload?.sections ?? payload;
  if (!isPlainObject(sections)) return <Muted>No structured analysis.</Muted>;

  const entries = Object.entries(sections).filter(
    ([k]) => k !== "_meta" && k !== "meta"
  );
  if (entries.length === 0) return <Muted>No structured analysis.</Muted>;

  function renderCitations(citations: any) {
    if (!Array.isArray(citations) || citations.length === 0) return null;
    return (
      <div className="mt-2 flex flex-wrap gap-2">
        {citations.slice(0, 10).map((c: number) => (
          <Pill key={c} onClick={() => onOpenClause?.(Number(c))}>
            Clause {c}
          </Pill>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {entries.map(([k, v]) => {
        // Special: other_red_flags array
        if (k === "other_red_flags" && Array.isArray(v)) {
          return (
            <div
              key={k}
              className="rounded-lg border border-white/10 bg-white/5 p-3"
            >
              <div className="text-sm font-semibold text-white/90 capitalize">
                {k.replaceAll("_", " ")}
              </div>

              <div className="mt-3 space-y-3">
                {v.slice(0, 20).map((it: any, idx: number) => (
                  <div
                    key={idx}
                    className="rounded-lg border border-white/10 bg-white/[0.03] p-3"
                  >
                    <div className="text-sm text-white/85 whitespace-pre-wrap">
                      {typeof it === "string"
                        ? it
                        : it?.issue ?? it?.text ?? asString(it)}
                    </div>
                    {renderCitations(it?.citations)}
                  </div>
                ))}
              </div>
            </div>
          );
        }

        const vv: any = v;

        // Normal { answer, citations }
        if (isPlainObject(vv) && typeof vv?.answer === "string") {
          const citations = Array.isArray(vv?.citations) ? vv.citations : [];

          return (
            <div
              key={k}
              className="rounded-lg border border-white/10 bg-white/5 p-3"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-semibold text-white/90 capitalize">
                  {k.replaceAll("_", " ")}
                </div>

                {citations.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {citations.slice(0, 6).map((c: number) => (
                      <Pill key={c} onClick={() => onOpenClause?.(Number(c))}>
                        Clause {c}
                      </Pill>
                    ))}
                  </div>
                )}
              </div>

              <div className="text-sm text-white/80 mt-2 whitespace-pre-wrap">
                {vv.answer}
              </div>
            </div>
          );
        }

        // fallback
        return (
          <div
            key={k}
            className="rounded-lg border border-white/10 bg-white/5 p-3"
          >
            <div className="text-sm font-semibold text-white/90 capitalize">
              {k.replaceAll("_", " ")}
            </div>
            <div className="text-sm text-white/80 mt-2 whitespace-pre-wrap">
              {asString(vv)}
            </div>
          </div>
        );
      })}

      {/* Confidence meta */}
      {sections?._meta && (
        <div className="rounded-lg border border-white/10 bg-white/5 p-3">
          <div className="text-sm font-semibold text-white/90">Confidence</div>

          {typeof sections._meta?.overall_confidence === "number" && (
            <div className="mt-2 text-sm text-white/85">
              Overall: {Math.round(sections._meta.overall_confidence * 100)}%
            </div>
          )}

          {isPlainObject(sections._meta?.section_confidence) ? (
            <div className="mt-3 space-y-1">
              {Object.entries(sections._meta.section_confidence).map(
                ([name, val]: any) => (
                  <div
                    key={name}
                    className="flex items-center justify-between text-sm text-white/80"
                  >
                    <div className="capitalize">{String(name).replaceAll("_", " ")}</div>
                    <div>{Math.round(Number(val) * 100)}%</div>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="mt-2 text-sm text-white/80 whitespace-pre-wrap">
              {asString(sections._meta)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** -------- Full Report -------- */
function renderFullReport(report: any, onOpenClause?: (id: number) => void) {
  let r = report?.full_report ?? report?.result ?? report;

  if (!isPlainObject(r)) return <Muted>No report.</Muted>;


  if (looksLikeRiskReport(r) && !("risk_report" in r)) {
    r = { risk_report: r };
  }

  const hasAny =
    !!(r as any).summary ||
    !!(r as any).key_clauses ||
    !!(r as any).structured_analysis ||
    !!(r as any).risk_report ||
    !!(r as any).unclear_or_missing ||
    !!(r as any).questions_to_ask_lawyer;

  if (!hasAny) {
    return (
      <div>
        <SectionTitle>Report</SectionTitle>
        <pre className="text-xs text-white/80 whitespace-pre-wrap">{asString(r)}</pre>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {(r as any).summary && (
        <div>
          <SectionTitle>Summary</SectionTitle>

          {typeof (r as any).summary?.summary === "string" ? (
            <div className="text-sm text-white/85 whitespace-pre-wrap">
              {(r as any).summary.summary}
            </div>
          ) : (
            <div className="text-sm text-white/85 whitespace-pre-wrap">
              {asString((r as any).summary)}
            </div>
          )}

          {Array.isArray((r as any).summary?.bullets) &&
            (r as any).summary.bullets.length > 0 && (
              <ul className="mt-3 list-disc pl-5 space-y-1 text-sm text-white/80">
                {(r as any).summary.bullets.slice(0, 25).map((b: any, i: number) => (
                  <li key={i} className="whitespace-pre-wrap">
                    {typeof b === "string" ? b : asString(b)}
                  </li>
                ))}
              </ul>
            )}

          {Array.isArray((r as any).summary?.key_citations) &&
            (r as any).summary.key_citations.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {(r as any).summary.key_citations.slice(0, 15).map((c: number) => (
                  <Pill key={c} onClick={() => onOpenClause?.(Number(c))}>
                    Clause {c}
                  </Pill>
                ))}
              </div>
            )}
        </div>
      )}

      {(r as any).key_clauses && (
        <div>
          <SectionTitle>Key clauses</SectionTitle>
          {renderKeyClauses((r as any).key_clauses, onOpenClause)}
        </div>
      )}

      {(r as any).structured_analysis && (
        <div>
          <SectionTitle>Structured analysis</SectionTitle>
          {renderStructured((r as any).structured_analysis, onOpenClause)}
        </div>
      )}

      {(r as any).risk_report && (
        <div>
          <SectionTitle>Risks & red flags</SectionTitle>
          {renderRisks((r as any).risk_report, onOpenClause)}
        </div>
      )}

      {(r as any).unclear_or_missing && (
        <div>
          <SectionTitle>Unclear / missing</SectionTitle>
          {renderUnclear((r as any).unclear_or_missing, onOpenClause)}
        </div>
      )}

      {(r as any).questions_to_ask_lawyer && (
        <div>
          <SectionTitle>Questions for lawyer</SectionTitle>
          {renderLawyerQuestions((r as any).questions_to_ask_lawyer, onOpenClause)}
        </div>
      )}
    </div>
  );
}

export default function ResultView(props: {
  mode: RunMode;
  result: any;
  onOpenClause?: (id: number) => void;
}) {
  const { mode, result } = props;

  if (!result) return <Muted>No response yet.</Muted>;

  const obj = result?.qa ?? result;

  try {
    return (
      <Card className="bg-white/5 border-white/10">
        <CardContent className="p-4">
          {mode === "qa" && (
            <div className="text-sm text-white/85 whitespace-pre-wrap">
              {typeof obj?.answer === "string"
                ? obj.answer
                : asString(obj?.answer ?? obj)}
            </div>
          )}

          {mode === "summary_only" && (
            <div className="space-y-3">
              <div className="text-sm text-white/85 whitespace-pre-wrap">
                {typeof obj?.summary === "string" ? obj.summary : asString(obj)}
              </div>

              {Array.isArray(obj?.bullets) && obj.bullets.length > 0 && (
                <ul className="list-disc pl-5 space-y-1 text-sm text-white/80">
                  {obj.bullets.slice(0, 25).map((b: any, i: number) => (
                    <li key={i} className="whitespace-pre-wrap">
                      {typeof b === "string" ? b : asString(b)}
                    </li>
                  ))}
                </ul>
              )}

              {Array.isArray(obj?.key_citations) && obj.key_citations.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {obj.key_citations.slice(0, 15).map((c: number) => (
                    <Pill key={c} onClick={() => props.onOpenClause?.(Number(c))}>
                      Clause {c}
                    </Pill>
                  ))}
                </div>
              )}
            </div>
          )}

          {mode === "key_clauses_only" && renderKeyClauses(obj, props.onOpenClause)}
          {mode === "risk_only" && renderRisks(obj, props.onOpenClause)}
          {mode === "structured_only" && renderStructured(obj, props.onOpenClause)}
          {mode === "unclear_only" && renderUnclear(obj, props.onOpenClause)}
          {mode === "lawyer_questions_only" &&
            renderLawyerQuestions(obj, props.onOpenClause)}

          {mode === "full_report" && renderFullReport(result, props.onOpenClause)}
        </CardContent>
      </Card>
    );
  } catch (e: any) {
    return (
      <Card className="bg-white/5 border-white/10">
        <CardContent className="p-4">
          <div className="text-sm text-white/80">
            Render error in ResultView (showing fallback JSON):
          </div>
          <pre className="mt-3 text-xs text-white/70 whitespace-pre-wrap">
            {asString(result)}
          </pre>
        </CardContent>
      </Card>
    );
  }
}