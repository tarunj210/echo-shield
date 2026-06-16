package com.echoshield.api.dto;

import java.util.UUID;

public record EmbeddingProgressDto(
    UUID embeddingJobId,
    String profileId,
    String status,
    Integer totalVideos,
    Integer embeddedVideos,
    Integer failedVideos,
    Double progressPercent
) {}