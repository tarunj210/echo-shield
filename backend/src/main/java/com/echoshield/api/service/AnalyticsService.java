package com.echoshield.api.service;

import com.echoshield.api.dto.*;
import com.echoshield.api.repository.AnalyticsRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class AnalyticsService {

    private final AnalyticsRepository analyticsRepository;

    public AnalyticsService(AnalyticsRepository analyticsRepository) {
        this.analyticsRepository = analyticsRepository;
    }

    public List<ProfileDto> getProfiles() {
        return analyticsRepository.findProfiles();
    }

    public ProfileOverviewDto getProfileOverview(String profileId) {
        return analyticsRepository.getProfileOverview(profileId);
    }

    public List<EchoSignalDto> getEchoSignals(String profileId, int limit) {
        return analyticsRepository.getEchoSignals(profileId, limit);
    }

    public List<TemporalDriftDto> getTemporalDrift(String profileId, String granularity, int limit) {
        return analyticsRepository.getTemporalDrift(profileId, granularity, limit);
    }

    public List<TopicExposurePointDto> getTopicTimeseries(String profileId, String granularity) {
        return analyticsRepository.getTopicTimeseries(profileId, granularity);
    }

    public List<ClusterVideoDto> getClusterVideos(String clusterId, int limit) {
        return analyticsRepository.getClusterVideos(clusterId, limit);
    }
}