import type { FindingStatus } from "../api";

export const STATUS_STYLES: Record<FindingStatus, { badge: string; dot: string; label: string }> = {
  COMPLIANT: {
    badge: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30",
    dot: "bg-emerald-500",
    label: "Compliant",
  },
  NON_COMPLIANT: {
    badge: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/30",
    dot: "bg-rose-500",
    label: "Non-Compliant",
  },
  UNVERIFIED_EVIDENCE: {
    badge: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30",
    dot: "bg-amber-500",
    label: "Unverified",
  },
};
