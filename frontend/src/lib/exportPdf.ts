import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

type AnyObj = Record<string, any>;

function isObj(v: any): v is AnyObj {
  return v != null && typeof v === "object" && !Array.isArray(v);
}

function safeText(v: any) {
  if (v == null) return "";
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v, null, 2);
  } catch {
    return String(v);
  }
}

function scoreToPct(x: any) {
  if (typeof x !== "number" || Number.isNaN(x)) return "—";
  if (x <= 1.5) return `${Math.round(x * 100)}%`;
  return `${Math.round(x)}%`;
}

function pickReportRoot(result: any) {
  // Prefer full_report if present
  if (isObj(result?.full_report)) return result.full_report;
  if (isObj(result?.result?.full_report)) return result.result.full_report;

  // If already a full report object
  if (
    isObj(result) &&
    (result.summary || result.key_clauses || result.structured_analysis || result.unclear_or_missing)
  ) {
    return result;
  }

  // Fall back to risk_report/qa if that’s all we have
  if (isObj(result?.risk_report)) return result.risk_report;
  if (isObj(result?.qa)) return result.qa;

  return result ?? {};
}

function normalizeKeyClauses(keyClauses: any) {
  const rows: Array<{ section: string; clauseId: string; text: string }> = [];
  if (!isObj(keyClauses)) return rows;

  for (const [section, arr] of Object.entries(keyClauses)) {
    if (!Array.isArray(arr)) continue;
    for (const item of arr) {
      const clauseId =
        item?.clause_id == null ? "—" : String(item.clause_id);
      const text = String(item?.clause_text ?? item?.text ?? item ?? "");
      if (!text) continue;
      rows.push({
        section,
        clauseId,
        text,
      });
    }
  }

  return rows;
}

function normalizeStructured(structured: any) {
  const rows: Array<{ topic: string; answer: string; cites: string }> = [];
  if (!isObj(structured)) return rows;

  for (const [topic, val] of Object.entries(structured)) {
    if (topic === "_meta") continue;
    if (Array.isArray(val)) {
      // other_red_flags etc
      const joined = val
        .slice(0, 5)
        .map((x: any) => `• ${safeText(x?.issue ?? x)}`)
        .join("\n");
      rows.push({ topic, answer: joined || "—", cites: "" });
      continue;
    }

    const answer = String(val?.answer ?? val ?? "");
    const citesArr = Array.isArray(val?.citations) ? val.citations : [];
    const cites = citesArr.length ? citesArr.join(", ") : "";
    if (!answer) continue;
    rows.push({ topic, answer, cites });
  }

  return rows;
}

function normalizeUnclear(unclear: any) {
  if (!Array.isArray(unclear)) return [];
  return unclear.map((x: any) => ({
    clause: x?.clause_id == null ? "—" : String(x.clause_id),
    type: String(x?.issue_type ?? "—"),
    snippet: String(x?.snippet ?? x?.text ?? "—"),
  }));
}

function normalizeLawyerQs(obj: any) {
  const qs =
    obj?.questions_to_ask_lawyer ??
    obj?.lawyer_questions ??
    obj?.questions ??
    null;

  if (!Array.isArray(qs)) return [];
  return qs.map((q: any) => {
    const text = q?.question ?? q?.text ?? q;
    return String(text ?? "");
  }).filter(Boolean);
}

export function exportContractPDF(args: {
  contractId: string;
  filename?: string;
  mode?: string;
  result: any; // lastResult
}) {
  const { contractId, filename, mode, result } = args;

  const doc = new jsPDF({ unit: "pt", format: "a4" });
  const marginX = 40;
  const pageW = doc.internal.pageSize.getWidth();
  const usableW = pageW - marginX * 2;

  // ----- Header -----
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("Contract Analyzer Report", marginX, 52);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);
  doc.text(`Contract ID: ${contractId}`, marginX, 72);
  if (filename) doc.text(`File: ${filename}`, marginX, 86);
  if (mode) doc.text(`Mode: ${mode}`, marginX, 100);

  let cursorY = 120;

  function ensureSpace(needed: number) {
    const pageH = doc.internal.pageSize.getHeight();
    if (cursorY + needed > pageH - 50) {
      doc.addPage();
      cursorY = 60;
    }
  }

  function sectionTitle(title: string) {
    ensureSpace(40);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(title, marginX, cursorY);
    cursorY += 14;
  }

  function sectionText(body: string) {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    const lines = doc.splitTextToSize(body, usableW);
    ensureSpace(lines.length * 12 + 10);
    doc.text(lines, marginX, cursorY);
    cursorY += lines.length * 12 + 10;
  }

  const root = pickReportRoot(result);
  const riskObj = isObj(root?.risk_report) ? root.risk_report : root;

  // ----- Summary -----
  const summary = root?.summary?.summary ?? root?.summary ?? null;
  if (summary) {
    sectionTitle("Summary");
    sectionText(safeText(summary));
  }

  // ----- Key clauses (table) -----
  if (root?.key_clauses) {
    const rows = normalizeKeyClauses(root.key_clauses);
    sectionTitle("Key Clauses");

    if (!rows.length) {
      sectionText("No key clauses found.");
    } else {
      autoTable(doc, {
        startY: cursorY,
        margin: { left: marginX, right: marginX },
        styles: { fontSize: 9, cellPadding: 6, overflow: "linebreak" },
        head: [["Section", "Clause", "Text (snippet)"]],
        body: rows.slice(0, 40).map((r) => [
          r.section,
          r.clauseId,
          r.text.length > 260 ? r.text.slice(0, 260) + "…" : r.text,
        ]),
        columnStyles: {
          0: { cellWidth: 90 },
          1: { cellWidth: 60 },
          2: { cellWidth: usableW - 150 },
        },
      });
      cursorY = (doc as any).lastAutoTable.finalY + 16;
    }
  }

  // ----- Structured analysis (table) -----
  if (root?.structured_analysis) {
    const rows = normalizeStructured(root.structured_analysis);
    sectionTitle("Structured Analysis");

    if (!rows.length) {
      sectionText("No structured analysis found.");
    } else {
      autoTable(doc, {
        startY: cursorY,
        margin: { left: marginX, right: marginX },
        styles: { fontSize: 9, cellPadding: 6, overflow: "linebreak" },
        head: [["Topic", "Answer", "Citations"]],
        body: rows.slice(0, 30).map((r) => [
          r.topic,
          r.answer.length > 350 ? r.answer.slice(0, 350) + "…" : r.answer,
          r.cites || "—",
        ]),
        columnStyles: {
          0: { cellWidth: 110 },
          1: { cellWidth: usableW - 180 },
          2: { cellWidth: 70 },
        },
      });
      cursorY = (doc as any).lastAutoTable.finalY + 16;
    }
  }

  // ----- Unclear / Missing (table) -----
  const unclear = root?.unclear_or_missing ?? root?.unclear ?? null;
  if (unclear) {
    const rows = normalizeUnclear(unclear);
    sectionTitle("Unclear / Missing Areas");

    if (!rows.length) {
      sectionText("No unclear/missing findings.");
    } else {
      autoTable(doc, {
        startY: cursorY,
        margin: { left: marginX, right: marginX },
        styles: { fontSize: 9, cellPadding: 6, overflow: "linebreak" },
        head: [["Clause", "Type", "Snippet"]],
        body: rows.slice(0, 35).map((r) => [
          r.clause,
          r.type,
          r.snippet.length > 320 ? r.snippet.slice(0, 320) + "…" : r.snippet,
        ]),
        columnStyles: {
          0: { cellWidth: 55 },
          1: { cellWidth: 120 },
          2: { cellWidth: usableW - 175 },
        },
      });
      // @ts-ignore
      cursorY = (doc as any).lastAutoTable.finalY + 16;
    }
  }

  // ----- Risks (table) -----
  const present = Array.isArray(riskObj?.present_risks) ? riskObj.present_risks : [];
  if (present.length > 0) {
    sectionTitle("Risks & Red Flags");

    autoTable(doc, {
      startY: cursorY,
      margin: { left: marginX, right: marginX },
      styles: { fontSize: 9, cellPadding: 6 },
      head: [["Risk", "Level", "Confidence", "Clause"]],
      body: present.slice(0, 40).map((r: any) => [
        r?.risk_type ?? r?.title ?? "—",
        String(r?.risk_level ?? "—"),
        typeof r?.confidence === "number"
          ? `${Math.round(r.confidence * 100)}%`
          : "—",
        r?.clause_id != null ? `Clause ${r.clause_id}` : "—",
      ]),
      columnStyles: {
        0: { cellWidth: usableW - 260 },
        1: { cellWidth: 80 },
        2: { cellWidth: 90 },
        3: { cellWidth: 90 },
      },
    });

   
    cursorY = (doc as any).lastAutoTable.finalY + 16;
  }

  // ----- Risk score -----
  if (typeof riskObj?.overall_risk_score !== "undefined") {
    sectionTitle("Risk Score");
    sectionText(
      `Overall risk: ${scoreToPct(riskObj.overall_risk_score)}\nMissing findings: ${
        Array.isArray(riskObj?.missing_risks?.findings)
          ? riskObj.missing_risks.findings.length
          : 0
      }`
    );
  }

  // ----- Lawyer questions -----
  const lawyerQs = normalizeLawyerQs(root);
  if (lawyerQs.length) {
    sectionTitle("Questions to Ask a Lawyer");
    const body = lawyerQs
      .slice(0, 25)
      .map((q, i) => `${i + 1}. ${q}`)
      .join("\n");
    sectionText(body);
  }

  const outName = `contract_${contractId}_${mode ?? "report"}.pdf`;
  doc.save(outName);
}