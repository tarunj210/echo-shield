import { useEffect, useMemo, useRef, useState } from "react";
import * as d3 from "d3";
import type { TopicExposurePoint } from "@/lib/echo/types";

const TOPIC_VARS = [
  "var(--color-topic-1)",
  "var(--color-topic-2)",
  "var(--color-topic-3)",
  "var(--color-topic-4)",
  "var(--color-topic-5)",
  "var(--color-topic-6)",
];

interface Props {
  points: TopicExposurePoint[];
}

export function TopicExposureChart({ points }: Props) {
  const ref = useRef<SVGSVGElement | null>(null);
  const wrap = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(800);
  const height = 320;
  const m = { top: 16, right: 24, bottom: 28, left: 40 };

  useEffect(() => {
    if (!wrap.current) return;
    const ro = new ResizeObserver((e) => setWidth(e[0].contentRect.width));
    ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);

  const { series, dates, topics, hover, setHover } = useStackedSeries(points);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    if (!series.length) return;

    const x = d3.scalePoint<string>().domain(dates).range([m.left, width - m.right]);
    const y = d3.scaleLinear().domain([0, 1]).range([height - m.bottom, m.top]);

    const g = svg.append("g");

    // grid
    g.append("g")
      .attr("transform", `translate(${m.left},0)`)
      .call(d3.axisLeft(y).ticks(4).tickSize(-(width - m.left - m.right)).tickFormat(d3.format(".0%") as never))
      .call((s) => s.select(".domain").remove())
      .call((s) => s.selectAll("line").attr("stroke", "var(--color-grid)").attr("stroke-dasharray", "2 4"))
      .call((s) => s.selectAll("text").attr("fill", "var(--color-muted-foreground)").attr("font-family", "var(--font-mono)").attr("font-size", 10));

    g.append("g")
      .attr("transform", `translate(0,${height - m.bottom})`)
      .call(d3.axisBottom(x))
      .call((s) => s.select(".domain").attr("stroke", "var(--color-border)"))
      .call((s) => s.selectAll("line").attr("stroke", "var(--color-border)"))
      .call((s) => s.selectAll("text").attr("fill", "var(--color-muted-foreground)").attr("font-family", "var(--font-mono)").attr("font-size", 10));

    const area = d3
      .area<{ date: string; v0: number; v1: number }>()
      .x((d) => x(d.date)!)
      .y0((d) => y(d.v0))
      .y1((d) => y(d.v1))
      .curve(d3.curveMonotoneX);

    series.forEach((s, i) => {
      const color = TOPIC_VARS[i % TOPIC_VARS.length];
      g.append("path")
        .attr("d", area(s.values)!)
        .attr("fill", color)
        .attr("fill-opacity", hover && hover !== s.key ? 0.12 : 0.55)
        .attr("stroke", color)
        .attr("stroke-opacity", hover && hover !== s.key ? 0.3 : 1)
        .attr("stroke-width", 1.25)
        .style("transition", "fill-opacity 200ms, stroke-opacity 200ms");
    });
  }, [series, dates, width, hover]);

  return (
    <div ref={wrap} className="w-full">
      <svg ref={ref} width={width} height={height} />
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2">
        {topics.map((t, i) => (
          <button
            key={t}
            onMouseEnter={() => setHover(t)}
            onMouseLeave={() => setHover(null)}
            className="flex items-center gap-2 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            <span className="size-2.5 rounded-sm" style={{ background: TOPIC_VARS[i % TOPIC_VARS.length] }} />
            {t}
          </button>
        ))}
      </div>
    </div>
  );
}

function useStackedSeries(points: TopicExposurePoint[]) {
  const [hover, setHover] = useState<string | null>(null);
  const data = useMemo(() => {
    const byDate = new Map<string, Record<string, number>>();
    const topicSet = new Set<string>();
    for (const p of points) {
      const key = new Date(p.windowStart).toLocaleDateString("en-AU", { month: "short", day: "numeric" });
      topicSet.add(p.parentLabel);
      if (!byDate.has(key)) byDate.set(key, {});
      byDate.get(key)![p.parentLabel] = p.exposureRatio;
    }
    const dates = Array.from(byDate.keys());
    const topics = Array.from(topicSet);

    // Stack normalized
    const series = topics.map((t) => ({ key: t, values: [] as { date: string; v0: number; v1: number }[] }));
    for (const date of dates) {
      const row = byDate.get(date)!;
      const total = topics.reduce((s, t) => s + (row[t] ?? 0), 0) || 1;
      let acc = 0;
      for (let i = 0; i < topics.length; i++) {
        const v = (row[topics[i]] ?? 0) / total;
        series[i].values.push({ date, v0: acc, v1: acc + v });
        acc += v;
      }
    }
    return { series, dates, topics };
  }, [points]);

  return { ...data, hover, setHover };
}
