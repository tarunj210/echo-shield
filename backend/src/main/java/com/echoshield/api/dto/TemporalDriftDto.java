package com.echoshield.api.dto;

import java.time.LocalDateTime;

public record TemporalDriftDto(
    String profileId,
    String granularity,
    LocalDateTime previousWindowStart,
    LocalDateTime previousWindowEnd,
    LocalDateTime currentWindowStart,
    LocalDateTime currentWindowEnd,
    String dominantTopicBefore,
    String dominantTopicAfter,
    Double topicDriftScore,
    Double clusterDriftScore,
    Double noveltyRatio,
    Double riskExposureBefore,
    Double riskExposureAfter,
    Double riskExposureDelta,
    Double driftScore,
    String severity,
    String explanation
) {}