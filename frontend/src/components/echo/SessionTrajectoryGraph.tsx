import { useMemo, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { SessionTrajectory, TrajectoryNode } from "@/lib/echo/types";

type GraphNode = TrajectoryNode & {
  val: number;
  isFinal: boolean;
};

type GraphLink = {
  source: string;
  target: string;
  type: "NEXT_WATCH" | "WATCHED_VIDEO" | "PUBLISHED_BY";
  minutesBetween: number | null;
};

type Props = {
  trajectory: SessionTrajectory;
};

export function SessionTrajectoryGraph({ trajectory }: Props) {
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  const lastSequence = Math.max(
    ...trajectory.nodes
      .map((node) => node.sequenceIndex ?? 0)
      .filter((value) => value > 0),
    0
  );

  const graphData = useMemo(() => {
    return {
      nodes: trajectory.nodes.map((node) => ({
        ...node,
        isFinal:
          node.type === "watch_event" && node.sequenceIndex === lastSequence,
        val:
          node.type === "watch_event"
            ? node.sequenceIndex === lastSequence
              ? 12
              : 8
            : node.type === "video"
              ? 9
              : 8,
      })),
      links: trajectory.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        type: edge.type,
        minutesBetween: edge.minutesBetween,
      })),
    };
  }, [trajectory, lastSequence]);

  return (
    <div className="grid gap-3">
      <div className="h-[620px] overflow-hidden rounded-xl border border-border bg-background">
        <ForceGraph2D
          graphData={graphData}
          backgroundColor="transparent"
          nodeRelSize={5}
          cooldownTicks={160}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.08}
          nodeLabel={(node: any) => buildTooltip(node)}
          onNodeHover={(node: any) => {
            setHoveredNodeId(node?.id ?? null);
          }}
          onNodeClick={(node: any) => {
            setSelectedNode(node);
          }}
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            const isHovered = node.id === hoveredNodeId;
            const isSelected = node.id === selectedNode?.id;

            const radius =
              node.type === "watch_event"
                ? node.isFinal
                  ? 12
                  : 8
                : node.type === "video"
                  ? 9
                  : 8;

            const color =
              node.type === "watch_event"
                ? node.isFinal
                  ? "#fbbf24"
                  : "#a78bfa"
                : node.type === "video"
                  ? "#38bdf8"
                  : "#22c55e";

            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();

            if (node.isFinal || isHovered || isSelected) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, radius + 5, 0, 2 * Math.PI, false);
              ctx.strokeStyle = node.isFinal
                ? "rgba(251,191,36,0.85)"
                : "rgba(255,255,255,0.55)";
              ctx.lineWidth = 2;
              ctx.stroke();
            }

            const shouldShowLabel =
              node.type === "watch_event" ||
              node.isFinal ||
              isHovered ||
              isSelected ||
              globalScale > 2.2;

            if (!shouldShowLabel) return;

            const label =
              node.type === "watch_event"
                ? node.isFinal
                  ? "CURRENT"
                  : String(node.sequenceIndex ?? "")
                : trimLabel(node.label, node.type === "video" ? 34 : 24);

            const fontSize = Math.max(10 / globalScale, 3);
            ctx.font = `${fontSize}px Inter, sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";

            const textWidth = ctx.measureText(label).width;
            const labelX = node.x;
            const labelY = node.y + radius + 5;

            if (node.type !== "watch_event") {
              ctx.fillStyle = "rgba(2,6,23,0.78)";
              roundRect(
                ctx,
                labelX - textWidth / 2 - 5,
                labelY - 2,
                textWidth + 10,
                fontSize + 6,
                4
              );
              ctx.fill();
            }

            ctx.fillStyle = "rgba(255,255,255,0.9)";
            ctx.fillText(label, labelX, labelY);

            if (
              (isHovered || isSelected) &&
              node.type === "video" &&
              node.watchedAt
            ) {
              ctx.fillStyle = "rgba(255,255,255,0.55)";
              ctx.fillText(
                formatTime(node.watchedAt),
                node.x,
                node.y + radius + 20
              );
            }
          }}
          linkColor={(link: any) => {
            if (link.type === "NEXT_WATCH") return "rgba(167,139,250,0.9)";
            if (link.type === "WATCHED_VIDEO") return "rgba(56,189,248,0.35)";
            return "rgba(34,197,94,0.35)";
          }}
          linkWidth={(link: any) => {
            if (link.type === "NEXT_WATCH") return 2;
            return 0.8;
          }}
          linkCanvasObjectMode={() => "after"}
          linkCanvasObject={(link: any, ctx, globalScale) => {
            if (link.type !== "NEXT_WATCH" || link.minutesBetween == null) {
              return;
            }

            const source = link.source;
            const target = link.target;

            if (!source.x || !source.y || !target.x || !target.y) return;

            // Only show minute labels when zoomed in enough.
            if (globalScale < 1.4) return;

            const x = (source.x + target.x) / 2;
            const y = (source.y + target.y) / 2;

            const text = `${link.minutesBetween}m`;
            const fontSize = Math.max(9 / globalScale, 3);

            ctx.font = `${fontSize}px Inter, sans-serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "rgba(216,180,254,0.95)";
            ctx.fillText(text, x, y - 4);
          }}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-1 px-3 py-2 text-xs text-muted-foreground">
        <LegendDot color="bg-violet-400" label="Watch event" />
        <LegendDot color="bg-sky-400" label="Video" />
        <LegendDot color="bg-green-400" label="Channel" />
        <LegendDot color="bg-yellow-400" label="Current/final event" />

        <span className="ml-auto hidden text-[11px] md:inline">
          Hover or click nodes to reveal full labels. Full sequence is shown in
          the timeline.
        </span>
      </div>

      {selectedNode && (
        <div className="rounded-xl border border-border bg-surface-1 p-3 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs uppercase tracking-wider text-muted-foreground">
                Selected {selectedNode.type.replace("_", " ")}
              </div>

              <div className="mt-1 truncate font-medium text-foreground">
                {selectedNode.label}
              </div>

              {selectedNode.channelTitle && (
                <div className="mt-1 truncate text-xs text-muted-foreground">
                  Channel: {selectedNode.channelTitle}
                </div>
              )}

              {selectedNode.watchedAt && (
                <div className="mt-1 font-mono text-xs text-muted-foreground">
                  Watched at {formatDateTime(selectedNode.watchedAt)}
                </div>
              )}
            </div>

            <button
              onClick={() => setSelectedNode(null)}
              className="rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-surface-2 hover:text-foreground"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`size-2 rounded-full ${color}`} />
      {label}
    </span>
  );
}

function buildTooltip(node: GraphNode) {
  const lines = [
    node.type.replace("_", " ").toUpperCase(),
    node.label,
    node.channelTitle ? `Channel: ${node.channelTitle}` : null,
    node.watchedAt ? `Watched: ${formatDateTime(node.watchedAt)}` : null,
    node.sequenceIndex ? `Sequence: ${node.sequenceIndex}` : null,
  ].filter(Boolean);

  return lines.join("\n");
}

function trimLabel(value: string, max: number) {
  if (!value) return "Untitled";
  return value.length > max ? `${value.slice(0, max)}…` : value;
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("en-AU", {
    hour: "numeric",
    minute: "2-digit",
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

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}