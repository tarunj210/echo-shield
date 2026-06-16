package com.echoshield.api.service;

import com.echoshield.api.repository.AnalyticsRepository;
import org.springframework.stereotype.Service;
import com.echoshield.api.dto.*;


import java.util.List;

@Service
public class WatchSessionService {
    private final EmbeddingWorkerService embeddingWorkerService;
    private final AnalyticsRepository analyticsRepository;

    public WatchSessionService(AnalyticsRepository analyticsRepository,EmbeddingWorkerService embeddingWorkerService) {
        this.analyticsRepository = analyticsRepository;
        this.embeddingWorkerService = embeddingWorkerService;
    }

    public List<WatchSessionDto> getWatchSessions(String profileId, int limit) {
        int safeLimit = Math.min(Math.max(limit, 1), 100);
        return analyticsRepository.getWatchSessions(profileId, safeLimit);
    }

    public SessionTrajectoryDto getSessionTrajectory(
        String profileId,
        String sessionId
    ) {
        return analyticsRepository.getSessionTrajectory(profileId, sessionId);
    }

    public SessionSummaryGraphDto getSessionSummaryGraph(String profileId, int limit) {
        int safeLimit = Math.min(Math.max(limit, 5), 100);
        return analyticsRepository.getSessionSummaryGraph(profileId, safeLimit);
    }

    public EmbeddingProgressDto getEmbeddingProgress(String profileId) {
        return analyticsRepository.getEmbeddingProgress(profileId);
    }
    public EmbeddingProgressDto startEmbeddingJob(String profileId) {
        return embeddingWorkerService.startEmbeddingJob(profileId);
    }
}