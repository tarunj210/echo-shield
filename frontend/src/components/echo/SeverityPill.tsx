const styles: Record<string, string> = {
    INFO:     "bg-sev-info/15 text-sev-info border-sev-info/30",
    LOW:      "bg-sev-low/15 text-sev-low border-sev-low/30",
    MEDIUM:   "bg-sev-medium/15 text-sev-medium border-sev-medium/30",
    HIGH:     "bg-sev-high/15 text-sev-high border-sev-high/40",
    CRITICAL: "bg-sev-critical/20 text-sev-critical border-sev-critical/50",
  };
  
  export function SeverityPill({ severity }: { severity: string | null | undefined }) {
    const s = severity ?? "INFO";
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider ${styles[s] ?? styles.INFO}`}
      >
        <span className="size-1.5 rounded-full bg-current" />
        {s}
      </span>
    );
  }
  