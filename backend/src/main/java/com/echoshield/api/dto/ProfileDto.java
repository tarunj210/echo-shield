package com.echoshield.api.dto;

import java.time.LocalDateTime;

public record ProfileDto(
    String profileId,
    String displayName,
    String profileType,
    LocalDateTime createdAt
) {}