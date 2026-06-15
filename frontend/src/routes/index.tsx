import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  GitBranch,
  ShieldCheck,
  Radio,
  Upload,
} from "lucide-react";

import {
  getEchoSignals,
  getProfileOverview,
  getTemporalDrift,
  getTopicTimeseries,
  USING_MOCK_DATA,
} from "@/lib/echo/client";

import type {
  EchoSignal,
  ProfileOverview,
  TemporalDrift,
  TopicExposurePoint,
} from "@/lib/echo/types";

import { TopicExposureChart } from "@/components/echo/TopicExposure";
import { EchoNetworkGraph } from "@/components/echo/EchoNetworkGraph";
import { DriftSankey } from "@/components/echo/DriftSankey";
import { RiskTimeline } from "@/components/echo/RiskTimeline";
import { SeverityPill } from "@/components/echo/SeverityPill";
import { WatchHistoryUpload } from "@/components/echo/WatchHistoryUpload";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "EchoShield — Child Online Echo Chamber Intelligence" },
      {
        name: "description",
        content:
          "Visualize how a child's online content exposure narrows over time. Topic drift, echo-chamber networks, and risk signals in one dashboard.",
      },
      {
        property: "og:title",
        content: "EchoShield — Child Echo Chamber Intelligence",
      },
      {
        property: "og:description",
        content:
          "Topic exposure over time, echo-chamber network, and temporal drift Sankey for a child profile.",
      },
    ],
  }),
  component: DashboardRoute,
});

function formatPercent(v: number | null | undefined) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function formatScore(v: number | null | undefined) {
  if (v == null) return "—";
  return v.toFixed(2);
}

function shortDate(s: string) {
  return new Date(s).toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
  });
}

function DashboardRoute() {
  const [profileId, setProfileId] = useState<string | null>(() => {
    return localStorage.getItem("echoshield_profile_id");
  });

  function handleProfileReady(nextProfileId: string) {
    localStorage.setItem("echoshield_profile_id", nextProfileId);
    setProfileId(nextProfileId);
  }

  function handleResetProfile() {
    localStorage.removeItem("echoshield_profile_id");
    setProfileId(null);
  }

  if (!profileId) {
    return (
      <main className="scanlines min-h-screen">
        <div className="mx-auto flex min-h-screen max-w-4xl items-center justify-center p-6">
          <div className="w-full space-y-6">
            <header className="text-center">
              <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-xl bg-primary/15 text-primary ring-1 ring-primary/30">
                <ShieldCheck size={28} />
              </div>

              <p className="eyebrow">EchoShield</p>

              <h1 className="mt-3 text-3xl font-semibold text-foreground md:text-5xl">
                Upload a YouTube watch-history export
              </h1>

              <p className="mx-auto mt-4 max-w-2xl text-sm text-muted-foreground md:text-base">
                Upload a Google Takeout YouTube watch-history HTML or JSON file.
                EchoShield will create a pseudonymised profile, process the viewing
                history, and generate exposure, echo-signal, and temporal drift
                analytics.
              </p>
            </header>

            <WatchHistoryUpload onProfileReady={handleProfileReady} />

            <div className="panel p-4 text-xs leading-relaxed text-muted-foreground">
              <div className="flex items-start gap-3">
                <Upload className="mt-0.5 size-4 shrink-0 text-primary" />
                <p>
                  This prototype is intended for local demo processing only. It
                  creates pseudonymised profile IDs and provides explainable
                  review-support signals. It does not make automated wellbeing
                  decisions or diagnoses.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <DashboardContent profileId={profileId} onResetProfile={handleResetProfile} />
  );
}

function DashboardContent({
  profileId,
  onResetProfile,
}: {
  profileId: string;
  onResetProfile: () => void;
}) {
  const [overview, setOverview] = useState<ProfileOverview | null>(null);
  const [signals, setSignals] = useState<EchoSignal[]>([]);
  const [drifts, setDrifts] = useState<TemporalDrift[]>([]);
  const [topics, setTopics] = useState<TopicExposurePoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isCancelled = false;

    setIsLoading(true);
    setError(null);

    Promise.all([
      getProfileOverview(profileId),
      getEchoSignals(profileId),
      getTemporalDrift(profileId),
      getTopicTimeseries(profileId),
    ])
      .then(([overviewData, signalData, driftData, topicData]) => {
        if (isCancelled) return;

        setOverview(overviewData);
        setSignals(signalData);
        setDrifts(driftData);
        setTopics(topicData);
      })
      .catch((e) => {
        if (isCancelled) return;
        setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [profileId]);

  const latestDrift = [...drifts].sort(
    (a, b) =>
      +new Date(b.currentWindowStart) - +new Date(a.currentWindowStart),
  )[0];

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center p-8">
        <div className="panel max-w-md p-6 text-center">
          <AlertTriangle className="mx-auto mb-3 text-sev-high" />
          <h1 className="text-lg">API error</h1>
          <p className="mt-2 text-sm text-muted-foreground">{error}</p>

          <button
            onClick={onResetProfile}
            className="mt-5 rounded-md border border-border px-4 py-2 text-sm text-muted-foreground transition hover:bg-surface-2 hover:text-foreground"
          >
            Upload another watch history
          </button>
        </div>
      </main>
    );
  }

  if (isLoading) {
    return (
      <main className="scanlines flex min-h-screen items-center justify-center p-8">
        <div className="panel max-w-md p-6 text-center">
          <Activity className="mx-auto mb-3 animate-pulse text-primary" />
          <h1 className="text-lg">Loading exposure analytics</h1>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            {profileId}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="scanlines min-h-screen">
      <div className="mx-auto flex max-w-[1400px] gap-6 p-6">
        <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-64 shrink-0 flex-col gap-6 lg:flex">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/30">
              <ShieldCheck size={20} />
            </div>

            <div>
              <h1 className="text-lg font-semibold leading-none">EchoShield</h1>
              <p className="eyebrow mt-1">Exposure intelligence</p>
            </div>
          </div>

          <nav className="flex flex-col gap-1 text-sm">
            {[
              { label: "Profile overview", active: true },
              { label: "Exposure signals" },
              { label: "Temporal drift" },
              { label: "Content clusters" },
              { label: "Graph explorer" },
            ].map((item) => (
              <button
                key={item.label}
                className={`rounded-md px-3 py-2 text-left transition ${
                  item.active
                    ? "bg-primary/15 text-primary ring-1 ring-primary/30"
                    : "text-muted-foreground hover:bg-surface-2 hover:text-foreground"
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <button
            onClick={onResetProfile}
            className="rounded-md border border-border px-3 py-2 text-left text-sm text-muted-foreground transition hover:bg-surface-2 hover:text-foreground"
          >
            Analyse another watch history
          </button>

          <div className="mt-auto panel p-3 text-[11px] text-muted-foreground">
            <div className="flex items-center gap-2">
              <Radio
                size={12}
                className={USING_MOCK_DATA ? "text-sev-medium" : "text-sev-low"}
              />
              <span className="font-mono uppercase tracking-wider">
                {USING_MOCK_DATA ? "Demo data" : "Live API"}
              </span>
            </div>

            <p className="mt-1.5 leading-snug">
              {USING_MOCK_DATA
                ? "Set VITE_API_BASE_URL to point at your Spring Boot service."
                : "Connected to backend."}
            </p>
          </div>
        </aside>

        <section className="min-w-0 flex-1 space-y-6">
          <header className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="eyebrow">Pseudonymised profile</p>

              <h2 className="mt-2 font-mono text-3xl">
                {overview?.profileId ?? profileId}
              </h2>

              <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">
                Explainable content exposure patterns for a child profile —
                topic mix, echo-chamber clusters, and how viewing behaviour has
                drifted week over week.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={onResetProfile}
                className="rounded-full border border-border bg-surface-1 px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-surface-2 hover:text-foreground lg:hidden"
              >
                Analyse another
              </button>

              <div className="flex items-center gap-2 rounded-full border border-border bg-surface-1 px-3 py-1.5 text-xs">
                <span className="size-1.5 animate-pulse rounded-full bg-sev-low" />
                <span className="font-mono uppercase tracking-wider text-muted-foreground">
                  Read-only analytics
                </span>
              </div>
            </div>
          </header>

          <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCard
              icon={<BarChart3 size={16} />}
              label="Watch events"
              value={overview?.totalWatchEvents?.toLocaleString() ?? "—"}
              helper={
                overview?.uniqueVideos
                  ? `${overview.uniqueVideos} unique videos`
                  : "clustered activity"
              }
            />

            <MetricCard
              icon={<GitBranch size={16} />}
              label="Unique clusters"
              value={overview?.uniqueClusters?.toLocaleString() ?? "—"}
              helper={overview?.dominantParentTopic ?? "—"}
            />

            <MetricCard
              icon={<AlertTriangle size={16} />}
              label="Top echo score"
              value={formatScore(overview?.topEchoScore)}
              helper={<SeverityPill severity={overview?.topSeverity} />}
            />

            <MetricCard
              icon={<Activity size={16} />}
              label="Latest drift"
              value={formatScore(latestDrift?.driftScore)}
              helper={<SeverityPill severity={latestDrift?.severity} />}
            />
          </section>

          <section className="grid gap-6 lg:grid-cols-3">
            <Panel
              className="lg:col-span-2"
              title="Weekly topic exposure"
              subtitle="Normalized share of clustered watch events, by parent topic"
            >
              <TopicExposureChart points={topics} />
            </Panel>

            <Panel
              title="Latest temporal drift"
              subtitle="How the dominant content category has just shifted"
            >
              {latestDrift ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <SeverityPill severity={latestDrift.severity} />
                    <span className="font-mono text-xs text-muted-foreground">
                      {shortDate(latestDrift.currentWindowStart)} →{" "}
                      {shortDate(latestDrift.currentWindowEnd)}
                    </span>
                  </div>

                  <div>
                    <div className="font-mono text-4xl tabular">
                      {formatScore(latestDrift.driftScore)}
                      <span className="ml-1 text-base text-muted-foreground">
                        / 100
                      </span>
                    </div>

                    <p className="mt-2 text-sm">
                      <span className="text-muted-foreground">
                        {latestDrift.dominantTopicBefore}
                      </span>
                      <span className="mx-2 text-primary">→</span>
                      <span className="text-foreground">
                        {latestDrift.dominantTopicAfter}
                      </span>
                    </p>
                  </div>

                  <dl className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border pt-3 text-xs">
                    <StatRow
                      label="Topic drift"
                      value={latestDrift.topicDriftScore.toFixed(3)}
                    />
                    <StatRow
                      label="Cluster drift"
                      value={latestDrift.clusterDriftScore.toFixed(3)}
                    />
                    <StatRow
                      label="Novelty"
                      value={formatPercent(latestDrift.noveltyRatio)}
                    />
                    <StatRow
                      label="Risk delta"
                      value={latestDrift.riskExposureDelta.toFixed(3)}
                    />
                  </dl>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No temporal drift signal available.
                </p>
              )}
            </Panel>
          </section>

          <section className="grid gap-6 lg:grid-cols-5">
            <Panel
              className="lg:col-span-3"
              title="Echo chamber network"
              subtitle="Bubble = exposure share. Edges link co-occurring clusters within a parent topic."
            >
              <EchoNetworkGraph signals={signals} />
            </Panel>

            <Panel
              className="lg:col-span-2"
              title="Temporal drift flow"
              subtitle="How the dominant topic flows across weeks"
            >
              <DriftSankey drifts={drifts} />
            </Panel>
          </section>

          <Panel
            title="Risk severity timeline"
            subtitle="Weekly drift severity — escalation indicates a tightening echo chamber"
          >
            <RiskTimeline drifts={drifts} />
          </Panel>

          <Panel
            title="Top exposure signals"
            subtitle="Clusters ranked by echo score — repeated exposure within a narrow topic"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-muted-foreground">
                    <th className="py-2 pr-4 font-medium">Cluster</th>
                    <th className="py-2 pr-4 font-medium">Parent topic</th>
                    <th className="py-2 pr-4 text-right font-medium">
                      Exposure
                    </th>
                    <th className="py-2 pr-4 text-right font-medium">Trend</th>
                    <th className="py-2 pr-4 font-medium">Risk category</th>
                    <th className="py-2 pr-4 text-right font-medium">Score</th>
                    <th className="py-2 font-medium">Severity</th>
                  </tr>
                </thead>

                <tbody className="divide-y divide-border/60">
                  {signals.map((s) => (
                    <tr key={s.clusterId} className="hover:bg-surface-2/50">
                      <td className="py-2.5 pr-4">
                        <div className="font-medium text-foreground">
                          {s.displayLabel}
                        </div>
                        <div className="font-mono text-[11px] text-muted-foreground">
                          {s.clusterId}
                        </div>
                      </td>

                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {s.parentLabel}
                      </td>

                      <td className="py-2.5 pr-4 text-right font-mono tabular">
                        {formatPercent(s.currentExposureRatio)}
                      </td>

                      <td
                        className={`py-2.5 pr-4 text-right font-mono tabular ${
                          s.trendDelta > 0 ? "text-sev-high" : "text-sev-low"
                        }`}
                      >
                        {s.trendDelta > 0 ? "+" : ""}
                        {formatPercent(s.trendDelta)}
                      </td>

                      <td className="py-2.5 pr-4 text-muted-foreground">
                        {s.inferredRiskCategory}
                      </td>

                      <td className="py-2.5 pr-4 text-right font-mono tabular">
                        {formatScore(s.echoScore)}
                      </td>

                      <td className="py-2.5">
                        <SeverityPill severity={s.severity} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          <footer className="pb-4 pt-2 text-center text-[11px] text-muted-foreground">
            EchoShield · Pseudonymised exposure analytics ·{" "}
            {new Date().getFullYear()}
          </footer>
        </section>
      </div>
    </main>
  );
}

function MetricCard({
  icon,
  label,
  value,
  helper,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  helper: ReactNode;
}) {
  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between text-muted-foreground">
        <span className="eyebrow">{label}</span>
        <span className="text-primary">{icon}</span>
      </div>

      <div className="mt-2 font-mono text-2xl tabular text-foreground">
        {value}
      </div>

      <div className="mt-2 text-xs text-muted-foreground">{helper}</div>
    </div>
  );
}

function Panel({
  title,
  subtitle,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel p-5 ${className}`}>
      <header className="mb-4">
        <h3 className="text-base">{title}</h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
        )}
      </header>

      {children}
    </section>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="text-right font-mono tabular text-foreground">{value}</dd>
    </>
  );
}