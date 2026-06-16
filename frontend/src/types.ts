export type ProfileOverview = {
    profileId: string;
    totalWatchEvents: number;
    uniqueVideos: number;
    uniqueClusters: number;
    reviewSignals: number;
    topEchoScore: number | null;
    topSeverity: string | null;
    dominantParentTopic: string | null;
  };
  
  export type EchoSignal = {
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
  };
  
  export type TemporalDrift = {
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
  };
  
  export type TopicExposurePoint = {
    profileId: string;
    parentLabel: string;
    granularity: string;
    windowStart: string;
    windowEnd: string;
    watchCount: number;
    totalWatchCount: number;
    exposureRatio: number;
  };