package com.echoshield.api.controller;
import com.echoshield.api.repository.AnalyticsRepository;
import com.echoshield.api.dto.*;
import com.echoshield.api.service.AnalyticsService;
import org.springframework.web.bind.annotation.*;
import com.echoshield.api.dto.SessionTrajectoryDto;
import com.echoshield.api.dto.WatchSessionDto;

import java.util.List;


@RestController
@RequestMapping("/api")
public class ProfileController {

    private final AnalyticsService analyticsService;

    public ProfileController(AnalyticsService analyticsService) {
        this.analyticsService = analyticsService;
    }

    @GetMapping("/profiles")
    public List<ProfileDto> getProfiles() {
        return analyticsService.getProfiles();
    }

    @GetMapping("/profiles/{profileId}/overview")
    public ProfileOverviewDto getProfileOverview(@PathVariable String profileId) {
        return analyticsService.getProfileOverview(profileId);
    }

    @GetMapping("/profiles/{profileId}/echo-signals")
    public List<EchoSignalDto> getEchoSignals(
        @PathVariable String profileId,
        @RequestParam(defaultValue = "20") int limit
    ) {
        return analyticsService.getEchoSignals(profileId, limit);
    }

    @GetMapping("/profiles/{profileId}/temporal-drift")
    public List<TemporalDriftDto> getTemporalDrift(
        @PathVariable String profileId,
        @RequestParam(defaultValue = "weekly") String granularity,
        @RequestParam(defaultValue = "20") int limit
    ) {
        return analyticsService.getTemporalDrift(profileId, granularity, limit);
    }

    @GetMapping("/profiles/{profileId}/topic-timeseries")
    public List<TopicExposurePointDto> getTopicTimeseries(
        @PathVariable String profileId,
        @RequestParam(defaultValue = "weekly") String granularity
    ) {
        return analyticsService.getTopicTimeseries(profileId, granularity);
    }

    
}