package com.echoshield.api.dto;

import java.time.LocalDateTime;

public record WatchSessionDto(
    String sessionId,
    String profileId,
    Integer sessionIndex,
    LocalDateTime sessionStart,
    LocalDateTime sessionEnd,
    Integer videoCount,
    Integer uniqueChannelCount,
    String dominantChannelTitle,
    Integer totalDurationMinutes
) {}