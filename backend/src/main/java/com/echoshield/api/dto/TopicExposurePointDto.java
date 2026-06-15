package com.echoshield.api.dto;

import java.time.LocalDateTime;

public record TopicExposurePointDto(
    String profileId,
    String parentLabel,
    String granularity,
    LocalDateTime windowStart,
    LocalDateTime windowEnd,
    Integer watchCount,
    Integer totalWatchCount,
    Double exposureRatio
) {}