import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { RunMode } from "@/components/layout/Workspace";

function clamp01(n: number) {
  if (Number.isNaN(n)) return 0;
  return Math.max(0, Math.min(1, n));
}

export default function Insights(props: {
  mode: RunMode;
  activeId: string;
  method?: string;
  confidence?: number;
  citations?: number[];
  onOpenRiskAnalytics: () => void;
}) {
  const showQaInsights = props.mode === "qa";

  const conf =
    typeof props.confidence === "number" ? clamp01(props.confidence) : null;

  const pct = conf === null ? 0 : Math.round(conf * 100);

  return (
    <div className="space-y-4">
      {/* Premium action */}
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="text-base">Analytics</CardTitle>
          <div className="text-xs text-white/60">
            Open full-screen dashboard (KPIs + charts).
          </div>
        </CardHeader>
        <CardContent>
          <Button className="w-full" onClick={props.onOpenRiskAnalytics}>
            View Risk Analytics →
          </Button>
        </CardContent>
      </Card>

      {/* Only show confidence + citations in QA mode */}
      {showQaInsights && (
        <>
          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <CardTitle className="text-base">Insights</CardTitle>
              <div className="text-xs text-white/60">
                Confidence + retrieval signals (best for QA mode).
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              <div>
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-white/70">Confidence</span>
                  <span className="text-white/80">
                    {conf === null ? "—" : `${pct}%`}
                  </span>
                </div>

                <Progress value={pct} />

                <div className="text-xs text-white/60 mt-2">
                  Based on retrieval strength + method.
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="text-sm text-white/70">Method</div>
                <Badge variant="secondary" className="bg-white/10">
                  {props.method ?? "—"}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white/5 border-white/10">
            <CardHeader>
              <CardTitle className="text-base">Top cited clauses</CardTitle>
              <div className="text-xs text-white/60">(From citations)</div>
            </CardHeader>

            <CardContent>
              {props.citations && props.citations.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {props.citations.slice(0, 12).map((c) => (
                    <span
                      key={c}
                      className="text-xs px-2 py-1 rounded-full bg-white/10 border border-white/10"
                    >
                      Clause {c}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-white/60">No citations yet.</div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Always show active session */}
      <Card className="bg-white/5 border-white/10">
        <CardHeader>
          <CardTitle className="text-base">Active session</CardTitle>
        </CardHeader>
        <CardContent className="text-xs text-white/70">
          {props.activeId ? props.activeId : "None"}
        </CardContent>
      </Card>
    </div>
  );
}