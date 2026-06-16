package com.echoshield.api.controller;

import com.echoshield.api.dto.ClusterVideoDto;
import com.echoshield.api.service.AnalyticsService;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/clusters")
public class ClusterController {

    private final AnalyticsService analyticsService;

    public ClusterController(AnalyticsService analyticsService) {
        this.analyticsService = analyticsService;
    }

    @GetMapping("/{clusterId}/videos")
    public List<ClusterVideoDto> getClusterVideos(
        @PathVariable String clusterId,
        @RequestParam(defaultValue = "25") int limit
    ) {
        return analyticsService.getClusterVideos(clusterId, limit);
    }
}