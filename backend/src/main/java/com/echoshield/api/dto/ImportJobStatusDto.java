package com.echoshield.api.dto;

import java.time.LocalDateTime;

public record ImportJobStatusDto(
    String importJobId,
    String profileId,
    String source,
    String status,
    String originalFilename,
    Integer totalEvents,
    Integer insertedEvents,
    String errorMessage,
    LocalDateTime createdAt,
    LocalDateTime startedAt,
    LocalDateTime completedAt
) {}