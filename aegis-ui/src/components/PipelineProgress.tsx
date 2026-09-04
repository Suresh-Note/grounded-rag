import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import type { JobState } from "../api";
import { Card, SectionLabel } from "./ui";

const STAGES: { key: string; label: string; threshold: number }[] = [
  { key: "planner", label: "Plan", threshold: 5 },
  { key: "retrieve", label: "Retrieve", threshold: 25 },
  { key: "auditor", label: "Audit", threshold: 55 },
  { key: "critic", label: "Verify", threshold: 75 },
  { key: "finalize_step", label: "Finalize", threshold: 90 },
  { key: "generate_report", label: "Report", threshold: 100 },
];

interface PipelineProgressProps {
  jobState: JobState;
}

export default function PipelineProgress({ jobState }: PipelineProgressProps) {
  const { status, progress_percent: progress, stage, last_message } = jobState;

  return (
    <Card className="p-5 sm:p-6 space-y-4">
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

      <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden" role="progressbar" aria-valuenow={progress}>
        <div
          className={`h-full transition-all duration-500 ${status === "failed" ? "bg-rose-500" : "bg-indigo-600"}`}
          style={{ width: `${status === "completed" ? 100 : progress}%` }}
        />
      </div>

      <ol className="space-y-2" aria-label="Pipeline stages">
        {STAGES.map((s) => {
          const done = status === "completed" || progress > s.threshold || (stage !== s.key && progress >= s.threshold);
          const active = stage === s.key && status !== "completed";
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

      {last_message && (
        <p className="text-xs text-slate-400 border-t border-slate-100 dark:border-white/10 pt-3">{last_message}</p>
      )}
    </Card>
  );
}
