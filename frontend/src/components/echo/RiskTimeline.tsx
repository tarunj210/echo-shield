import type { TemporalDrift } from "@/lib/echo/types";
import { SeverityPill } from "./SeverityPill";

const SEV_BAR: Record<string, string> = {
  INFO: "bg-sev-info",
  LOW: "bg-sev-low",
  MEDIUM: "bg-sev-medium",
  HIGH: "bg-sev-high",
  CRITICAL: "bg-sev-critical",
};

function shortDate(s: string) {
  return new Date(s).toLocaleDateString("en-AU", { month: "short", day: "numeric" });
}

export function RiskTimeline({ drifts }: { drifts: TemporalDrift[] }) {
  const chrono = [...drifts].sort(
    (a, b) => +new Date(a.currentWindowStart) - +new Date(b.currentWindowStart),
  );
  const max = Math.max(100, ...chrono.map((d) => d.driftScore));

  return (
    <div className="space-y-2">
      {chrono.map((d) => {
        const pct = (d.driftScore / max) * 100;
        return (
          <div
            key={d.currentWindowStart}
            className="grid grid-cols-[110px_1fr_auto] items-center gap-3 rounded-md border border-border/60 bg-surface-1 px-3 py-2"
          >
            <div className="font-mono text-[11px] text-muted-foreground">
              {shortDate(d.currentWindowStart)} → {shortDate(d.currentWindowEnd)}
            </div>
            <div className="relative h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full ${SEV_BAR[d.severity] ?? "bg-primary"} transition-all`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm tabular text-foreground">
                {d.driftScore.toFixed(1)}
              </span>
              <SeverityPill severity={d.severity} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
