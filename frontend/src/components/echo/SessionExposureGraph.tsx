import { useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type {
  SessionSummaryGraph,
  SessionSummaryNode,
} from "@/lib/echo/types";

type Props = {
  graph: SessionSummaryGraph;
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
};

type GraphNode = SessionSummaryNode & {
  val: number;
};

export function SessionExposureGraph({
  graph,
  selectedSessionId,
  onSelectSession,
}: Props) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const graphData = useMemo(() => {
    return {
      nodes: graph.nodes.map((node) => ({
        ...node,
        val: Math.max(8, Math.min(32, Math.sqrt(node.videoCount) * 2.2)),
      })),
      links: graph.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        type: edge.type,
      })),
    };
  }, [graph]);

  const selectedNode =
    graph.nodes.find((node) => node.id === selectedSessionId) ?? null;

  return (
    <div className="grid gap-3">
      <div className="h-[620px] overflow-hidden rounded-xl border border-border bg-background">
        <ForceGraph2D
          graphData={graphData}
          backgroundColor="transparent"
          nodeRelSize={5}
          cooldownTicks={160}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.08}
          nodeLabel={(node: any) => buildTooltip(node)}
          onNodeHover={(node: any) => {
            setHoveredNodeId(node?.id ?? null);
          }}
          onNodeClick={(node: any) => {
            onSelectSession(node.id);
          }}
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            const isSelected = node.id === selectedSessionId;
            const isHovered = node.id === hoveredNodeId;

            const radius = Math.max(
              9,
              Math.min(30, Math.sqrt(node.videoCount) * 2.2)
            );

            const color = topicColor(node.dominantParentTopic);

            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();

            const concentrationRing = Math.max(2, node.topicConcentration * 8);

            ctx.beginPath();
            ctx.arc(node.x, node.y, radius + concentrationRing, 0, 2 * Math.PI);
            ctx.strokeStyle = isSelected ? "rgba(251,191,36,0.95)": echoSeverityColor(node.echoSeverity);
            ctx.lineWidth = isSelected ? 3 : Math.max(1.5, node.echoScore / 25);
            ctx.stroke();

            const label =
              isSelected || isHovered || globalScale > 1.5
                ? `${node.videoCount} videos`
                : String(node.videoCount);

            const fontSize = Math.max(10 / globalScale, 3);
            ctx.font = `${fontSize}px Inter, sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "rgba(255,255,255,0.92)";
            ctx.fillText(label, node.x, node.y);

            if (isSelected || isHovered || globalScale > 2) {
              const topic = trimLabel(node.dominantParentTopic, 26);
              ctx.textBaseline = "top";
              ctx.fillStyle = "rgba(255,255,255,0.78)";
              ctx.fillText(topic, node.x, node.y + radius + 8);
            }
          }}
          linkColor={() => "rgba(148,163,184,0.35)"}
          linkWidth={() => 1.5}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-1 px-3 py-2 text-xs text-muted-foreground">
        <span>Node = session</span>
        <span>Size = video count</span>
        <span>Colour = dominant parent topic</span>
        <span>Ring = topic concentration</span>
        <span>Arrow = next session</span>
      </div>

      {selectedNode && (
        <div className="rounded-xl border border-border bg-surface-1 p-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                Selected session
              </div>

              <div className="mt-1 font-mono text-lg text-foreground">
                {formatDateTime(selectedNode.sessionStart)}
              </div>

              <div className="mt-1 text-sm text-muted-foreground">
                {selectedNode.videoCount} videos ·{" "}
                {selectedNode.uniqueChannelCount} channels ·{" "}
                {selectedNode.durationMinutes} min
              </div>
            </div>

            <div className="rounded-lg border border-border bg-background px-3 py-2 text-right">
              <div className="text-xs text-muted-foreground">
                Dominant topic
              </div>
              <div className="mt-1 text-sm text-foreground">
                {selectedNode.dominantParentTopic}
              </div>
            </div>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <InsightPill
              label="Channel diversity"
              value={`${Math.round(selectedNode.channelDiversity * 100)}%`}
              helper="unique channels / videos"
            />

            <InsightPill
              label="Topic concentration"
              value={`${Math.round(selectedNode.topicConcentration * 100)}%`}
              helper="dominant topic share"
            />

            <InsightPill
              label="Dominant channel"
              value={selectedNode.dominantChannelTitle ?? "Unknown"}
              helper="most frequent channel"
            />
            <InsightPill
              label="Echo score"
              value={`${Math.round(selectedNode.echoScore)}/100`}
              helper={selectedNode.echoSeverity}
            />

            <InsightPill
              label="Echo-linked videos"
              value={String(selectedNode.highEchoVideoCount)}
              helper="videos from elevated clusters"
            />
          </div>

          {selectedNode.topicBreakdown.length > 0 && (
            <div className="mt-4 space-y-2">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                Topic breakdown
              </div>

              {selectedNode.topicBreakdown.slice(0, 5).map((topic) => {
                const ratio = selectedNode.videoCount
                  ? topic.videoCount / selectedNode.videoCount
                  : 0;

                return (
                  <div key={topic.parentTopic} className="space-y-1">
                    <div className="flex justify-between gap-3 text-xs">
                      <span className="truncate text-muted-foreground">
                        {topic.parentTopic}
                      </span>
                      <span className="font-mono text-foreground">
                        {topic.videoCount}
                      </span>
                    </div>

                    <div className="h-1.5 overflow-hidden rounded-full bg-background">
                      <div
                        className="h-full rounded-full bg-primary"
                        style={{ width: `${Math.round(ratio * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          {selectedNode.dominantEchoClusterLabel && (
            <div className="mt-3 rounded-lg border border-border bg-background p-3">
                <div className="text-xs text-muted-foreground">
                Dominant echo cluster
                </div>
                <div className="mt-1 text-sm text-foreground">
                {selectedNode.dominantEchoClusterLabel}
                </div>
            </div>
            )}
        </div>
      )}
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

function buildTooltip(node: GraphNode) {
  return [
    node.label,
    `${node.videoCount} videos`,
    `${node.uniqueChannelCount} channels`,
    `Topic: ${node.dominantParentTopic}`,
    `Duration: ${node.durationMinutes} min`,
    `Channel diversity: ${Math.round(node.channelDiversity * 100)}%`,
    `Topic concentration: ${Math.round(node.topicConcentration * 100)}%`,
  ].join("\n");
}

function trimLabel(value: string, max: number) {
  if (!value) return "Unknown";
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-AU", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function echoSeverityColor(severity: string) {
    if (severity === "high") return "rgba(239,68,68,0.95)";
    if (severity === "medium") return "rgba(249,115,22,0.9)";
    if (severity === "low") return "rgba(234,179,8,0.85)";
    return "rgba(148,163,184,0.28)";
  }