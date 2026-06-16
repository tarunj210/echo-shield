import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  GitBranch,
  ShieldCheck,
} from "lucide-react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import {
  getEchoSignals,
  getProfileOverview,
  getTemporalDrift,
  getTopicTimeseries,
} from "./api/client";
import type {
  EchoSignal,
  ProfileOverview,
  TemporalDrift,
  TopicExposurePoint,
} from "./types";
import "./App.css";

const PROFILE_ID = "profile_self";

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(2);
}

function shortDate(value: string): string {
  return new Date(value).toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
  });
}

function severityClass(severity?: string | null): string {
  if (!severity) return "severity info";
  return `severity ${severity.toLowerCase()}`;
}

function App() {
  const [overview, setOverview] = useState<ProfileOverview | null>(null);
  const [echoSignals, setEchoSignals] = useState<EchoSignal[]>([]);
  const [driftSignals, setDriftSignals] = useState<TemporalDrift[]>([]);
  const [topicPoints, setTopicPoints] = useState<TopicExposurePoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      getProfileOverview(PROFILE_ID),
      getEchoSignals(PROFILE_ID),
      getTemporalDrift(PROFILE_ID),
      getTopicTimeseries(PROFILE_ID),
    ])
      .then(([overviewData, echoData, driftData, topicData]) => {
        setOverview(overviewData);
        setEchoSignals(echoData);
        setDriftSignals(driftData);
        setTopicPoints(topicData);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Unknown error");
      });
  }, []);

  const chartData = useMemo(() => {
    const grouped = new Map<string, Record<string, string | number>>();

    for (const point of topicPoints) {
      const dateKey = shortDate(point.windowStart);

      if (!grouped.has(dateKey)) {
        grouped.set(dateKey, { week: dateKey });
      }

      const row = grouped.get(dateKey)!;
      row[point.parentLabel] = Number((point.exposureRatio * 100).toFixed(1));
    }

    return Array.from(grouped.values());
  }, [topicPoints]);

  const latestDrift = driftSignals[0];

  if (error) {
    return (
      <main className="app-shell">
        <section className="error-card">
          <h1>EchoShield API error</h1>
          <p>{error}</p>
          <p>Check that Spring Boot is running on port 8080.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <h1>EchoShield</h1>
            <p>Exposure intelligence</p>
          </div>
        </div>

        <nav>
          <a className="active">Student Overview</a>
          <a>Exposure Signals</a>
          <a>Temporal Drift</a>
          <a>Content Clusters</a>
          <a>Graph Explorer</a>
        </nav>
      </aside>

      <section className="dashboard">
        <header className="page-header">
          <div>
            <p className="eyebrow">Pseudonymised profile</p>
            <h2>{PROFILE_ID}</h2>
            <p>
              Explainable content exposure patterns, review signals, and temporal drift.
            </p>
          </div>

          <div className="status-pill">
            <Activity size={16} />
            Read-only analytics
          </div>
        </header>

        <section className="cards-grid">
          <MetricCard
            icon={<BarChart3 />}
            label="Watch events"
            value={overview?.totalWatchEvents?.toLocaleString() ?? "—"}
            helper="Clustered activity analysed"
          />
          <MetricCard
            icon={<GitBranch />}
            label="Unique clusters"
            value={overview?.uniqueClusters?.toLocaleString() ?? "—"}
            helper={overview?.dominantParentTopic ?? "Dominant topic unavailable"}
          />
          <MetricCard
            icon={<AlertTriangle />}
            label="Top exposure score"
            value={formatScore(overview?.topEchoScore)}
            helper={overview?.topSeverity ?? "No severity"}
          />
          <MetricCard
            icon={<Activity />}
            label="Latest drift score"
            value={formatScore(latestDrift?.driftScore)}
            helper={latestDrift?.severity ?? "No drift signal"}
          />
        </section>

        <section className="content-grid">
          <article className="panel large">
            <div className="panel-header">
              <div>
                <h3>Weekly topic exposure</h3>
                <p>Share of clustered watch events by parent topic.</p>
              </div>
            </div>

            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="week" />
                  <YAxis unit="%" />
                  <Tooltip />
                  <Line type="monotone" dataKey="Entertainment & Commentary" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Sports" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Motivation & Self-improvement" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Social & Lifestyle" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="Technology & Computing" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>

          <article className="panel">
            <div className="panel-header">
              <div>
                <h3>Latest temporal drift</h3>
                <p>Behavioural content exposure change.</p>
              </div>
            </div>

            {latestDrift ? (
              <div className="drift-summary">
                <div className={severityClass(latestDrift.severity)}>
                  {latestDrift.severity}
                </div>
                <h4>{formatScore(latestDrift.driftScore)} / 100</h4>
                <p>
                  {latestDrift.dominantTopicBefore} →{" "}
                  {latestDrift.dominantTopicAfter}
                </p>
                <ul>
                  <li>Topic drift: {latestDrift.topicDriftScore.toFixed(3)}</li>
                  <li>Cluster drift: {latestDrift.clusterDriftScore.toFixed(3)}</li>
                  <li>Novelty: {formatPercent(latestDrift.noveltyRatio)}</li>
                  <li>Risk delta: {latestDrift.riskExposureDelta.toFixed(3)}</li>
                </ul>
              </div>
            ) : (
              <p>No temporal drift signal available.</p>
            )}
          </article>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h3>Top exposure signals</h3>
              <p>Repeated exposure clusters ranked by review signal score.</p>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Cluster</th>
                  <th>Parent topic</th>
                  <th>Exposure</th>
                  <th>Trend</th>
                  <th>Risk category</th>
                  <th>Score</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                {echoSignals.map((signal) => (
                  <tr key={signal.clusterId}>
                    <td>
                      <strong>{signal.displayLabel}</strong>
                      <span>{signal.clusterId}</span>
                    </td>
                    <td>{signal.parentLabel}</td>
                    <td>{formatPercent(signal.currentExposureRatio)}</td>
                    <td>{formatPercent(signal.trendDelta)}</td>
                    <td>{signal.inferredRiskCategory}</td>
                    <td>{formatScore(signal.echoScore)}</td>
                    <td>
                      <span className={severityClass(signal.severity)}>
                        {signal.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h3>Temporal drift history</h3>
              <p>Weekly change in topic mix, cluster mix, novelty, and risk exposure.</p>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Window</th>
                  <th>Before</th>
                  <th>After</th>
                  <th>Topic drift</th>
                  <th>Cluster drift</th>
                  <th>Novelty</th>
                  <th>Risk delta</th>
                  <th>Score</th>
                  <th>Severity</th>
                </tr>
              </thead>
              <tbody>
                {driftSignals.map((signal) => (
                  <tr key={`${signal.currentWindowStart}-${signal.currentWindowEnd}`}>
                    <td>
                      {shortDate(signal.currentWindowStart)} →{" "}
                      {shortDate(signal.currentWindowEnd)}
                    </td>
                    <td>{signal.dominantTopicBefore}</td>
                    <td>{signal.dominantTopicAfter}</td>
                    <td>{signal.topicDriftScore.toFixed(3)}</td>
                    <td>{signal.clusterDriftScore.toFixed(3)}</td>
                    <td>{formatPercent(signal.noveltyRatio)}</td>
                    <td>{signal.riskExposureDelta.toFixed(3)}</td>
                    <td>{formatScore(signal.driftScore)}</td>
                    <td>
                      <span className={severityClass(signal.severity)}>
                        {signal.severity}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

function MetricCard({
  icon,
  label,
  value,
  helper,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <article className="metric-card">
      <div className="metric-icon">{icon}</div>
      <p>{label}</p>
      <h3>{value}</h3>
      <span>{helper}</span>
    </article>
  );
}

export default App;