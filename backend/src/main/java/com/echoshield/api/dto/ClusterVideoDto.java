package com.echoshield.api.dto;

public record ClusterVideoDto(
    String videoId,
    String title,
    String channelTitle,
    String thumbnailUrl,
    Long viewCount,
    Long likeCount
) {}