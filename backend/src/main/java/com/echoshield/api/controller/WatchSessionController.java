package com.echoshield.api.controller;

import com.echoshield.api.dto.*;
import com.echoshield.api.service.WatchSessionService;
import org.springframework.web.bind.annotation.*;
import com.echoshield.api.dto.SessionSummaryGraphDto;
import java.util.List;

@RestController
@RequestMapping("/api/profiles")
public class WatchSessionController {

    private final WatchSessionService watchSessionService;

    public WatchSessionController(WatchSessionService watchSessionService) {
        this.watchSessionService = watchSessionService;
    }

    @GetMapping("/{profileId}/sessions")
    public List<WatchSessionDto> getWatchSessions(
        @PathVariable String profileId,
        @RequestParam(defaultValue = "30") int limit
    ) {
        return watchSessionService.getWatchSessions(profileId, limit);
    }

    @GetMapping("/{profileId}/sessions/{sessionId}/trajectory")
    public SessionTrajectoryDto getSessionTrajectory(
        @PathVariable String profileId,
        @PathVariable String sessionId
    ) {
        return watchSessionService.getSessionTrajectory(profileId, sessionId);
    }

    @GetMapping("/{profileId}/session-summary-graph")
    public SessionSummaryGraphDto getSessionSummaryGraph(
        @PathVariable String profileId,
        @RequestParam(defaultValue = "50") int limit
    ) {
        return watchSessionService.getSessionSummaryGraph(profileId, limit);
    }

    @GetMapping("/{profileId}/embedding-progress")
    public EmbeddingProgressDto getEmbeddingProgress(
        @PathVariable String profileId
    ) {
        return watchSessionService.getEmbeddingProgress(profileId);
    }
    @PostMapping("/{profileId}/embedding-jobs/start")
    public EmbeddingProgressDto startEmbeddingJob(
        @PathVariable String profileId
    ) {
        return watchSessionService.startEmbeddingJob(profileId);
    }
}