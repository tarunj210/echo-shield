import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import { sankey, sankeyLinkHorizontal, type SankeyGraph } from "d3-sankey";
import type { TemporalDrift } from "@/lib/echo/types";

interface SNode { name: string; week: number; }
interface SLink { source: number | SNode; target: number | SNode; value: number; }

const TOPIC_COLORS: Record<string, string> = {
  "Sports": "var(--color-topic-2)",
  "Entertainment & Commentary": "var(--color-topic-1)",
  "Motivation & Self-improvement": "var(--color-topic-4)",
  "Social & Lifestyle": "var(--color-topic-3)",
  "Technology & Computing": "var(--color-topic-6)",
  "Gaming & Streamers": "var(--color-topic-5)",
};

export function DriftSankey({ drifts }: { drifts: TemporalDrift[] }) {
  const wrap = useRef<HTMLDivElement | null>(null);
  const ref = useRef<SVGSVGElement | null>(null);
  const [w, setW] = useState(700);
  const h = 320;

  useEffect(() => {
    if (!wrap.current) return;
    const ro = new ResizeObserver((e) => setW(e[0].contentRect.width));
    ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);

  // Build a temporal sankey: each weekly window is a column; topics flow week-to-week.
  const graph = useMemo<SankeyGraph<SNode, SLink>>(() => {
    const chrono = [...drifts].sort((a, b) => +new Date(a.currentWindowStart) - +new Date(b.currentWindowStart));
    const nodes: SNode[] = [];
    const indexOf = new Map<string, number>();
    const ensure = (name: string, week: number) => {
      const k = `${week}::${name}`;
      if (!indexOf.has(k)) { indexOf.set(k, nodes.length); nodes.push({ name, week }); }
      return indexOf.get(k)!;
    };
    const links: SLink[] = [];
    chrono.forEach((d, i) => {
      const a = ensure(d.dominantTopicBefore, i);
      const b = ensure(d.dominantTopicAfter, i + 1);
      // Weight links by drift score so big shifts read as thick streams
      links.push({ source: a, target: b, value: Math.max(0.05, d.driftScore / 100) });
    });
    return { nodes, links } as SankeyGraph<SNode, SLink>;
  }, [drifts]);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    if (!graph.nodes.length) return;

    const layout = sankey<SNode, SLink>()
      .nodeWidth(10)
      .nodePadding(14)
      .extent([[10, 20], [w - 10, h - 10]]);

    const g = layout({
      nodes: graph.nodes.map((n) => ({ ...n })),
      links: graph.links.map((l) => ({ ...l })),
    });

    const root = svg.append("g");

    root.append("g")
      .attr("fill", "none")
      .selectAll("path")
      .data(g.links)
      .join("path")
      .attr("d", sankeyLinkHorizontal())
      .attr("stroke", (d) => TOPIC_COLORS[(d.source as SNode).name] ?? "var(--color-primary)")
      .attr("stroke-opacity", 0.35)
      .attr("stroke-width", (d) => Math.max(1, d.width ?? 1));

    const nodeSel = root.append("g")
      .selectAll("g")
      .data(g.nodes)
      .join("g");

    nodeSel.append("rect")
      .attr("x", (d) => d.x0!)
      .attr("y", (d) => d.y0!)
      .attr("width", (d) => (d.x1! - d.x0!))
      .attr("height", (d) => Math.max(2, d.y1! - d.y0!))
      .attr("fill", (d) => TOPIC_COLORS[d.name] ?? "var(--color-primary)")
      .attr("rx", 1);

    // Only label the leftmost and rightmost columns to avoid clutter
    const maxWeek = d3.max(g.nodes, (n) => n.week) ?? 0;
    nodeSel
      .filter((d) => d.week === 0 || d.week === maxWeek)
      .append("text")
      .attr("x", (d) => (d.week === 0 ? d.x1! + 6 : d.x0! - 6))
      .attr("y", (d) => (d.y0! + d.y1!) / 2)
      .attr("dy", "0.32em")
      .attr("text-anchor", (d) => (d.week === 0 ? "start" : "end"))
      .attr("fill", "var(--color-foreground)")
      .attr("font-size", 10)
      .attr("font-family", "var(--font-mono)")
      .text((d) => d.name);

    // Column headers
    const weeks = Array.from(new Set(g.nodes.map((n) => n.week))).sort((a, b) => a - b);
    const colX = (week: number) => {
      const n = g.nodes.find((nn) => nn.week === week)!;
      return (n.x0! + n.x1!) / 2;
    };
    root.append("g")
      .selectAll("text")
      .data(weeks)
      .join("text")
      .attr("x", (week) => colX(week))
      .attr("y", 12)
      .attr("text-anchor", "middle")
      .attr("fill", "var(--color-muted-foreground)")
      .attr("font-family", "var(--font-mono)")
      .attr("font-size", 9)
      .attr("letter-spacing", 1)
      .text((week) => `W${week + 1}`);
  }, [graph, w]);

  return (
    <div ref={wrap} className="w-full">
      <svg ref={ref} width={w} height={h} />
    </div>
  );
}
