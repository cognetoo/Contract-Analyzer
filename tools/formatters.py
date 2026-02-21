from typing import Any, Dict, List

def format_summary(summary_obj: Any) -> str:
    if not isinstance(summary_obj, dict):
        return str(summary_obj)

    s = summary_obj.get("summary", "")
    bullets = summary_obj.get("bullets", [])
    citations = summary_obj.get("key_citations", [])

    out = "\n=== CONTRACT SUMMARY ===\n\n"
    out += s + "\n\n"

    if bullets:
        out += "Key Points:\n"
        for b in bullets:
            out += f"- {b}\n"

    if citations:
        out += "\nKey Clauses Referenced: " + ", ".join(map(str, citations))

    return out


def format_key_clauses(obj: Any) -> str:
    if not isinstance(obj, dict):
        return str(obj)

    out = "\n=== KEY CLAUSES ===\n"

    for section, clauses in obj.items():
        out += f"\n{str(section).upper()}:\n"
        if not clauses:
            out += "  Not found\n"
            continue

        for c in clauses:
            cid = c.get("clause_id")
            text = c.get("clause_text", "")
            out += f"\n  Clause {cid}:\n  {text[:500]}...\n"

    return out


def format_structured_analysis(obj):
    if not isinstance(obj, dict):
        return str(obj)

    out = "\n=== STRUCTURED ANALYSIS ===\n"

    # 🔹 Extract meta confidence block (if present)
    meta = obj.get("_meta", {})
    overall_conf = meta.get("overall_confidence")

    if overall_conf is not None:
        out += f"\nOVERALL STRUCTURED ANALYSIS CONFIDENCE: {overall_conf}\n"

        if overall_conf < 0.50:
            out += "Evidence weak across sections.\n"
        elif overall_conf < 0.70:
            out += "Moderate evidence strength.\n"
        else:
            out += "Strong section-level evidence.\n"

        out += "\n"

    # 🔹 Print each section
    for section, data in obj.items():

        if section == "_meta":
            continue 

        if isinstance(data, dict):
            answer = data.get("answer", "Not found")
            citations = data.get("citations", [])

            out += f"\n{section.upper()}:\n{answer}\n"

            if citations:
                out += f"(Citations: {', '.join(map(str, citations))})\n"

        elif isinstance(data, list): 
            out += f"\n{section.upper()}:\n"
            for item in data:
                issue = item.get("issue")
                cites = item.get("citations", [])
                out += f"- {issue}\n"
                if cites:
                    out += f"  (Citations: {', '.join(map(str, cites))})\n"

    return out


def format_unclear(issues: Any) -> str:
    if not isinstance(issues, list):
        return str(issues)

    out = "\n=== UNCLEAR / MISSING CLAUSES ===\n"

    if not issues:
        return out + "\nNo vague or missing clauses detected.\n"

    for i in issues:
        out += f"\nClause {i.get('clause_id')} | {i.get('issue_type')}\n"
        out += f"{i.get('snippet', '')[:400]}...\n"

    return out


def format_lawyer_questions(qs: Any) -> str:
    if not isinstance(qs, list):
        return str(qs)

    out = "\n=== QUESTIONS TO ASK A LAWYER ===\n"

    for i, q in enumerate(qs, 1):
        out += f"\n{i}. {q.get('question')}\n"
        out += f"   Reason: {q.get('reason')}\n"
        cites = q.get("citations", [])
        if cites:
            out += f"   (Citations: {', '.join(map(str, cites))})\n"

    return out


def format_risk_report(risk_obj: Any) -> str:
    
    if not isinstance(risk_obj, dict):
        return str(risk_obj)

    out = "\n=== FULL CONTRACT RISK REPORT ===\n"

    overall = risk_obj.get("overall_risk_score")
    present = risk_obj.get("present_risks", [])
    missing = risk_obj.get("missing_risks", {})
    additional = risk_obj.get("additional_risks", [])

    overall = risk_obj.get("overall_risk_score")

    if overall is not None:
        out += f"\nOVERALL CONTRACT RISK SCORE: {overall}\n"
        if overall > 0.75:
            out += " High overall contract risk!!\n"
        elif overall > 0.50:
            out += "Moderate contract risk.\n"
        else:
            out += "✓  Low overall contract risk.\n"

    if present:
        out += "\nPRESENT RISKS:\n"
        for r in present:
            out += f"\nClause {r.get('clause_id')} | {r.get('risk_type')} | {r.get('risk_level')}\n"

            conf = r.get("confidence")
            if conf is not None:
                out += f"Confidence: {conf}\n"

            out += f"Explanation: {r.get('explanation')}\n"
            out += f"Mitigation: {r.get('mitigation')}\n"

    if missing:
        findings = missing.get("findings", [])
        if findings:
            out += "\nMISSING CLAUSES:\n"
            for f in findings:
                out += f"- {f}\n"

    if additional:
        out += "\nADDITIONAL RISKS:\n"
        for r in additional:
            out += f"- {r.get('risk_type')} ({r.get('risk_level')})\n"

    return out


def format_full_report(report: Any) -> str:
    if not isinstance(report, dict):
        return str(report)

    out = "\n==============================\n"
    out += " COMPLETE CONTRACT REPORT\n"
    out += "==============================\n"

    out += format_summary(report.get("summary", {}))
    out += "\n\n"
    out += format_key_clauses(report.get("key_clauses", {}))
    out += "\n\n"
    out += format_structured_analysis(report.get("structured_analysis", {}))
    out += "\n\n"
    out += format_unclear(report.get("unclear_or_missing", []))
    out += "\n\n"
    out += format_lawyer_questions(report.get("questions_to_ask_lawyer", []))

    return out


def format_qa(qa_obj: Any) -> str:
    # qa_obj might be dict or plain string
    if not isinstance(qa_obj, dict):
        return str(qa_obj)

    ans = qa_obj.get("answer", "")
    conf = qa_obj.get("confidence", None)
    method = qa_obj.get("method", "")
    cites = qa_obj.get("citations", [])

    out = ""
    if method:
        out += f"[QA via {method}] "
    if conf is not None:
        out += f"(confidence: {conf})\n\n"
        
        ##warnings for low confidence
        if conf < 0.45:
            out += "Very low confidence. Retrieved clauses weakly match the query.\n"
        elif conf <0.60:
            out += "Moderate confidence. Consider reviewing cited clauses.\n"
        
        out += "\n"

    out += str(ans).strip()

    if cites:
        out += "\n\nCitations: " + ", ".join(map(str, cites))

    return out