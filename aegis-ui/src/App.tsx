import { useEffect, useMemo, useState } from "react";
import {
  FileText,
  Sparkles,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Moon,
  Sun,
  Download,
  Copy,
  Check,
  ShieldCheck,
} from "lucide-react";
import { submitAudit, getJobState, getDownloadUrl, getStreamUrl, type JobState, type Finding, type FindingStatus } from "./api";

const STAGES: { key: string; label: string; threshold: number }[] = [
  { key: "planner", label: "Plan", threshold: 5 },
  { key: "retrieve", label: "Retrieve", threshold: 25 },
  { key: "auditor", label: "Audit", threshold: 55 },
  { key: "critic", label: "Verify", threshold: 75 },
  { key: "finalize_step", label: "Finalize", threshold: 90 },
  { key: "generate_report", label: "Report", threshold: 100 },
];

const STATUS_STYLES: Record<FindingStatus, { badge: string; dot: string; label: string }> = {
  COMPLIANT: { badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30", dot: "bg-emerald-500", label: "Compliant" },
  NON_COMPLIANT: { badge: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30", dot: "bg-rose-500", label: "Non-Compliant" },
  UNVERIFIED_EVIDENCE: { badge: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30", dot: "bg-amber-500", label: "Unverified" },
};

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded-2xl border border-slate-200 bg-white dark:border-white/10 dark:bg-slate-900 ${className}`}>
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">{children}</h3>;
}

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const [file, setFile] = useState<File | null>(null);
  const [jurisdiction, setJurisdiction] = useState("European Union");
  const [executionYear, setExecutionYear] = useState(2026);
  const [rawQuery, setRawQuery] = useState(
    "Perform a comprehensive regulatory compliance audit on data retention, cross-border transfer, and liability exposure."
  );

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobState, setJobState] = useState<JobState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const status = jobState?.status;
  const isTerminal = status === "completed" || status === "failed";
  const isRunning = submitting || (Boolean(jobId) && !isTerminal);

  useEffect(() => {
    if (!jobId || isTerminal) return;
    let cancelled = false;

    // Fetch current state immediately — the SSE stream only carries events
    // published from the moment we connect onward, so a fresh page load or a
    // reconnect needs this to catch up on whatever already happened.
    getJobState(jobId)
      .then((data) => {
        if (!cancelled) setJobState(data);
      })
      .catch(() => {});

    const source = new EventSource(getStreamUrl(jobId));
    source.onmessage = (event) => {
      try {
        const update = JSON.parse(event.data) as Partial<JobState>;
        setJobState((prev) => ({ ...(prev as JobState), ...update }) as JobState);
      } catch {
        // ignore a malformed event; the next one will still arrive
      }
    };
    // EventSource retries automatically on transient connection drops —
    // nothing to do here beyond letting it.
    source.onerror = () => {};

    return () => {
      cancelled = true;
      source.close();
    };
  }, [jobId, isTerminal]);

  const report = jobState?.payload?.job_report;
  const findings: Finding[] = useMemo(
    () => jobState?.payload?.validated_drafts ?? report?.raw_findings_array ?? [],
    [jobState, report]
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [findings.length]);

  const nonCompliantCount = findings.filter((f) => f.finding_status === "NON_COMPLIANT").length;
  const unverifiedCount = findings.filter((f) => f.finding_status === "UNVERIFIED_EVIDENCE").length;
  const cleanCompletion = status === "completed" && findings.length === 0;
  const selected = findings[selectedIndex];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || isRunning) return;
    setError(null);
    setSubmitting(true);
    setJobState(null);
    setJobId(null);
    try {
      const res = await submitAudit(file, rawQuery, jurisdiction, executionYear);
      setJobId(res.job_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start audit.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyQuote = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const progress = jobState?.progress_percent ?? 0;
  const isDark = theme === "dark";

  return (
    <div className={`h-screen flex flex-col ${isDark ? "bg-slate-950 text-slate-100" : "bg-slate-50 text-slate-900"}`}>
      {/* Header */}
      <header className="flex-shrink-0 border-b border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">GroundedRAG</h1>
              <p className="text-xs text-slate-500 dark:text-slate-400">Multi-Agent RAG with Hallucination Mitigation</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {jobId && status === "completed" && (
              <a
                href={getDownloadUrl(jobId)}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition-colors"
              >
                <Download className="w-4 h-4" /> Download Report
              </a>
            )}
            <button
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className="p-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      {/* Main app shell */}
      <div className="flex-1 max-w-[1600px] w-full mx-auto p-6 flex gap-6 overflow-hidden">
        {/* LEFT: Configuration + Progress + Summary */}
        <div className="w-[380px] flex-shrink-0 flex flex-col gap-6 overflow-y-auto pr-1">
          <Card className="p-6 space-y-4">
            <SectionLabel>Audit Configuration</SectionLabel>
            <form onSubmit={handleSubmit} className="space-y-4">
              <label
                htmlFor="filePicker"
                className={`block border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
                  file
                    ? "border-indigo-400 bg-indigo-50 dark:bg-indigo-500/10"
                    : "border-slate-300 dark:border-slate-700 hover:border-indigo-300"
                }`}
              >
                <input
                  id="filePicker"
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <FileText className="w-6 h-6 mx-auto mb-2 text-slate-400" />
                <p className="text-sm font-semibold truncate">{file ? file.name : "Select contract PDF"}</p>
                <p className="text-xs text-slate-400 mt-0.5">Click to browse</p>
              </label>

              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">Jurisdiction</label>
                <select
                  value={jurisdiction}
                  onChange={(e) => setJurisdiction(e.target.value)}
                  className="w-full text-sm rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 px-3 py-2"
                >
                  <option>European Union</option>
                  <option>United States</option>
                  <option>United Kingdom</option>
                  <option>Global Framework Standard</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">Execution Year</label>
                <input
                  type="number"
                  value={executionYear}
                  onChange={(e) => setExecutionYear(Number(e.target.value))}
                  className="w-full text-sm rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 px-3 py-2"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">Audit Objective</label>
                <textarea
                  value={rawQuery}
                  onChange={(e) => setRawQuery(e.target.value)}
                  rows={3}
                  className="w-full text-sm rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 px-3 py-2 resize-none"
                />
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={!file || isRunning}
                className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
              >
                {isRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Running Audit…
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" /> Run Audit
                  </>
                )}
              </button>
            </form>
          </Card>

          {jobId && (
            <Card className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <SectionLabel>Pipeline Progress</SectionLabel>
                {status === "failed" ? (
                  <span className="flex items-center gap-1 text-xs font-bold text-rose-500">
                    <XCircle className="w-3.5 h-3.5" /> Failed
                  </span>
                ) : status === "completed" ? (
                  <span className="flex items-center gap-1 text-xs font-bold text-emerald-500">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Complete
                  </span>
                ) : (
                  <span className="text-xs font-mono text-slate-400">{Math.round(progress)}%</span>
                )}
              </div>

              <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${status === "failed" ? "bg-rose-500" : "bg-indigo-600"}`}
                  style={{ width: `${status === "completed" ? 100 : progress}%` }}
                />
              </div>

              <ol className="space-y-2">
                {STAGES.map((s) => {
                  const done = status === "completed" || progress > s.threshold || (jobState?.stage !== s.key && progress >= s.threshold);
                  const active = jobState?.stage === s.key && status !== "completed";
                  return (
                    <li key={s.key} className="flex items-center gap-2.5 text-sm">
                      {done ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      ) : active ? (
                        <Loader2 className="w-4 h-4 text-indigo-500 animate-spin flex-shrink-0" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border-2 border-slate-200 dark:border-slate-700 flex-shrink-0" />
                      )}
                      <span className={done || active ? "font-semibold" : "text-slate-400"}>{s.label}</span>
                    </li>
                  );
                })}
              </ol>

              {jobState?.last_message && (
                <p className="text-xs text-slate-400 border-t border-slate-100 dark:border-white/10 pt-3">{jobState.last_message}</p>
              )}
            </Card>
          )}

          {status === "completed" && report && (
            <Card className="p-6 space-y-3">
              <SectionLabel>Result Summary</SectionLabel>
              <div className="flex items-baseline justify-between">
                <span className="text-sm text-slate-500 dark:text-slate-400">Risk Score</span>
                <span
                  className={`text-2xl font-black ${
                    report.risk_score > 60 ? "text-rose-500" : report.risk_score > 35 ? "text-amber-500" : "text-emerald-500"
                  }`}
                >
                  {report.risk_score}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">Verdict</span>
                <span className="font-semibold">{report.status?.replace(/_/g, " ")}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">Non-compliant findings</span>
                <span className="font-semibold text-rose-500">{nonCompliantCount}</span>
              </div>
              {unverifiedCount > 0 && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500 dark:text-slate-400">Unverified findings</span>
                  <span className="font-semibold text-amber-500">{unverifiedCount}</span>
                </div>
              )}
            </Card>
          )}
        </div>

        {/* RIGHT: Findings list + detail */}
        <div className="flex-1 flex gap-6 overflow-hidden">
          <Card className="w-[340px] flex-shrink-0 flex flex-col overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 dark:border-white/10 flex items-center justify-between">
              <SectionLabel>Findings {findings.length > 0 && `(${findings.length})`}</SectionLabel>
            </div>
            <div className="flex-1 overflow-y-auto">
              {!jobId ? (
                <div className="p-6 text-sm text-slate-400 text-center">Upload a contract and run an audit to see findings here.</div>
              ) : cleanCompletion ? (
                <div className="p-6 text-center space-y-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
                  <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">No issues found</p>
                </div>
              ) : findings.length === 0 ? (
                <div className="p-6 text-sm text-slate-400 text-center">Waiting for findings…</div>
              ) : (
                findings.map((f, idx) => {
                  const s = STATUS_STYLES[f.finding_status] ?? STATUS_STYLES.UNVERIFIED_EVIDENCE;
                  const isSelected = idx === selectedIndex;
                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedIndex(idx)}
                      className={`w-full text-left px-5 py-4 border-b border-slate-100 dark:border-white/5 transition-colors ${
                        isSelected ? "bg-indigo-50 dark:bg-indigo-500/10" : "hover:bg-slate-50 dark:hover:bg-white/5"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${s.badge}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} /> {s.label}
                        </span>
                        <span className="text-[11px] font-mono text-slate-400">Pg {f.evidence_location?.page_number || "—"}</span>
                      </div>
                      <p className="text-sm font-semibold leading-snug line-clamp-2">{f.parameter || f.rule_id}</p>
                    </button>
                  );
                })
              )}
            </div>
          </Card>

          <Card className="flex-1 overflow-y-auto p-6">
            {selected ? (
              <div className="space-y-5 max-w-2xl">
                <div className="flex items-center justify-between">
                  <span
                    className={`inline-flex items-center gap-1.5 text-xs font-bold uppercase px-2.5 py-1 rounded-full border ${
                      (STATUS_STYLES[selected.finding_status] ?? STATUS_STYLES.UNVERIFIED_EVIDENCE).badge
                    }`}
                  >
                    {(STATUS_STYLES[selected.finding_status] ?? STATUS_STYLES.UNVERIFIED_EVIDENCE).label}
                  </span>
                  {selected.reconciled_conflict && (
                    <span className="text-xs font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
                      <AlertTriangle className="w-3.5 h-3.5" /> Conflict reconciled conservatively
                    </span>
                  )}
                </div>

                <h2 className="text-xl font-bold leading-snug">{selected.parameter || selected.rule_id}</h2>
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{selected.analysis}</p>

                <div>
                  <div className="flex items-center justify-between mb-2">
                    <SectionLabel>Verbatim Evidence</SectionLabel>
                    {selected.evidence_quote && (
                      <button
                        onClick={() => handleCopyQuote(selected.evidence_quote)}
                        className="flex items-center gap-1 text-xs text-slate-400 hover:text-indigo-500 transition-colors"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                        {copied ? "Copied" : "Copy"}
                      </button>
                    )}
                  </div>
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-white/10">
                    <p className="text-sm italic leading-relaxed">
                      {selected.evidence_quote ? `"${selected.evidence_quote}"` : "No evidence quote was extracted for this finding."}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <SectionLabel>Source</SectionLabel>
                    <p className="mt-1 font-mono text-xs">
                      {selected.evidence_location?.document_name || "—"} · Page {selected.evidence_location?.page_number || "—"}
                    </p>
                  </div>
                  <div>
                    <SectionLabel>Confidence</SectionLabel>
                    <p className="mt-1 font-mono text-xs">{Math.round((selected.confidence ?? 0) * 100)}%</p>
                  </div>
                </div>

                <div>
                  <SectionLabel>Remediation</SectionLabel>
                  <p className={`mt-1 text-sm ${selected.remediation ? "" : "italic text-slate-400"}`}>
                    {selected.remediation || "No automated remediation suggestion is available for this finding — review manually against your compliance policy."}
                  </p>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-slate-400">
                Select a finding to inspect its evidence and grounding.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
