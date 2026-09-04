import { useEffect, useMemo, useState } from "react";
import { submitAudit, getJobState, getStreamUrl, type JobState, type Finding } from "./api";
import Header from "./components/Header";
import AuditForm from "./components/AuditForm";
import PipelineProgress from "./components/PipelineProgress";
import ResultSummary from "./components/ResultSummary";
import FindingsList from "./components/FindingsList";
import FindingDetail from "./components/FindingDetail";

export default function App() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const [file, setFile] = useState<File | null>(null);
  const [jurisdiction, setJurisdiction] = useState("European Union");
  const [executionYear, setExecutionYear] = useState(2026);
  const [rawQuery, setRawQuery] = useState(
    "Perform a comprehensive regulatory compliance audit on data retention, cross-border transfer, and liability exposure.",
  );

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobState, setJobState] = useState<JobState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const status = jobState?.status;
  const isTerminal = status === "completed" || status === "failed";
  const isRunning = submitting || (Boolean(jobId) && !isTerminal);

  useEffect(() => {
    if (!jobId || isTerminal) return;
    let cancelled = false;

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
        /* ignore malformed event */
      }
    };
    source.onerror = () => {};

    return () => {
      cancelled = true;
      source.close();
    };
  }, [jobId, isTerminal]);

  const report = jobState?.payload?.job_report;
  const findings: Finding[] = useMemo(
    () => jobState?.payload?.validated_drafts ?? report?.raw_findings_array ?? [],
    [jobState, report],
  );

  useEffect(() => {
    setSelectedIndex(0);
  }, [findings.length]);

  const nonCompliantCount = findings.filter((f) => f.finding_status === "NON_COMPLIANT").length;
  const unverifiedCount = findings.filter((f) => f.finding_status === "UNVERIFIED_EVIDENCE").length;
  const isDark = theme === "dark";

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

  return (
    <div className={`h-screen flex flex-col ${isDark ? "bg-slate-950 text-slate-100" : "bg-slate-50 text-slate-900"}`}>
      <Header isDark={isDark} onToggleTheme={() => setTheme(isDark ? "light" : "dark")} jobId={jobId} status={status} />

      <div className="flex-1 max-w-[1600px] w-full mx-auto p-4 sm:p-6 flex flex-col lg:flex-row gap-4 sm:gap-6 overflow-hidden">
        {/* LEFT: Config + Progress + Summary */}
        <div className="w-full lg:w-[380px] flex-shrink-0 flex flex-col gap-4 sm:gap-6 overflow-y-auto lg:pr-1">
          <AuditForm
            file={file}
            onFileChange={setFile}
            jurisdiction={jurisdiction}
            onJurisdictionChange={setJurisdiction}
            executionYear={executionYear}
            onExecutionYearChange={setExecutionYear}
            rawQuery={rawQuery}
            onRawQueryChange={setRawQuery}
            error={error}
            isRunning={isRunning}
            onSubmit={handleSubmit}
          />

          {jobId && jobState && <PipelineProgress jobState={jobState} />}

          {status === "completed" && report && (
            <ResultSummary report={report} nonCompliantCount={nonCompliantCount} unverifiedCount={unverifiedCount} />
          )}
        </div>

        {/* RIGHT: Findings list + detail */}
        <div className="flex-1 flex flex-col lg:flex-row gap-4 sm:gap-6 overflow-hidden min-h-0">
          <FindingsList
            findings={findings}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
            jobId={jobId}
            isComplete={status === "completed"}
            isWaiting={isRunning && findings.length === 0}
          />

          <div className="hidden lg:flex flex-1 min-w-0">
            <FindingDetail finding={findings[selectedIndex]} />
          </div>

          {/* Mobile: show detail below list when a finding is selected */}
          {findings[selectedIndex] && (
            <div className="lg:hidden">
              <FindingDetail finding={findings[selectedIndex]} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
