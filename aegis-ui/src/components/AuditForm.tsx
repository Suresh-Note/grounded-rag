import { AlertTriangle, FileText, Loader2, Sparkles } from "lucide-react";
import { Card, SectionLabel } from "./ui";

interface AuditFormProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  jurisdiction: string;
  onJurisdictionChange: (v: string) => void;
  executionYear: number;
  onExecutionYearChange: (v: number) => void;
  rawQuery: string;
  onRawQueryChange: (v: string) => void;
  error: string | null;
  isRunning: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

export default function AuditForm({
  file,
  onFileChange,
  jurisdiction,
  onJurisdictionChange,
  executionYear,
  onExecutionYearChange,
  rawQuery,
  onRawQueryChange,
  error,
  isRunning,
  onSubmit,
}: AuditFormProps) {
  return (
    <Card className="p-5 sm:p-6 space-y-4">
      <SectionLabel>Audit Configuration</SectionLabel>
      <form onSubmit={onSubmit} className="space-y-4">
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
            onChange={(e) => onFileChange(e.target.files?.[0] || null)}
          />
          <FileText className="w-6 h-6 mx-auto mb-2 text-slate-400" />
          <p className="text-sm font-semibold truncate">{file ? file.name : "Select contract PDF"}</p>
          <p className="text-xs text-slate-400 mt-0.5">Click to browse</p>
        </label>

        <div>
          <label htmlFor="jurisdiction" className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">
            Jurisdiction
          </label>
          <select
            id="jurisdiction"
            value={jurisdiction}
            onChange={(e) => onJurisdictionChange(e.target.value)}
            className="w-full text-sm rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 px-3 py-2"
          >
            <option>European Union</option>
            <option>United States</option>
            <option>United Kingdom</option>
            <option>Global Framework Standard</option>
          </select>
        </div>

        <div>
          <label htmlFor="execYear" className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">
            Execution Year
          </label>
          <input
            id="execYear"
            type="number"
            value={executionYear}
            onChange={(e) => onExecutionYearChange(Number(e.target.value))}
            className="w-full text-sm rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 px-3 py-2"
          />
        </div>

        <div>
          <label htmlFor="auditQuery" className="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-1">
            Audit Objective
          </label>
          <textarea
            id="auditQuery"
            value={rawQuery}
            onChange={(e) => onRawQueryChange(e.target.value)}
            rows={3}
            className="w-full text-sm rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-800 px-3 py-2 resize-none"
          />
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs"
          >
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
              <Loader2 className="w-4 h-4 animate-spin" /> Running Audit...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" /> Run Audit
            </>
          )}
        </button>
      </form>
    </Card>
  );
}
