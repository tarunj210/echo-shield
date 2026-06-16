package com.echoshield.api.service;

import com.echoshield.api.dto.EmbeddingProgressDto;
import com.echoshield.api.repository.AnalyticsRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.util.Arrays;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class EmbeddingWorkerService {
    private static final Logger log =
        LoggerFactory.getLogger(EmbeddingWorkerService.class);

    private final AnalyticsRepository analyticsRepository;

    private final Set<UUID> locallyRunningJobs = ConcurrentHashMap.newKeySet();

    @Value("${echoshield.embedding.python-executable}")
    private String pythonExecutable;

    @Value("${echoshield.embedding.pipeline-dir}")
    private String pipelineDir;

    @Value("${echoshield.embedding.batch-size:64}")
    private int defaultBatchSize;

    public EmbeddingWorkerService(AnalyticsRepository analyticsRepository) {
        this.analyticsRepository = analyticsRepository;
    }

    public EmbeddingProgressDto startEmbeddingJob(String profileId) {
        if (analyticsRepository.hasActiveEmbeddingJob(profileId)) {
            log.info("Embedding or enrichment job already active for profile {}", profileId);
            return analyticsRepository.getEmbeddingProgress(profileId);
        }

        UUID embeddingJobId =
            analyticsRepository.createEmbeddingJob(profileId, defaultBatchSize);

        if (embeddingJobId == null) {
            throw new IllegalStateException(
                "Failed to create embedding job for profile " + profileId
            );
        }

        runWorkerAsync(profileId, embeddingJobId, defaultBatchSize);

        return analyticsRepository.getEmbeddingProgress(profileId);
    }

    private void runWorkerAsync(
        String profileId,
        UUID embeddingJobId,
        int batchSize
    ) {
        if (!locallyRunningJobs.add(embeddingJobId)) {
            log.info("Embedding job {} is already running locally", embeddingJobId);
            return;
        }

        CompletableFuture.runAsync(() -> {
            try {
                log.info(
                    "Starting embedding worker. profileId={}, embeddingJobId={}, batchSize={}",
                    profileId,
                    embeddingJobId,
                    batchSize
                );

                int embeddingExitCode = runPipelineCommand(
                    "generate_video_embeddings",
                    pythonExecutable,
                    "generate_video_embeddings.py",
                    "--profile-id", profileId,
                    "--embedding-job-id", embeddingJobId.toString(),
                    "--batch-size", String.valueOf(batchSize)
                );

                if (embeddingExitCode != 0) {
                    analyticsRepository.updateEmbeddingJobStatus(
                        embeddingJobId,
                        "FAILED",
                        "Embedding worker failed with exit code " + embeddingExitCode
                    );
                    return;
                }

                analyticsRepository.updateEmbeddingJobStatus(
                    embeddingJobId,
                    "ENRICHING",
                    null
                );

                runSemanticEnrichment(profileId);

                analyticsRepository.updateEmbeddingJobStatus(
                    embeddingJobId,
                    "COMPLETED",
                    null
                );

                log.info(
                    "Embedding and semantic enrichment completed. profileId={}, embeddingJobId={}",
                    profileId,
                    embeddingJobId
                );
            } catch (Exception error) {
                log.error(
                    "Embedding/enrichment pipeline failed. embeddingJobId={}",
                    embeddingJobId,
                    error
                );

                analyticsRepository.updateEmbeddingJobStatus(
                    embeddingJobId,
                    "FAILED",
                    error.getMessage()
                );
            } finally {
                locallyRunningJobs.remove(embeddingJobId);
            }
        });
    }

    private void runSemanticEnrichment(String profileId) throws Exception {
        runPipelineCommand(
            "build_similarity_edges",
            pythonExecutable,
            "build_similarity_edges.py"
        );

        runPipelineCommand(
            "discover_semantic_clusters",
            pythonExecutable,
            "discover_semantic_clusters.py"
        );

        runPipelineCommand(
            "label_clusters_keybert",
            pythonExecutable,
            "label_clusters_keybert.py"
        );

        runPipelineCommand(
            "dynamic_refine_cluster_labels",
            pythonExecutable,
            "dynamic_refine_cluster_labels.py",
            "--taxonomy", "../config/topic_taxonomy.yml",
            "--threshold", "0.17",
            "--min-margin", "0.02"
        );

        runPipelineCommand(
            "map_clusters_to_taxonomy",
            pythonExecutable,
            "map_clusters_to_taxonomy.py"
        );

        runPipelineCommand(
            "calculate_echo_chamber_scores",
            pythonExecutable,
            "calculate_echo_chamber_scores.py",
            "--profile-id", profileId,
            "--window-days", "365",
            "--min-watch-count", "5",
            "--min-score", "15"
        );

        runPipelineCommand(
            "calculate_temporal_drift_weekly",
            pythonExecutable,
            "calculate_temporal_drift.py",
            "--profile-id", profileId,
            "--granularity", "weekly",
            "--periods", "12"
        );

        runPipelineCommand(
            "calculate_temporal_drift_monthly",
            pythonExecutable,
            "calculate_temporal_drift.py",
            "--profile-id", profileId,
            "--granularity", "monthly",
            "--periods", "6"
        );
    }

    private int runPipelineCommand(String stepName, String... command)
        throws Exception {
        log.info("Starting pipeline step: {}", stepName);
        log.info("Command: {}", Arrays.toString(command));
        log.info("Working directory: {}", pipelineDir);

        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.directory(new File(pipelineDir));
        processBuilder.redirectErrorStream(true);

        Process process = processBuilder.start();

        try (BufferedReader reader = new BufferedReader(
            new InputStreamReader(process.getInputStream())
        )) {
            String line;

            while ((line = reader.readLine()) != null) {
                log.info("[{}] {}", stepName, line);
            }
        }

        int exitCode = process.waitFor();

        if (exitCode != 0) {
            throw new IllegalStateException(
                "Pipeline step failed: " + stepName + ", exitCode=" + exitCode
            );
        }

        log.info("Completed pipeline step: {}", stepName);

        return exitCode;
    }
}