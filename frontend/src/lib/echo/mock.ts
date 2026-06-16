import type {
    EchoSignal,
    ProfileOverview,
    TemporalDrift,
    TopicExposurePoint,
  } from "./types";
  
  const PARENT_TOPICS = [
    "Entertainment & Commentary",
    "Sports",
    "Motivation & Self-improvement",
    "Social & Lifestyle",
    "Technology & Computing",
    "Gaming & Streamers",
  ];
  
  function rand(seed: number) {
    let s = seed;
    return () => {
      s = (s * 9301 + 49297) % 233280;
      return s / 233280;
    };
  }
  
  export function mockOverview(profileId: string): ProfileOverview {
    return {
      profileId,
      totalWatchEvents: 4_823,
      uniqueVideos: 312,
      uniqueClusters: 27,
      reviewSignals: 4,
      dominantParentTopic: "Motivation & Self-improvement",
      topEchoScore: 0.87,
      topSeverity: "HIGH",
    };
  }
  
  export function mockEchoSignals(): EchoSignal[] {
    const rows: Array<Omit<EchoSignal, "clusterId">> = [
      { profileId: "profile_self", displayLabel: "Hyper-masculine 'alpha' commentary", parentLabel: "Motivation & Self-improvement", currentWatchCount: 842, currentTotalWatchCount: 4_823, currentExposureRatio: 0.31, previousExposureRatio: 0.17, trendDelta: 0.14, inferredRiskCategory: "Identity-narrowing", taxonomyRiskScore: 0.82, echoScore: 0.87, severity: "HIGH", explanation: "Exposure to hyper-masculine commentary rose 82% in 14 days.", calculatedAt: new Date(2026, 5, 10).toISOString() },
      { profileId: "profile_self", displayLabel: "Looksmaxxing & physique edits", parentLabel: "Social & Lifestyle", currentWatchCount: 482, currentTotalWatchCount: 4_823, currentExposureRatio: 0.18, previousExposureRatio: 0.09, trendDelta: 0.09, inferredRiskCategory: "Body image", taxonomyRiskScore: 0.71, echoScore: 0.74, severity: "HIGH", explanation: "Body-image related content doubled from prior window.", calculatedAt: new Date(2026, 5, 10).toISOString() },
      { profileId: "profile_self", displayLabel: "Edgy prank compilations", parentLabel: "Entertainment & Commentary", currentWatchCount: 321, currentTotalWatchCount: 4_823, currentExposureRatio: 0.12, previousExposureRatio: 0.08, trendDelta: 0.04, inferredRiskCategory: "Norm-erosion", taxonomyRiskScore: 0.58, echoScore: 0.61, severity: "MEDIUM", explanation: "Prank content exposure trending upward; associated with risk-adjacent behaviour.", calculatedAt: new Date(2026, 5, 10).toISOString() },
      { profileId: "profile_self", displayLabel: "Late-night gaming streamers", parentLabel: "Gaming & Streamers", currentWatchCount: 268, currentTotalWatchCount: 4_823, currentExposureRatio: 0.10, previousExposureRatio: 0.12, trendDelta: -0.02, inferredRiskCategory: "Sleep disruption", taxonomyRiskScore: 0.48, echoScore: 0.52, severity: "MEDIUM", explanation: "Gaming exposure slightly decreased but remains elevated post-22:00.", calculatedAt: new Date(2026, 5, 10).toISOString() },
      { profileId: "profile_self", displayLabel: "Crypto / get-rich shorts", parentLabel: "Motivation & Self-improvement", currentWatchCount: 214, currentTotalWatchCount: 4_823, currentExposureRatio: 0.08, previousExposureRatio: 0.02, trendDelta: 0.06, inferredRiskCategory: "Financial scam-adjacent", taxonomyRiskScore: 0.45, echoScore: 0.49, severity: "MEDIUM", explanation: "Sudden spike in financial 'guru' content; possible scam exposure.", calculatedAt: new Date(2026, 5, 10).toISOString() },
      { profileId: "profile_self", displayLabel: "Football skill edits", parentLabel: "Sports", currentWatchCount: 187, currentTotalWatchCount: 4_823, currentExposureRatio: 0.07, previousExposureRatio: 0.10, trendDelta: -0.03, inferredRiskCategory: "Low-risk", taxonomyRiskScore: 0.18, echoScore: 0.22, severity: "LOW", explanation: "Sports content declining proportionally as other topics grow.", calculatedAt: new Date(2026, 5, 10).toISOString() },
      { profileId: "profile_self", displayLabel: "Coding tutorials", parentLabel: "Technology & Computing", currentWatchCount: 134, currentTotalWatchCount: 4_823, currentExposureRatio: 0.05, previousExposureRatio: 0.10, trendDelta: -0.05, inferredRiskCategory: "Educational", taxonomyRiskScore: 0.10, echoScore: 0.14, severity: "INFO", explanation: "Educational content still present but shrinking as entertainment share rises.", calculatedAt: new Date(2026, 5, 10).toISOString() },
    ];
    return rows.map((r, i) => ({ ...r, clusterId: `cl_${String(i + 1).padStart(3, "0")}` }));
  }
  
  export function mockTemporalDrift(): TemporalDrift[] {
    const weeks = 8;
    const r = rand(7);
    const before = ["Sports", "Sports", "Entertainment & Commentary", "Entertainment & Commentary", "Social & Lifestyle", "Social & Lifestyle", "Motivation & Self-improvement", "Motivation & Self-improvement"];
    const after  = ["Sports", "Entertainment & Commentary", "Entertainment & Commentary", "Social & Lifestyle", "Social & Lifestyle", "Motivation & Self-improvement", "Motivation & Self-improvement", "Motivation & Self-improvement"];
    const severities = ["INFO", "LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "HIGH", "CRITICAL"];
    const out: TemporalDrift[] = [];
    for (let i = 0; i < weeks; i++) {
      const prevStart = new Date(2026, 3, 4 + (i - 1) * 7);
      const prevEnd = new Date(2026, 3, 10 + (i - 1) * 7);
      const start = new Date(2026, 3, 4 + i * 7);
      const end = new Date(2026, 3, 10 + i * 7);
      const baseDrift = 0.18 + i * 0.08 + r() * 0.05;
      out.push({
        profileId: "profile_self",
        granularity: "weekly",
        previousWindowStart: prevStart.toISOString(),
        previousWindowEnd: prevEnd.toISOString(),
        currentWindowStart: start.toISOString(),
        currentWindowEnd: end.toISOString(),
        dominantTopicBefore: before[i],
        dominantTopicAfter: after[i],
        topicDriftScore: Math.min(0.95, baseDrift),
        clusterDriftScore: Math.min(0.95, baseDrift * 0.9 + r() * 0.05),
        noveltyRatio: 0.1 + i * 0.04,
        riskExposureBefore: Math.max(0, 0.15 + (i - 1) * 0.06),
        riskExposureAfter: Math.max(0, 0.15 + i * 0.06),
        riskExposureDelta: i * 0.06 - 0.05,
        driftScore: Math.min(99, 18 + i * 9 + r() * 4),
        severity: severities[i],
        explanation: `Dominant topic shifted from ${before[i]} to ${after[i]} during this window.`,
      });
    }
    return out.reverse();
  }
  
  export function mockTopicTimeseries(): TopicExposurePoint[] {
    const weeks = 8;
    const out: TopicExposurePoint[] = [];
    const trajectory: Record<string, number[]> = {
      "Sports":                        [0.34, 0.31, 0.27, 0.22, 0.17, 0.12, 0.09, 0.07],
      "Entertainment & Commentary":    [0.22, 0.24, 0.27, 0.26, 0.24, 0.22, 0.18, 0.15],
      "Motivation & Self-improvement": [0.08, 0.11, 0.15, 0.21, 0.28, 0.34, 0.41, 0.46],
      "Social & Lifestyle":            [0.12, 0.14, 0.15, 0.16, 0.17, 0.18, 0.18, 0.17],
      "Technology & Computing":        [0.16, 0.12, 0.09, 0.08, 0.07, 0.07, 0.06, 0.05],
      "Gaming & Streamers":            [0.08, 0.08, 0.07, 0.07, 0.07, 0.07, 0.08, 0.10],
    };
    for (let i = 0; i < weeks; i++) {
      const start = new Date(2026, 3, 4 + i * 7);
      const end = new Date(2026, 3, 10 + i * 7);
      for (const topic of PARENT_TOPICS) {
        out.push({
          profileId: "profile_self",
          parentLabel: topic,
          granularity: "weekly",
          windowStart: start.toISOString(),
          windowEnd: end.toISOString(),
          watchCount: Math.round(trajectory[topic][i] * 4_823),
          totalWatchCount: 4_823,
          exposureRatio: trajectory[topic][i],
        });
      }
    }
    return out;
  }
  