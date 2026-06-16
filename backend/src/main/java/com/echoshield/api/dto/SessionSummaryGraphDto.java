package com.echoshield.api.dto;

import java.time.LocalDateTime;
import java.util.List;

public record SessionSummaryGraphDto(
    String profileId,
    List<SessionNodeDto> nodes,
    List<SessionEdgeDto> edges
) {
    public record SessionNodeDto(
        String id,
        String label,
        Integer sessionIndex,
        LocalDateTime sessionStart,
        LocalDateTime sessionEnd,
        Integer videoCount,
        Integer uniqueChannelCount,
        Integer durationMinutes,
        String dominantChannelTitle,
        String dominantParentTopic,
        Integer dominantTopicVideoCount,
        Double channelDiversity,
        Double topicConcentration,

        Double echoScore,
        String echoSeverity,
        String dominantEchoClusterId,
        String dominantEchoClusterLabel,
        Integer highEchoVideoCount,

        List<TopicBreakdownDto> topicBreakdown
    ) {}

    public record SessionEdgeDto(
        String source,
        String target,
        String type
    ) {}

    public record TopicBreakdownDto(
        String parentTopic,
        Integer videoCount
    ) {}
}