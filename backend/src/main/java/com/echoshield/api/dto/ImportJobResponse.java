package com.echoshield.api.dto;

public record ImportJobResponse(
    String importJobId,
    String profileId,
    String status
) {}