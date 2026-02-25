export type RiskItem = {
  risk_type?: string;
  risk_level?: string;
  clause_id?: number;
  confidence?: number;
};

export function extractRiskReport(result: any) {
  const root = result?.full_report ?? result?.result ?? result;
  const rr = root?.risk_report ?? root?.risk_report?.risk_report ?? root?.risk_report ?? null;


  const obj = rr?.risk_report ?? rr ?? null;

  if (!obj) return null;

  const present: RiskItem[] = Array.isArray(obj.present_risks) ? obj.present_risks : [];
  const additional: RiskItem[] = Array.isArray(obj.additional_risks) ? obj.additional_risks : [];
  const missing = obj.missing_risks ?? null;

  const overallRiskScore =
    typeof obj.overall_risk_score === "number" ? obj.overall_risk_score : undefined;

  const overallRiskLevel =
    typeof obj.overall_risk_level === "string" ? obj.overall_risk_level : undefined;

  const missingFindings: string[] = Array.isArray(missing?.findings) ? missing.findings : [];

  return {
    overallRiskScore,
    overallRiskLevel,
    present,
    additional,
    missing,
    missingFindings,
  };
}

export function countBy(arr: any[], key: string) {
  const map: Record<string, number> = {};
  for (const it of arr) {
    const k = String((it as any)?.[key] ?? "Unknown");
    map[k] = (map[k] ?? 0) + 1;
  }
  return map;
}

export function topEntries(map: Record<string, number>, n: number) {
  return Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, n);
}