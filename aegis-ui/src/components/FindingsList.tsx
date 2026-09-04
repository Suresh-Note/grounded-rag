import { useCallback, useRef } from "react";
import { CheckCircle2 } from "lucide-react";
import type { Finding } from "../api";
import { STATUS_STYLES } from "./constants";
import { Card, FindingSkeleton, SectionLabel } from "./ui";

interface FindingsListProps {
  findings: Finding[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  jobId: string | null;
  isComplete: boolean;
  isWaiting: boolean;
}

export default function FindingsList({ findings, selectedIndex, onSelect, jobId, isComplete, isWaiting }: FindingsListProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (findings.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        onSelect(Math.min(selectedIndex + 1, findings.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        onSelect(Math.max(selectedIndex - 1, 0));
      }
    },
    [findings.length, selectedIndex, onSelect],
  );

  const cleanCompletion = isComplete && findings.length === 0;

  return (
    <Card className="w-full lg:w-[340px] flex-shrink-0 flex flex-col overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-white/10 flex items-center justify-between">
        <SectionLabel>Findings {findings.length > 0 && `(${findings.length})`}</SectionLabel>
      </div>
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto focus:outline-none"
        role="listbox"
        aria-label="Audit findings"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {!jobId ? (
          <div className="p-6 text-sm text-slate-400 text-center">Upload a contract and run an audit to see findings here.</div>
        ) : cleanCompletion ? (
          <div className="p-6 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto" />
            <p className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">No issues found</p>
          </div>
        ) : findings.length === 0 && isWaiting ? (
          <>
            <FindingSkeleton />
            <FindingSkeleton />
            <FindingSkeleton />
          </>
        ) : findings.length === 0 ? (
          <div className="p-6 text-sm text-slate-400 text-center">Waiting for findings...</div>
        ) : (
          findings.map((f, idx) => {
            const s = STATUS_STYLES[f.finding_status] ?? STATUS_STYLES.UNVERIFIED_EVIDENCE;
            const isSelected = idx === selectedIndex;
            return (
              <button
                key={idx}
                role="option"
                aria-selected={isSelected}
                onClick={() => onSelect(idx)}
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
  );
}
