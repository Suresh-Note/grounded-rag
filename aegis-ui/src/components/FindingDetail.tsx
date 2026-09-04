import { useState } from "react";
import { AlertTriangle, Check, Copy } from "lucide-react";
import type { Finding } from "../api";
import { STATUS_STYLES } from "./constants";
import { Card, SectionLabel } from "./ui";

interface FindingDetailProps {
  finding: Finding | undefined;
}

export default function FindingDetail({ finding }: FindingDetailProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyQuote = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (!finding) {
    return (
      <Card className="flex-1 overflow-y-auto p-6">
        <div className="h-full flex items-center justify-center text-sm text-slate-400">
          Select a finding to inspect its evidence and grounding.
        </div>
      </Card>
    );
  }

  const style = STATUS_STYLES[finding.finding_status] ?? STATUS_STYLES.UNVERIFIED_EVIDENCE;

  return (
    <Card className="flex-1 overflow-y-auto p-5 sm:p-6">
      <div className="space-y-5 max-w-2xl">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <span className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase px-2.5 py-1 rounded-full border ${style.badge}`}>
            {style.label}
          </span>
          {finding.reconciled_conflict && (
            <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" /> Conflict reconciled conservatively
            </span>
          )}
        </div>

        <h2 className="text-xl font-bold leading-snug">{finding.parameter || finding.rule_id}</h2>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{finding.analysis}</p>

        <div>
          <div className="flex items-center justify-between mb-2">
            <SectionLabel>Verbatim Evidence</SectionLabel>
            {finding.evidence_quote && (
              <button
                onClick={() => handleCopyQuote(finding.evidence_quote)}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-indigo-500 transition-colors"
                aria-label="Copy evidence quote"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copied" : "Copy"}
              </button>
            )}
          </div>
          <blockquote className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-white/10">
            <p className="text-sm italic leading-relaxed">
              {finding.evidence_quote ? `"${finding.evidence_quote}"` : "No evidence quote was extracted for this finding."}
            </p>
          </blockquote>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <SectionLabel>Source</SectionLabel>
            <p className="mt-1 font-mono text-xs">
              {finding.evidence_location?.document_name || "—"} · Page {finding.evidence_location?.page_number || "—"}
            </p>
          </div>
          <div>
            <SectionLabel>Confidence</SectionLabel>
            <p className="mt-1 font-mono text-xs">{Math.round((finding.confidence ?? 0) * 100)}%</p>
          </div>
        </div>

        <div>
          <SectionLabel>Remediation</SectionLabel>
          <p className={`mt-1 text-sm ${finding.remediation ? "" : "italic text-slate-400"}`}>
            {finding.remediation ||
              "No automated remediation suggestion is available for this finding — review manually against your compliance policy."}
          </p>
        </div>
      </div>
    </Card>
  );
}
