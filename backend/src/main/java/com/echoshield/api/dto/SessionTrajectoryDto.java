package com.echoshield.api.dto;

import java.time.LocalDateTime;
import java.util.List;

public record SessionTrajectoryDto(
    String profileId,
    String sessionId,
    List<TrajectoryNodeDto> nodes,
    List<TrajectoryEdgeDto> edges,
    List<TrajectoryTimelineItemDto> timeline
) {
    public record TrajectoryNodeDto(
        String id,
        String type,
        String label,
        String videoId,
        String channelId,
        String channelTitle,
        String thumbnailUrl,
        LocalDateTime watchedAt,
        Integer sequenceIndex
    ) {}

    public record TrajectoryEdgeDto(
        String source,
        String target,
        String type,
        Integer minutesBetween
    ) {}

    public record TrajectoryTimelineItemDto(
        String eventId,
        String videoId,
        String title,
        String channelTitle,
        String thumbnailUrl,
        LocalDateTime watchedAt,
        Integer minutesSincePrevious,
        Integer sequenceIndex
    ) {}
}