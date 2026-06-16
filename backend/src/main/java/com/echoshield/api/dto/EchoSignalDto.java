package com.echoshield.api.dto;

import java.time.LocalDateTime;

public record EchoSignalDto(
    String profileId,
    String clusterId,
    String displayLabel,
    String parentLabel,
    Integer currentWatchCount,
    Integer currentTotalWatchCount,
    Double currentExposureRatio,
    Double previousExposureRatio,
    Double trendDelta,
    String inferredRiskCategory,
    Double taxonomyRiskScore,
    Double echoScore,
    String severity,
    String explanation,
    LocalDateTime calculatedAt
) {}