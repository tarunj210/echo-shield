import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import type { EchoSignal } from "@/lib/echo/types";

interface Node extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  parent: string;
  score: number;
  ratio: number;
  severity: string;
  risk: string;
}
interface Link extends d3.SimulationLinkDatum<Node> {
  weight: number;
}

const SEVERITY_FILL: Record<string, string> = {
  INFO: "var(--color-sev-info)",
  LOW: "var(--color-sev-low)",
  MEDIUM: "var(--color-sev-medium)",
  HIGH: "var(--color-sev-high)",
  CRITICAL: "var(--color-sev-critical)",
};

export function EchoNetworkGraph({ signals }: { signals: EchoSignal[] }) {
  const wrap = useRef<HTMLDivElement | null>(null);
  const ref = useRef<SVGSVGElement | null>(null);
  const [w, setW] = useState(700);
  const h = 420;
  const [hovered, setHovered] = useState<Node | null>(null);

  useEffect(() => {
    if (!wrap.current) return;
    const ro = new ResizeObserver((e) => setW(e[0].contentRect.width));
    ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);

  const { nodes, links, parents } = useMemo(() => {
    const nodes: Node[] = signals.map((s) => ({
      id: s.clusterId,
      label: s.displayLabel,
      parent: s.parentLabel,
      score: s.echoScore,
      ratio: s.currentExposureRatio,
      severity: s.severity,
      risk: s.inferredRiskCategory,
    }));
    // Link clusters sharing a parent topic (co-exposure proxy)
    const links: Link[] = [];
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        if (nodes[i].parent === nodes[j].parent) {
          links.push({ source: nodes[i].id, target: nodes[j].id, weight: (nodes[i].score + nodes[j].score) / 2 });
        }
      }
    }
    const parents = Array.from(new Set(nodes.map((n) => n.parent)));
    return { nodes, links, parents };
  }, [signals]);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    if (!nodes.length) return;

    // Cluster anchors by parent topic (radial layout)
    const anchorR = Math.min(w, h) * 0.32;
    const anchorMap = new Map<string, { x: number; y: number }>();
    parents.forEach((p, i) => {
      const a = (i / parents.length) * Math.PI * 2;
      anchorMap.set(p, { x: w / 2 + Math.cos(a) * anchorR, y: h / 2 + Math.sin(a) * anchorR });
    });

    const sim = d3
      .forceSimulation<Node>(nodes)
      .force("charge", d3.forceManyBody().strength(-160))
      .force("link", d3.forceLink<Node, Link>(links).id((d) => d.id).distance(60).strength((d) => 0.2 + d.weight * 0.4))
      .force("x", d3.forceX<Node>((d) => anchorMap.get(d.parent)!.x).strength(0.18))
      .force("y", d3.forceY<Node>((d) => anchorMap.get(d.parent)!.y).strength(0.18))
      .force("collide", d3.forceCollide<Node>().radius((d) => 10 + d.ratio * 90))
      .stop();

    for (let i = 0; i < 280; i++) sim.tick();

    const g = svg.append("g");

    // Parent anchor rings
    g.append("g")
      .selectAll("circle")
      .data(parents)
      .join("circle")
      .attr("cx", (p) => anchorMap.get(p)!.x)
      .attr("cy", (p) => anchorMap.get(p)!.y)
      .attr("r", 4)
      .attr("fill", "var(--color-muted-foreground)")
      .attr("opacity", 0.35);

    g.append("g")
      .selectAll("text")
      .data(parents)
      .join("text")
      .attr("x", (p) => anchorMap.get(p)!.x)
      .attr("y", (p) => anchorMap.get(p)!.y - 12)
      .attr("text-anchor", "middle")
      .attr("fill", "var(--color-muted-foreground)")
      .attr("font-family", "var(--font-mono)")
      .attr("font-size", 9)
      .attr("letter-spacing", 1)
      .text((p) => p.toUpperCase());

    // Links
    g.append("g")
      .attr("stroke", "var(--color-primary)")
      .attr("stroke-opacity", 0.18)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("x1", (d) => (d.source as Node).x!)
      .attr("y1", (d) => (d.source as Node).y!)
      .attr("x2", (d) => (d.target as Node).x!)
      .attr("y2", (d) => (d.target as Node).y!)
      .attr("stroke-width", (d) => 0.5 + d.weight * 2);

    const nodeG = g
      .append("g")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("transform", (d) => `translate(${d.x},${d.y})`)
      .style("cursor", "pointer")
      .on("mouseenter", (_e, d) => setHovered(d))
      .on("mouseleave", () => setHovered(null));

    nodeG
      .append("circle")
      .attr("r", (d) => 6 + d.ratio * 60)
      .attr("fill", (d) => SEVERITY_FILL[d.severity] ?? "var(--color-primary)")
      .attr("fill-opacity", 0.15)
      .attr("stroke", (d) => SEVERITY_FILL[d.severity] ?? "var(--color-primary)")
      .attr("stroke-width", 1.5);

    nodeG
      .append("circle")
      .attr("r", 3)
      .attr("fill", (d) => SEVERITY_FILL[d.severity] ?? "var(--color-primary)");
  }, [nodes, links, parents, w]);

  return (
    <div ref={wrap} className="relative w-full">
      <svg ref={ref} width={w} height={h} />
      {hovered && (
        <div className="pointer-events-none absolute left-3 top-3 max-w-xs rounded-md border border-border bg-popover/95 p-3 text-xs shadow-xl backdrop-blur">
          <div className="eyebrow mb-1">{hovered.parent}</div>
          <div className="text-sm font-medium text-foreground">{hovered.label}</div>
          <div className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 font-mono text-muted-foreground">
            <span>Echo score</span><span className="text-right text-foreground">{hovered.score.toFixed(2)}</span>
            <span>Exposure</span><span className="text-right text-foreground">{(hovered.ratio * 100).toFixed(1)}%</span>
            <span>Risk</span><span className="text-right text-foreground">{hovered.risk}</span>
          </div>
        </div>
      )}
    </div>
  );
}
