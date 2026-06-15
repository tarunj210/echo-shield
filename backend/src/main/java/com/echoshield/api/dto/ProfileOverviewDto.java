package com.echoshield.api.dto;

public record ProfileOverviewDto(
    String profileId,
    long totalWatchEvents,
    long uniqueVideos,
    long uniqueClusters,
    long reviewSignals,
    Double topEchoScore,
    String topSeverity,
    String dominantParentTopic
) {}