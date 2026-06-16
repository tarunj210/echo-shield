import { useMemo, useState } from "react";
import type {
  SessionSummaryGraph,
  SessionSummaryNode,
} from "@/lib/echo/types";

type Props = {
  graph: SessionSummaryGraph;
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  domainStartTime: number;
  domainEndTime: number;
};

const WIDTH = 1120;
const LEFT = 210;
const RIGHT = 40;
const TOP = 52;
const BOTTOM = 72;
const LANE_HEIGHT = 78;

export function SessionBubbleTimeline({
  graph,
  selectedSessionId,
  onSelectSession,
  domainStartTime,
  domainEndTime,
}: Props) {
  const [hoveredSessionId, setHoveredSessionId] = useState<string | null>(null);

  const model = useMemo(() => {
    const nodes = [...graph.nodes].sort(
      (a, b) =>
        new Date(a.sessionStart).getTime() -
        new Date(b.sessionStart).getTime(),
    );

    const topics = Array.from(
      new Set(
        nodes.map((node) => node.dominantParentTopic || "General / Mixed"),
      ),
    ).sort();

    const safeMin = Number.isFinite(domainStartTime)
      ? domainStartTime
      : Date.now() - 30 * 24 * 60 * 60 * 1000;

    const safeMax =
      Number.isFinite(domainEndTime) && domainEndTime > safeMin
        ? domainEndTime
        : safeMin + 24 * 60 * 60 * 1000;

    const height = TOP + Math.max(1, topics.length) * LANE_HEIGHT + BOTTOM;
    const plotWidth = WIDTH - LEFT - RIGHT;

    const topicToY = new Map(
      topics.map((topic, index) => [
        topic,
        TOP + index * LANE_HEIGHT + LANE_HEIGHT / 2,
      ]),
    );

    const positionedNodes = nodes.map((node) => {
      const sessionTime = new Date(node.sessionStart).getTime();

      const x =
        LEFT + ((sessionTime - safeMin) / (safeMax - safeMin)) * plotWidth;

      const baseY =
        topicToY.get(node.dominantParentTopic || "General / Mixed") ??
        TOP + LANE_HEIGHT / 2;

      const jitter = ((node.sessionIndex % 3) - 1) * 9;
      const y = baseY + jitter;

      const radius = clamp(Math.sqrt(node.durationMinutes || 1) * 1.35, 9, 34);

      return {
        ...node,
        x: clamp(x, LEFT, WIDTH - RIGHT),
        y,
        radius,
      };
    });

    const rangeDays = (safeMax - safeMin) / (24 * 60 * 60 * 1000);

    const ticks = Array.from({ length: 5 }).map((_, index) => {
    const ratio = index / 4;
    const time = safeMin + (safeMax - safeMin) * ratio;

    return {
        id: `${index}-${Math.round(time)}`,
        x: LEFT + ratio * plotWidth,
        label: formatDateTick(time, rangeDays),
    };
    });

    return {
      nodes: positionedNodes,
      topics,
      topicToY,
      ticks,
      height,
    };
  }, [graph, domainStartTime, domainEndTime]);

  const selectedNode =
    graph.nodes.find((node) => node.id === selectedSessionId) ?? null;

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-border bg-background">
        <svg
          viewBox={`0 0 ${WIDTH} ${model.height}`}
          className="min-w-[980px]"
          role="img"
          aria-label="Session exposure timeline"
        >
          <defs>
            <filter id="bubbleGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {model.topics.map((topic) => {
            const y = model.topicToY.get(topic) ?? 0;

            return (
              <g key={topic}>
                <line
                  x1={LEFT}
                  x2={WIDTH - RIGHT}
                  y1={y}
                  y2={y}
                  stroke="rgba(148,163,184,0.14)"
                  strokeDasharray="4 8"
                />

                <text
                  x={24}
                  y={y + 4}
                  fill="rgba(226,232,240,0.74)"
                  fontSize="12"
                  fontFamily="Inter, sans-serif"
                >
                  {trimLabel(topic, 28)}
                </text>
              </g>
            );
          })}

            {model.ticks.map((tick) => (
            <g key={tick.id}>
              <line
                x1={tick.x}
                x2={tick.x}
                y1={TOP - 18}
                y2={model.height - BOTTOM + 18}
                stroke="rgba(148,163,184,0.10)"
              />

              <text
                x={tick.x}
                y={model.height - 30}
                textAnchor="middle"
                fill="rgba(148,163,184,0.8)"
                fontSize="11"
                fontFamily="monospace"
              >
                {tick.label}
              </text>
            </g>
          ))}

          <line
            x1={LEFT}
            x2={WIDTH - RIGHT}
            y1={model.height - BOTTOM + 18}
            y2={model.height - BOTTOM + 18}
            stroke="rgba(148,163,184,0.28)"
          />

          {model.nodes.map((node) => {
            const isSelected = node.id === selectedSessionId;
            const isHovered = node.id === hoveredSessionId;

            const diversity = clamp(node.channelDiversity ?? 0, 0, 1);
            const opacity = clamp(0.25 + diversity * 0.75, 0.25, 1);

            const echoScore = node.echoScore ?? 0;

            const strokeWidth = isSelected
              ? 4
              : clamp(1.5 + echoScore / 22, 1.5, 6);

            const stroke = isSelected
              ? "rgba(251,191,36,0.96)"
              : echoSeverityColor(node.echoSeverity);

            return (
              <g
                key={node.id}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredSessionId(node.id)}
                onMouseLeave={() => setHoveredSessionId(null)}
                onClick={() => onSelectSession(node.id)}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.radius}
                  fill={topicColor(node.dominantParentTopic)}
                  fillOpacity={opacity}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  filter={isSelected || isHovered ? "url(#bubbleGlow)" : undefined}
                />

                {(isSelected || isHovered) && (
                  <>
                    <rect
                      x={node.x - 78}
                      y={node.y - node.radius - 56}
                      width="156"
                      height="46"
                      rx="8"
                      fill="rgba(2,6,23,0.9)"
                      stroke="rgba(148,163,184,0.24)"
                    />

                    <text
                      x={node.x}
                      y={node.y - node.radius - 37}
                      textAnchor="middle"
                      fill="rgba(255,255,255,0.92)"
                      fontSize="11"
                      fontFamily="Inter, sans-serif"
                    >
                      {node.videoCount} videos · {node.durationMinutes}m
                    </text>

                    <text
                      x={node.x}
                      y={node.y - node.radius - 19}
                      textAnchor="middle"
                      fill="rgba(203,213,225,0.78)"
                      fontSize="10"
                      fontFamily="monospace"
                    >
                      Echo {Math.round(node.echoScore ?? 0)} · Diversity{" "}
                      {Math.round((node.channelDiversity ?? 0) * 100)}%
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-1 px-3 py-2 text-xs text-muted-foreground">
        <span>Bubble = session</span>
        <span>X-axis = time</span>
        <span>Y-axis = dominant parent topic</span>
        <span>Size = duration</span>
        <span>Colour = topic</span>
        <span>Opacity = channel diversity</span>
        <span>Border = echo severity/score</span>
      </div>

      {selectedNode && <SelectedSessionSummary node={selectedNode} />}
    </div>
  );
}

function SelectedSessionSummary({ node }: { node: SessionSummaryNode }) {
    return (
      <div className="rounded-xl border border-border bg-surface-1 p-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Selected session
            </div>
  
            <div className="mt-1 font-mono text-lg text-foreground">
              {formatDateTime(node.sessionStart)}
            </div>
  
            <div className="mt-1 text-sm text-muted-foreground">
              {node.videoCount} videos · {node.uniqueChannelCount} channels ·{" "}
              {node.durationMinutes} minutes
            </div>
          </div>
  
          <div className="rounded-lg border border-border bg-background px-3 py-2 text-right">
            <div className="text-xs text-muted-foreground">Dominant topic</div>
            <div className="mt-1 text-sm text-foreground">
              {node.dominantParentTopic}
            </div>
          </div>
        </div>
  
        <div className="mt-4 grid gap-3 md:grid-cols-5">
          <InsightPill
            label="Duration"
            value={`${node.durationMinutes}m`}
            helper="session length"
          />
  
          <InsightPill
            label="Channel diversity"
            value={`${Math.round((node.channelDiversity ?? 0) * 100)}%`}
            helper="unique channels / videos"
          />
  
          <InsightPill
            label="Topic concentration"
            value={`${Math.round((node.topicConcentration ?? 0) * 100)}%`}
            helper="dominant topic share"
          />
  
          <InsightPill
            label="Echo score"
            value={`${Math.round(node.echoScore ?? 0)}/100`}
            helper={node.echoSeverity ?? "info"}
          />
  
          <InsightPill
            label="Echo-linked videos"
            value={String(node.highEchoVideoCount ?? 0)}
            helper="from elevated clusters"
          />
        </div>
  
        {node.dominantEchoClusterLabel && (
          <div className="mt-4 rounded-lg border border-border bg-background p-3">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Dominant echo cluster
            </div>
  
            <div className="mt-1 text-sm text-foreground">
              {node.dominantEchoClusterLabel}
            </div>
          </div>
        )}
  
        <div className="mt-4 rounded-lg border border-border bg-background p-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                Topic distribution
              </div>
  
              <div className="mt-1 text-xs text-muted-foreground">
                Breakdown of videos inside this selected session
              </div>
            </div>
  
            <div className="font-mono text-xs text-muted-foreground">
              {node.videoCount} total
            </div>
          </div>
  
          {node.topicBreakdown && node.topicBreakdown.length > 0 ? (
            <div className="space-y-3">
              {node.topicBreakdown.slice(0, 8).map((topic) => {
                const ratio = node.videoCount
                  ? topic.videoCount / node.videoCount
                  : 0;
  
                const percentage = Math.round(ratio * 100);
  
                return (
                  <div key={topic.parentTopic} className="space-y-1.5">
                    <div className="flex items-center justify-between gap-3 text-xs">
                      <span className="truncate text-muted-foreground">
                        {topic.parentTopic}
                      </span>
  
                      <span className="shrink-0 font-mono text-foreground">
                        {topic.videoCount} · {percentage}%
                      </span>
                    </div>
  
                    <div className="h-2 overflow-hidden rounded-full bg-surface-2">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-md border border-border bg-surface-1 p-3 text-xs text-muted-foreground">
              No topic breakdown available for this session. Check whether the API
              response contains <span className="font-mono">topicBreakdown</span>.
            </div>
          )}
        </div>
      </div>
    );
  }

function InsightPill({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-background p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 truncate font-mono text-lg text-foreground">
        {value}
      </div>
      <div className="mt-1 text-[11px] text-muted-foreground">{helper}</div>
    </div>
  );
}

function topicColor(topic: string) {
  const normalized = topic.toLowerCase();

  if (normalized.includes("entertainment")) return "#8b5cf6";
  if (normalized.includes("sports")) return "#38bdf8";
  if (normalized.includes("news")) return "#ef4444";
  if (normalized.includes("politics")) return "#ef4444";
  if (normalized.includes("education")) return "#22c55e";
  if (normalized.includes("technology")) return "#14b8a6";
  if (normalized.includes("gaming")) return "#f97316";
  if (normalized.includes("music")) return "#ec4899";
  if (normalized.includes("lifestyle")) return "#eab308";
  if (normalized.includes("travel")) return "#06b6d4";
  if (normalized.includes("finance")) return "#84cc16";

  return "#64748b";
}

function echoSeverityColor(severity: string | null | undefined) {
  if (severity === "high") return "rgba(239,68,68,0.95)";
  if (severity === "medium") return "rgba(249,115,22,0.9)";
  if (severity === "low") return "rgba(234,179,8,0.85)";
  return "rgba(148,163,184,0.38)";
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function trimLabel(value: string, max: number) {
  if (!value) return "Unknown";
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function formatDateTick(value: number, rangeDays: number) {
    if (rangeDays <= 2) {
      return new Date(value).toLocaleString("en-AU", {
        month: "short",
        day: "numeric",
        hour: "numeric",
      });
    }
  
    return new Date(value).toLocaleDateString("en-AU", {
      month: "short",
      day: "numeric",
    });
  }

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-AU", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}