import { Download, Moon, ShieldCheck, Sun } from "lucide-react";
import { getDownloadUrl } from "../api";

interface HeaderProps {
  isDark: boolean;
  onToggleTheme: () => void;
  jobId: string | null;
  status: string | undefined;
}

export default function Header({ isDark, onToggleTheme, jobId, status }: HeaderProps) {
  return (
    <header className="flex-shrink-0 border-b border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">GroundedRAG</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">
              Multi-Agent RAG with Hallucination Mitigation
            </p>
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
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Download Report</span>
              <span className="sm:hidden">PDF</span>
            </a>
          )}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-lg border border-slate-200 dark:border-white/10 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/5 transition-colors"
            aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </header>
  );
}
