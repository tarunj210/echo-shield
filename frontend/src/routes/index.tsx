import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  GitBranch,
  ShieldCheck,
  Upload,
} from "lucide-react";

import {
  getEchoSignals,
  getProfileOverview,
  getTemporalDrift,
  getTopicTimeseries,
  getSessionTrajectory,
  getSessionSummaryGraph,
  getEmbeddingProgress,
  startEmbeddingJob,
} from "@/lib/echo/client";

import type {
  EchoSignal,
  ProfileOverview,
  TemporalDrift,
  TopicExposurePoint,
  SessionTrajectory,
  SessionSummaryGraph,
  EmbeddingProgress,
} from "@/lib/echo/types";

import { TopicExposureChart } from "@/components/echo/TopicExposure";
import { RiskTimeline } from "@/components/echo/RiskTimeline";
import { SeverityPill } from "@/components/echo/SeverityPill";
import { WatchHistoryUpload } from "@/components/echo/WatchHistoryUpload";
import { SessionTimeline } from "@/components/echo/SessionTimeline";
import { SessionBubbleTimeline } from "@/components/echo/SessionBubbleTimeline";

const TIME_WINDOW_OPTIONS = [
  { label: "1d", days: 1 },
  { label: "3d", days: 3 },
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
] as const;

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "EchoShield — Session Exposure Intelligence" },
      {
        name: "description",
        content:
          "Visualize YouTube watch sessions, topic concentration, channel diversity, and echo-chamber signals.",
      },
      {
        property: "og:title",
        content: "EchoShield — Session Exposure Intelligence",
      },
      {
        property: "og:description",
        content:
          "Session-level exposure map for timestamped YouTube Takeout history.",
      },
    ],
  }),
  component: DashboardRoute,
});

function DashboardRoute() {
  const [profileId, setProfileId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("echoshield_profile_id");
  });

  function LandingPage({
    onProfileReady,
  }: {
    onProfileReady: (profileId: string) => void;
  }) {
    const metrics = [
      {
        title: "Watch events",
        description: "Every recorded video interaction — the raw timeline behind every insight.",
      },
      {
        title: "Viewing sessions",
        description: "Videos grouped into continuous viewing bursts by timestamp gaps.",
      },
      {
        title: "Dominant topic",
        description: "The main content category taking most attention in a session or window.",
      },
      {
        title: "Topic exposure",
        description: "The share of viewing time assigned to each content category.",
      },
      {
        title: "Concentration score",
        description: "How repeatedly your attention returns to a narrow cluster of content.",
      },
      {
        title: "Channel diversity",
        description: "Whether a session spans many creators or circles a few sources.",
      },
      {
        title: "Temporal drift",
        description: "How dominant topics shift between time windows.",
      },
      {
        title: "Repeated exposure patterns",
        description: "Content clusters that appear most strongly across your watch history.",
      },
    ];
  
    const steps = [
      {
        title: "Upload watch history",
        text: "Import a Google Takeout YouTube export. EchoShield creates a pseudonymised local profile.",
      },
      {
        title: "Build sessions",
        text: "Raw events are grouped into viewing sessions using timestamp gaps.",
      },
      {
        title: "Map topics",
        text: "Videos are enriched with metadata and grouped into topic categories.",
      },
      {
        title: "Detect patterns",
        text: "Topic exposure, concentration, repeated viewing, and drift are calculated.",
      },
    ];
  
    return (
      <main className="scanlines min-h-screen">
        <div className="mx-auto max-w-7xl space-y-16 px-6 py-10 md:py-16">
  
          {/* Hero */}
          <section className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs text-primary">
                <Activity size={14} />
                Personal media intelligence
              </div>
  
              <h1 className="mt-6 max-w-4xl text-4xl font-semibold tracking-tight text-foreground md:text-6xl">
                See your media habits. Detect attention echo chambers.
              </h1>
  
              <p className="mt-5 max-w-xl text-base leading-7 text-muted-foreground">
                EchoShield turns YouTube watch history into a session-level map of
                topic exposure, content concentration, and attention drift.
              </p>
            </div>
  
            <div className="panel p-5">
              <div className="mb-4">
                <p className="eyebrow">Start analysis</p>
                <h2 className="mt-2 text-xl text-foreground">
                  Upload your watch-history export
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Use a Google Takeout YouTube watch-history HTML or JSON file.
                </p>
              </div>
  
              <WatchHistoryUpload onProfileReady={onProfileReady} />
  
              <div className="mt-4 rounded-xl border border-border bg-background p-4 text-xs leading-relaxed text-muted-foreground">
                EchoShield does not diagnose behaviour or classify content as good
                or bad. It makes viewing patterns easier to inspect.
              </div>
            </div>
          </section>
  
          {/* Three pillars */}
          <section className="grid gap-4 md:grid-cols-3">
            <LandingInfoCard
              icon={<BarChart3 size={18} />}
              title="Raw history is hard to read"
              text="Thousands of timestamped events become sessions, topics, and trends."
            />
            <LandingInfoCard
              icon={<GitBranch size={18} />}
              title="Sessions tell the real story"
              text="How attention flows across a viewing period matters more than individual videos."
            />
            <LandingInfoCard
              icon={<Activity size={18} />}
              title="Patterns become actionable"
              text="Identify recurring clusters and understand when attention narrows over time."
            />
          </section>
  
          {/* Echo chamber concept */}
          <section className="panel p-6 md:p-8">
            <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
              <div>
                <p className="eyebrow">Core concept</p>
                <h2 className="mt-2 text-3xl font-semibold text-foreground">
                  What is an attention echo chamber?
                </h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  Repeated exposure to a narrow cluster of semantically similar
                  content. Not necessarily harmful — just increasingly concentrated.
                </p>
              </div>
  
              <div className="grid gap-3 md:grid-cols-3">
                {[
                  { label: "Repetition", text: "Similar videos keep appearing." },
                  { label: "Narrowness", text: "Attention concentrates on few topics." },
                  { label: "Drift", text: "Viewing gradually moves into a tighter bubble." },
                ].map(({ label, text }) => (
                  <div key={label} className="rounded-xl border border-border bg-background p-4">
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
                    <p className="mt-2 text-sm leading-6 text-foreground">{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
  
          {/* How it works */}
          <section>
            <div className="mb-6 max-w-2xl">
              <p className="eyebrow">How it works</p>
              <h2 className="mt-2 text-3xl font-semibold text-foreground">
                From raw history to readable insights
              </h2>
            </div>
  
            <div className="grid gap-4 md:grid-cols-4">
              {steps.map((step, index) => (
                <div key={step.title} className="panel p-5">
                  <div className="mb-4 flex size-9 items-center justify-center rounded-lg bg-primary/10 font-mono text-sm text-primary">
                    {index + 1}
                  </div>
                  <h3 className="text-base text-foreground">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{step.text}</p>
                </div>
              ))}
            </div>
          </section>
  
          {/* Metrics */}
          <section>
            <div className="mb-6 max-w-2xl">
              <p className="eyebrow">Metrics explained</p>
              <h2 className="mt-2 text-3xl font-semibold text-foreground">
                Every metric has a purpose
              </h2>
            </div>
  
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
              {metrics.map((metric) => (
                <div key={metric.title} className="panel p-4">
                  <h3 className="text-sm font-medium text-foreground">{metric.title}</h3>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{metric.description}</p>
                </div>
              ))}
            </div>
          </section>
  
          {/* Questions */}
          <section className="panel overflow-hidden p-0">
            <div className="grid gap-0 lg:grid-cols-[0.9fr_1.1fr]">
              <div className="border-b border-border p-6 lg:border-b-0 lg:border-r">
                <p className="eyebrow">What it helps you answer</p>
                <h2 className="mt-2 text-2xl font-semibold text-foreground">
                  Questions the dashboard is built to answer
                </h2>
              </div>
  
              <div className="grid gap-3 p-6 sm:grid-cols-2">
                {[
                  "What topics dominate my recent viewing?",
                  "Am I repeatedly watching similar content?",
                  "Are my sessions broad or concentrated?",
                  "How has my attention changed over time?",
                  "Which clusters appear repeatedly?",
                  "Where is my viewing becoming narrower?",
                ].map((text) => (
                  <QuestionCard key={text} text={text} />
                ))}
              </div>
            </div>
          </section>
  
          <footer className="pb-4 text-center text-[11px] text-muted-foreground">
            EchoShield · Personal content exposure analytics · {new Date().getFullYear()}
          </footer>
        </div>
      </main>
    );
  }
  
  function LandingInfoCard({
    icon,
    title,
    text,
  }: {
    icon: ReactNode;
    title: string;
    text: string;
  }) {
    return (
      <div className="panel p-5">
        <div className="mb-4 flex size-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          {icon}
        </div>
        <h3 className="text-base text-foreground">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p>
      </div>
    );
  }

  
  function MetricExplainerCard({
    metric,
  }: {
    metric: {
      title: string;
      description: string;
      whyNeeded: string;
      impact: string;
    };
  }) {
    return (
      <div className="panel p-5">
        <h3 className="text-lg text-foreground">{metric.title}</h3>
  
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          {metric.description}
        </p>
  
        <div className="mt-5 grid gap-3">
          <div className="rounded-xl border border-border bg-background p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Why this is needed
            </div>
  
            <p className="mt-2 text-sm leading-6 text-foreground">
              {metric.whyNeeded}
            </p>
          </div>
  
          <div className="rounded-xl border border-border bg-background p-4">
            <div className="text-xs uppercase tracking-wider text-muted-foreground">
              Impact
            </div>
  
            <p className="mt-2 text-sm leading-6 text-foreground">
              {metric.impact}
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  function QuestionCard({ text }: { text: string }) {
    return (
      <div className="rounded-xl border border-border bg-background p-4 text-sm leading-6 text-foreground">
        {text}
      </div>
    );
  }

  function handleProfileReady(nextProfileId: string) {
    localStorage.setItem("echoshield_profile_id", nextProfileId);
    setProfileId(nextProfileId);
  }

  function handleResetProfile() {
    localStorage.removeItem("echoshield_profile_id");
    setProfileId(null);
  }

  if (!profileId) {
    return <LandingPage onProfileReady={handleProfileReady} />;
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

  const [sessionGraph, setSessionGraph] = useState<SessionSummaryGraph | null>(
    null,
  );

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null,
  );

  const [trajectory, setTrajectory] = useState<SessionTrajectory | null>(null);

  const [timeWindowIndex, setTimeWindowIndex] = useState(2);
  const [topicFilter, setTopicFilter] = useState<string>("all");
  const [echoFilter, setEchoFilter] = useState<
    "all" | "low" | "medium" | "high"
  >("all");

  const [embeddingProgress, setEmbeddingProgress] =
    useState<EmbeddingProgress | null>(null);

  const [embeddingError, setEmbeddingError] = useState<string | null>(null);

  const embeddingStartAttemptedRef = useRef<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTrajectoryLoading, setIsTrajectoryLoading] = useState(false);

  useEffect(() => {
    let isCancelled = false;

    setIsLoading(true);
    setError(null);

    setOverview(null);
    setSignals([]);
    setDrifts([]);
    setTopics([]);
    setSessionGraph(null);
    setSelectedSessionId(null);
    setTrajectory(null);

    setEmbeddingProgress(null);
    setEmbeddingError(null);
    embeddingStartAttemptedRef.current = null;

    Promise.all([
      getProfileOverview(profileId),
      getEchoSignals(profileId),
      getTemporalDrift(profileId),
      getTopicTimeseries(profileId),
      getSessionSummaryGraph(profileId, 1000),
    ])
      .then(
        ([
          overviewData,
          signalData,
          driftData,
          topicData,
          sessionGraphData,
        ]) => {
          if (isCancelled) return;

          setOverview(overviewData);
          setSignals(signalData);
          setDrifts(driftData);
          setTopics(topicData);
          setSessionGraph(sessionGraphData);

          if (sessionGraphData.nodes.length > 0) {
            setSelectedSessionId(sessionGraphData.nodes[0].id);
          }

          if (embeddingStartAttemptedRef.current !== profileId) {
            embeddingStartAttemptedRef.current = profileId;

            startEmbeddingJob(profileId)
              .then((progress) => {
                if (isCancelled) return;
                setEmbeddingProgress(progress);
              })
              .catch((startError) => {
                if (isCancelled) return;

                setEmbeddingError(
                  startError instanceof Error
                    ? startError.message
                    : String(startError),
                );
              });
          }
        },
      )
      .catch((loadError) => {
        if (isCancelled) return;

        setError(
          loadError instanceof Error ? loadError.message : String(loadError),
        );
      })
      .finally(() => {
        if (isCancelled) return;
        setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [profileId]);

  useEffect(() => {
    let isCancelled = false;
    let intervalId: number | null = null;

    async function refreshEnrichedDashboardData() {
      const [
        refreshedSignals,
        refreshedDrifts,
        refreshedTopics,
        refreshedGraph,
      ] = await Promise.all([
        getEchoSignals(profileId),
        getTemporalDrift(profileId),
        getTopicTimeseries(profileId),
        getSessionSummaryGraph(profileId, 1000),
      ]);

      if (isCancelled) return;

      setSignals(refreshedSignals);
      setDrifts(refreshedDrifts);
      setTopics(refreshedTopics);
      setSessionGraph(refreshedGraph);
    }

    async function pollEmbeddingProgress() {
      try {
        const progress = await getEmbeddingProgress(profileId);

        if (isCancelled) return;

        setEmbeddingProgress(progress);

        if (
          progress.status === "PENDING" ||
          progress.status === "RUNNING" ||
          progress.status === "ENRICHING"
        ) {
          const refreshedGraph = await getSessionSummaryGraph(profileId, 1000);

          if (!isCancelled) {
            setSessionGraph(refreshedGraph);
          }

          return;
        }

        if (progress.status === "COMPLETED") {
          await refreshEnrichedDashboardData();

          if (intervalId != null) {
            window.clearInterval(intervalId);
            intervalId = null;
          }

          return;
        }

        if (progress.status === "FAILED") {
          if (intervalId != null) {
            window.clearInterval(intervalId);
            intervalId = null;
          }
        }
      } catch (pollError) {
        if (isCancelled) return;

        setEmbeddingError(
          pollError instanceof Error ? pollError.message : String(pollError),
        );
      }
    }

    pollEmbeddingProgress();
    intervalId = window.setInterval(pollEmbeddingProgress, 5000);

    return () => {
      isCancelled = true;

      if (intervalId != null) {
        window.clearInterval(intervalId);
      }
    };
  }, [profileId]);

  const latestDrift = [...drifts].sort(
    (a, b) =>
      +new Date(b.currentWindowStart) - +new Date(a.currentWindowStart),
  )[0];

  const selectedTimeWindow =
    TIME_WINDOW_OPTIONS[timeWindowIndex] ?? TIME_WINDOW_OPTIONS[2];

  const effectiveTimeWindowDays = selectedTimeWindow.days;
  const timeWindowLabel = `Last ${effectiveTimeWindowDays} days`;

  const latestSessionTime = sessionGraph
    ? getLatestSessionTime(sessionGraph)
    : Date.now();

  const timelineDomainEndTime = latestSessionTime;
  const timelineDomainStartTime =
    timelineDomainEndTime - effectiveTimeWindowDays * 24 * 60 * 60 * 1000;

  const filteredSessionGraph = useMemo(() => {
    if (!sessionGraph) return null;

    return filterSessionGraph(
      sessionGraph,
      effectiveTimeWindowDays,
      topicFilter,
      echoFilter,
    );
  }, [sessionGraph, effectiveTimeWindowDays, topicFilter, echoFilter]);

  const availableTopics = sessionGraph
    ? Array.from(
        new Set(
          sessionGraph.nodes
            .map((node) => node.dominantParentTopic)
            .filter(Boolean),
        ),
      ).sort()
    : [];

  const selectedSessionNode =
    sessionGraph?.nodes.find((node) => node.id === selectedSessionId) ?? null;

  const shouldShowEmbeddingCard =
    embeddingError != null ||
    (embeddingProgress != null &&
      embeddingProgress.status !== "NOT_STARTED");

  useEffect(() => {
    if (!filteredSessionGraph || filteredSessionGraph.nodes.length === 0) {
      setSelectedSessionId(null);
      return;
    }

    const selectedStillVisible = filteredSessionGraph.nodes.some(
      (node) => node.id === selectedSessionId,
    );

    if (!selectedStillVisible) {
      setSelectedSessionId(filteredSessionGraph.nodes[0].id);
    }
  }, [filteredSessionGraph, selectedSessionId]);

  useEffect(() => {
    if (!selectedSessionId) {
      setTrajectory(null);
      return;
    }

    let isCancelled = false;

    setIsTrajectoryLoading(true);
    setTrajectory(null);
    setError(null);

    getSessionTrajectory(profileId, selectedSessionId)
      .then((trajectoryData) => {
        if (isCancelled) return;
        setTrajectory(trajectoryData);
      })
      .catch((trajectoryError) => {
        if (isCancelled) return;

        setError(
          trajectoryError instanceof Error
            ? trajectoryError.message
            : String(trajectoryError),
        );
      })
      .finally(() => {
        if (isCancelled) return;
        setIsTrajectoryLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [profileId, selectedSessionId]);

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
          <h1 className="text-lg">Loading session exposure analytics</h1>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            {profileId}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="scanlines min-h-screen">
      <div className="mx-auto max-w-[1400px] space-y-6 p-6">
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">Pseudonymised profile</p>

            <h2 className="mt-2 font-mono text-3xl">
              {overview?.profileId ?? profileId}
            </h2>

            <p className="mt-1.5 max-w-xl text-sm text-muted-foreground">
              Session-level exposure intelligence built from timestamped YouTube
              Takeout events. Each bubble is a viewing session, positioned over
              time and grouped by dominant parent topic.
            </p>
          </div>

          <button
            onClick={onResetProfile}
            className="rounded-full border border-border bg-surface-1 px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-surface-2 hover:text-foreground"
          >
            Analyse another
          </button>
        </header>

        <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCard
            icon={<BarChart3 size={16} />}
            label="Watch events"
            value={overview?.totalWatchEvents?.toLocaleString() ?? "—"}
            helper={
              overview?.uniqueVideos
                ? `${overview.uniqueVideos} unique videos`
                : "timestamped activity"
            }
          />

          <MetricCard
            icon={<GitBranch size={16} />}
            label="Visible sessions"
            value={(filteredSessionGraph?.nodes.length ?? 0).toLocaleString()}
            helper={timeWindowLabel}
          />

          <MetricCard
            icon={<AlertTriangle size={16} />}
            label="Selected echo score"
            value={formatScore(selectedSessionNode?.echoScore)}
            helper={
              <SeverityPill
                severity={selectedSessionNode?.echoSeverity ?? "info"}
              />
            }
          />

          <MetricCard
            icon={<Activity size={16} />}
            label="Latest drift"
            value={formatScore(latestDrift?.driftScore)}
            helper={<SeverityPill severity={latestDrift?.severity ?? "info"} />}
          />
        </section>

        {shouldShowEmbeddingCard && (
          <EmbeddingProgressCard
            progress={embeddingProgress}
            error={embeddingError}
          />
        )}

        <section className="grid gap-6 lg:grid-cols-4">
          <Panel
            className="lg:col-span-3"
            title="Session bubble timeline"
            subtitle="Bubble = session · x-axis = time · y-axis = topic · size = duration · opacity = diversity · border = echo signal"
          >
            <div className="mb-4 space-y-4">
              <div className="rounded-xl border border-border bg-background p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground">
                      Time window
                    </div>

                    <div className="mt-1 font-mono text-lg text-foreground">
                      {timeWindowLabel}
                    </div>
                  </div>

                  <button
                    onClick={() =>
                      setTimeWindowIndex(TIME_WINDOW_OPTIONS.length - 1)
                    }
                    className="rounded-md border border-border px-3 py-2 text-xs text-muted-foreground transition hover:bg-surface-2 hover:text-foreground"
                  >
                    Last 14d
                  </button>
                </div>

                <input
                  type="range"
                  min={0}
                  max={TIME_WINDOW_OPTIONS.length - 1}
                  step={1}
                  value={timeWindowIndex}
                  onChange={(event) =>
                    setTimeWindowIndex(Number(event.target.value))
                  }
                  className="mt-4 w-full accent-primary"
                />

                <div className="mt-2 grid grid-cols-4 font-mono text-[11px] text-muted-foreground">
                  {TIME_WINDOW_OPTIONS.map((option) => (
                    <span
                      key={option.label}
                      className="text-center first:text-left last:text-right"
                    >
                      {option.label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <select
                  value={topicFilter}
                  onChange={(event) => setTopicFilter(event.target.value)}
                  className="rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground"
                >
                  <option value="all">All topics</option>

                  {availableTopics.map((topic) => (
                    <option key={topic} value={topic}>
                      {topic}
                    </option>
                  ))}
                </select>

                <select
                  value={echoFilter}
                  onChange={(event) =>
                    setEchoFilter(
                      event.target.value as "all" | "low" | "medium" | "high",
                    )
                  }
                  className="rounded-md border border-border bg-background px-3 py-2 text-xs text-foreground"
                >
                  <option value="all">All echo levels</option>
                  <option value="low">Low and above</option>
                  <option value="medium">Medium and above</option>
                  <option value="high">High only</option>
                </select>

                <div className="rounded-md border border-border bg-surface-1 px-3 py-2 text-xs text-muted-foreground">
                  Showing{" "}
                  <span className="font-mono text-foreground">
                    {filteredSessionGraph?.nodes.length ?? 0}
                  </span>{" "}
                  sessions
                </div>
              </div>
            </div>

            {filteredSessionGraph && filteredSessionGraph.nodes.length > 0 ? (
              <SessionBubbleTimeline
                graph={filteredSessionGraph}
                selectedSessionId={selectedSessionId}
                onSelectSession={setSelectedSessionId}
                domainStartTime={timelineDomainStartTime}
                domainEndTime={timelineDomainEndTime}
              />
            ) : (
              <div className="flex h-[420px] items-center justify-center rounded-xl border border-border bg-background">
                <p className="text-sm text-muted-foreground">
                  No sessions match the selected filters.
                </p>
              </div>
            )}
          </Panel>

          <Panel
            className="lg:col-span-1"
            title="Selected session videos"
            subtitle="Videos watched in order"
          >
            {isTrajectoryLoading ? (
              <div className="flex h-[420px] items-center justify-center rounded-xl border border-border bg-background">
                <div className="text-center">
                  <Activity className="mx-auto mb-3 animate-pulse text-primary" />
                  <p className="text-sm text-muted-foreground">
                    Loading selected session...
                  </p>
                </div>
              </div>
            ) : trajectory ? (
              <SessionTimeline items={trajectory.timeline} />
            ) : (
              <p className="text-sm text-muted-foreground">
                Select a bubble to view videos.
              </p>
            )}
          </Panel>
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
                  <th className="py-2 pr-4 text-right font-medium">Exposure</th>
                  <th className="py-2 pr-4 text-right font-medium">Trend</th>
                  <th className="py-2 pr-4 font-medium">Risk category</th>
                  <th className="py-2 pr-4 text-right font-medium">Score</th>
                  <th className="py-2 font-medium">Severity</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-border/60">
                {signals.map((signal) => (
                  <tr key={signal.clusterId} className="hover:bg-surface-2/50">
                    <td className="py-2.5 pr-4">
                      <div className="font-medium text-foreground">
                        {signal.displayLabel}
                      </div>

                      <div className="font-mono text-[11px] text-muted-foreground">
                        {signal.clusterId}
                      </div>
                    </td>

                    <td className="py-2.5 pr-4 text-muted-foreground">
                      {signal.parentLabel}
                    </td>

                    <td className="py-2.5 pr-4 text-right font-mono tabular">
                      {formatPercent(signal.currentExposureRatio)}
                    </td>

                    <td
                      className={`py-2.5 pr-4 text-right font-mono tabular ${
                        signal.trendDelta > 0 ? "text-sev-high" : "text-sev-low"
                      }`}
                    >
                      {signal.trendDelta > 0 ? "+" : ""}
                      {formatPercent(signal.trendDelta)}
                    </td>

                    <td className="py-2.5 pr-4 text-muted-foreground">
                      {signal.inferredRiskCategory}
                    </td>

                    <td className="py-2.5 pr-4 text-right font-mono tabular">
                      {formatScore(signal.echoScore)}
                    </td>

                    <td className="py-2.5">
                      <SeverityPill severity={signal.severity} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {signals.length === 0 && (
              <div className="rounded-xl border border-border bg-background p-6 text-sm text-muted-foreground">
                No exposure signals available yet. This section will populate
                after semantic clustering, taxonomy mapping, and echo-score
                calculation complete successfully.
              </div>
            )}
          </div>
        </Panel>

        <footer className="pb-4 pt-2 text-center text-[11px] text-muted-foreground">
          EchoShield · Pseudonymised session exposure analytics ·{" "}
          {new Date().getFullYear()}
        </footer>
      </div>
    </main>
  );
}

function EmbeddingProgressCard({
  progress,
  error,
}: {
  progress: EmbeddingProgress | null;
  error: string | null;
}) {
  const progressPercent = Math.max(
    0,
    Math.min(100, progress?.progressPercent ?? 0),
  );

  const status = progress?.status ?? "NOT_STARTED";
  const isFailed = status === "FAILED";

  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Embedding enrichment
          </div>

          <div className="mt-1 text-sm text-foreground">
            {status === "NOT_STARTED" && "Waiting to start embedding job"}
            {status === "PENDING" && "Embedding job queued"}
            {status === "RUNNING" &&
              `${progress?.embeddedVideos.toLocaleString()} / ${progress?.totalVideos.toLocaleString()} videos embedded`}
            {status === "ENRICHING" &&
              "Building clusters, taxonomy labels, echo scores, and drift signals"}
            {status === "COMPLETED" && "Embedding and enrichment completed"}
            {status === "FAILED" && "Embedding or enrichment job failed"}
          </div>

          <div className="mt-1 text-xs text-muted-foreground">
            Echo scores, topic exposure, temporal drift, and exposure signals
            refresh after enrichment completes.
          </div>
        </div>

        <div
          className={`font-mono text-sm ${
            isFailed ? "text-sev-high" : "text-primary"
          }`}
        >
          {progressPercent.toFixed(1)}%
        </div>
      </div>

      <div className="mt-3 h-2 overflow-hidden rounded-full bg-background">
        <div
          className={`h-full rounded-full ${
            isFailed ? "bg-sev-high" : "bg-primary"
          }`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="mt-2 flex flex-wrap justify-between gap-2 text-[11px] text-muted-foreground">
        <span>Status: {status}</span>
        <span>Failed: {progress?.failedVideos.toLocaleString() ?? 0}</span>
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-sev-high/30 bg-sev-high/10 p-3 text-xs text-sev-high">
          {error}
        </div>
      )}
    </div>
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

function formatPercent(value: number | null | undefined) {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function formatScore(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toFixed(2);
}

function shortDate(value: string) {
  return new Date(value).toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
  });
}

function getLatestSessionTime(graph: SessionSummaryGraph) {
  if (graph.nodes.length === 0) {
    return Date.now();
  }

  return Math.max(
    ...graph.nodes.map((node) => new Date(node.sessionStart).getTime()),
  );
}

function filterSessionGraph(
  graph: SessionSummaryGraph,
  timeWindowDays: number,
  topicFilter: string,
  echoFilter: "all" | "low" | "medium" | "high",
): SessionSummaryGraph {
  if (graph.nodes.length === 0) {
    return graph;
  }

  const latestSessionTime = getLatestSessionTime(graph);
  const minTime = latestSessionTime - timeWindowDays * 24 * 60 * 60 * 1000;

  const minEchoRank =
    echoFilter === "high"
      ? 3
      : echoFilter === "medium"
        ? 2
        : echoFilter === "low"
          ? 1
          : 0;

  const visibleNodes = graph.nodes.filter((node) => {
    const sessionTime = new Date(node.sessionStart).getTime();

    const matchesTimeWindow = sessionTime >= minTime;

    const matchesTopic =
      topicFilter === "all" || node.dominantParentTopic === topicFilter;

    const matchesEcho = echoRank(node.echoSeverity) >= minEchoRank;

    return matchesTimeWindow && matchesTopic && matchesEcho;
  });

  const visibleNodeIds = new Set(visibleNodes.map((node) => node.id));

  const visibleEdges = graph.edges.filter(
    (edge) =>
      visibleNodeIds.has(String(edge.source)) &&
      visibleNodeIds.has(String(edge.target)),
  );

  return {
    ...graph,
    nodes: visibleNodes,
    edges: visibleEdges,
  };
}

function echoRank(severity: string | null | undefined) {
  if (severity === "high") return 3;
  if (severity === "medium") return 2;
  if (severity === "low") return 1;
  return 0;
}