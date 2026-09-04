import type { JobReport } from "../api";
import { Card, SectionLabel } from "./ui";

interface ResultSummaryProps {
  report: JobReport;
  nonCompliantCount: number;
  unverifiedCount: number;
}

export default function ResultSummary({ report, nonCompliantCount, unverifiedCount }: ResultSummaryProps) {
  return (
    <Card className="p-5 sm:p-6 space-y-3">
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
  );
}
