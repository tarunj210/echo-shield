export type Severity = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ProfileOverview {
  profileId: string;
  totalWatchEvents: number;
  uniqueVideos: number;
  uniqueClusters: number;
  reviewSignals: number;
  topEchoScore: number | null;
  topSeverity: string | null;
  dominantParentTopic: string | null;
}

export interface EchoSignal {
  profileId: string;
  clusterId: string;
  displayLabel: string;
  parentLabel: string;
  currentWatchCount: number;
  currentTotalWatchCount: number;
  currentExposureRatio: number;
  previousExposureRatio: number;
  trendDelta: number;
  inferredRiskCategory: string;
  taxonomyRiskScore: number | null;
  echoScore: number;
  severity: string;
  explanation: string;
  calculatedAt: string;
}

export interface TemporalDrift {
  profileId: string;
  granularity: string;
  previousWindowStart: string;
  previousWindowEnd: string;
  currentWindowStart: string;
  currentWindowEnd: string;
  dominantTopicBefore: string;
  dominantTopicAfter: string;
  topicDriftScore: number;
  clusterDriftScore: number;
  noveltyRatio: number;
  riskExposureBefore: number;
  riskExposureAfter: number;
  riskExposureDelta: number;
  driftScore: number;
  severity: string;
  explanation: string;
}

export interface TopicExposurePoint {
  profileId: string;
  parentLabel: string;
  granularity: string;
  windowStart: string;
  windowEnd: string;
  watchCount: number;
  totalWatchCount: number;
  exposureRatio: number;
}

export type WatchSession = {
    sessionId: string;
    profileId: string;
    sessionIndex: number;
    sessionStart: string;
    sessionEnd: string;
    videoCount: number;
    uniqueChannelCount: number;
    dominantChannelTitle: string | null;
    totalDurationMinutes: number;
  };
  
export type TrajectoryNode = {
    id: string;
    type: "watch_event" | "video" | "channel";
    label: string;
    videoId: string | null;
    channelId: string | null;
    channelTitle: string | null;
    thumbnailUrl: string | null;
    watchedAt: string | null;
    sequenceIndex: number | null;
  };
  
  export type TrajectoryEdge = {
    source: string;
    target: string;
    type: "NEXT_WATCH" | "WATCHED_VIDEO" | "PUBLISHED_BY";
    minutesBetween: number | null;
  };
  
  export type TrajectoryTimelineItem = {
    eventId: string;
    videoId: string;
    title: string;
    channelTitle: string;
    thumbnailUrl: string | null;
    watchedAt: string;
    minutesSincePrevious: number | null;
    sequenceIndex: number;
  };
  
  export type SessionTrajectory = {
    profileId: string;
    sessionId: string;
    nodes: TrajectoryNode[];
    edges: TrajectoryEdge[];
    timeline: TrajectoryTimelineItem[];
  };

  export type SessionTopicBreakdown = {
    parentTopic: string;
    videoCount: number;
  };
  
  export type SessionSummaryNode = {
    id: string;
    label: string;
    sessionIndex: number;
    sessionStart: string;
    sessionEnd: string;
    videoCount: number;
    uniqueChannelCount: number;
    durationMinutes: number;
    dominantChannelTitle: string | null;
    dominantParentTopic: string;
    dominantTopicVideoCount: number;
    channelDiversity: number;
    topicConcentration: number;
    topicBreakdown: SessionTopicBreakdown[];
    echoScore: number;
    echoSeverity: "info" | "low" | "medium" | "high";
    dominantEchoClusterId: string | null;
    dominantEchoClusterLabel: string | null;
    highEchoVideoCount: number;
  };
  
export type SessionSummaryEdge = {
    source: string;
    target: string;
    type: "NEXT_SESSION";
  };
  
export type SessionSummaryGraph = {
    profileId: string;
    nodes: SessionSummaryNode[];
    edges: SessionSummaryEdge[];
  };

export type EmbeddingProgressStatus =
  | "NOT_STARTED"
  | "PENDING"
  | "RUNNING"
  | "ENRICHING"
  | "COMPLETED"
  | "FAILED";

export type EmbeddingProgress = {
  embeddingJobId: string | null;
  profileId: string;
  status: EmbeddingProgressStatus;
  totalVideos: number;
  embeddedVideos: number;
  failedVideos: number;
  progressPercent: number;
};
