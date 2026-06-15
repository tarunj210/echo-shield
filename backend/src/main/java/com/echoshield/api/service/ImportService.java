package com.echoshield.api.service;

import com.echoshield.api.dto.ImportJobResponse;
import com.echoshield.api.dto.ImportJobStatusDto;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

@Service
public class ImportService {

    private final JdbcTemplate jdbcTemplate;

    @Value("${echoshield.uploads-dir:uploads/imports}")
    private String uploadsDir;

    @Value("${echoshield.pipeline-script:../scripts/run_profile_pipeline.sh}")
    private String pipelineScript;

    public ImportService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public ImportJobResponse createWatchHistoryImport(MultipartFile file, String displayName) {
        validateFile(file);

        UUID importJobId = UUID.randomUUID();
        String profileId = "profile_" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);

        String originalFilename = StringUtils.cleanPath(
            file.getOriginalFilename() == null ? "watch-history.html" : file.getOriginalFilename()
        );

        try {
            Path importDir = Path.of(uploadsDir, importJobId.toString()).toAbsolutePath().normalize();
            Files.createDirectories(importDir);

            Path storedFile = importDir.resolve(originalFilename).normalize();
            file.transferTo(storedFile.toFile());

            createProfile(profileId, displayName);
            createImportJob(importJobId, profileId, originalFilename, storedFile);

            startPipelineInBackground(importJobId, profileId, storedFile, importDir);

            return new ImportJobResponse(
                importJobId.toString(),
                profileId,
                "PROCESSING"
            );

        } catch (Exception exception) {
            throw new RuntimeException("Failed to create watch-history import.", exception);
        }
    }

    public ImportJobStatusDto getImportJobStatus(UUID importJobId) {
        String sql = """
            SELECT
                import_job_id,
                profile_id,
                source,
                status,
                original_filename,
                total_events,
                inserted_events,
                error_message,
                created_at,
                started_at,
                completed_at
            FROM import_jobs
            WHERE import_job_id = ?
        """;

        return jdbcTemplate.queryForObject(
            sql,
            (rs, rowNum) -> new ImportJobStatusDto(
                rs.getObject("import_job_id", UUID.class).toString(),
                rs.getString("profile_id"),
                rs.getString("source"),
                rs.getString("status"),
                rs.getString("original_filename"),
                rs.getObject("total_events", Integer.class),
                rs.getObject("inserted_events", Integer.class),
                rs.getString("error_message"),
                toLocalDateTime(rs.getTimestamp("created_at")),
                toLocalDateTime(rs.getTimestamp("started_at")),
                toLocalDateTime(rs.getTimestamp("completed_at"))
            ),
            importJobId
        );
    }

    private LocalDateTime toLocalDateTime(java.sql.Timestamp timestamp) {
        return timestamp == null ? null : timestamp.toLocalDateTime();
    }

    private void validateFile(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new IllegalArgumentException("Uploaded file is empty.");
        }

        String filename = file.getOriginalFilename();

        if (filename == null) {
            throw new IllegalArgumentException("Uploaded file must have a filename.");
        }

        String lower = filename.toLowerCase(Locale.ROOT);

        if (!lower.endsWith(".html") && !lower.endsWith(".json")) {
            throw new IllegalArgumentException("Only Google Takeout .html or .json watch-history files are supported.");
        }
    }

    private void createProfile(String profileId, String displayName) {
        String resolvedDisplayName =
            displayName == null || displayName.isBlank()
                ? "Uploaded profile"
                : displayName.trim();

        String sql = """
            INSERT INTO profiles (
                profile_id,
                display_name,
                profile_type,
                tenant_id,
                created_at
            )
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (profile_id)
            DO NOTHING
        """;

        jdbcTemplate.update(
            sql,
            profileId,
            resolvedDisplayName,
            "uploaded_google_takeout",
            "default_tenant"
        );
    }

    private void createImportJob(
        UUID importJobId,
        String profileId,
        String originalFilename,
        Path storedFile
    ) {
        String sql = """
            INSERT INTO import_jobs (
                import_job_id,
                profile_id,
                source,
                status,
                original_filename,
                stored_file_path,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """;

        jdbcTemplate.update(
            sql,
            importJobId,
            profileId,
            "google_takeout_youtube_watch_history",
            "PROCESSING",
            originalFilename,
            storedFile.toString()
        );
    }

    private void startPipelineInBackground(
        UUID importJobId,
        String profileId,
        Path storedFile,
        Path importDir
    ) {
        CompletableFuture.runAsync(() -> {
            try {
                markStarted(importJobId);

                Path logFile = importDir.resolve("pipeline.log");
                Path scriptPath = Path.of(pipelineScript).toAbsolutePath().normalize();

                ProcessBuilder processBuilder = new ProcessBuilder(
                    "/bin/bash",
                    scriptPath.toString(),
                    importJobId.toString(),
                    profileId,
                    storedFile.toAbsolutePath().toString()
                );

                processBuilder.redirectErrorStream(true);
                processBuilder.redirectOutput(ProcessBuilder.Redirect.appendTo(logFile.toFile()));

                Process process = processBuilder.start();
                int exitCode = process.waitFor();

                if (exitCode == 0) {
                    markCompleted(importJobId);
                } else {
                    markFailed(importJobId, "Pipeline failed with exit code " + exitCode + ". Check " + logFile);
                }

            } catch (Exception exception) {
                markFailed(importJobId, exception.getMessage());
            }
        });
    }

    private void markStarted(UUID importJobId) {
        String sql = """
            UPDATE import_jobs
            SET status = 'PROCESSING',
                started_at = CURRENT_TIMESTAMP
            WHERE import_job_id = ?
        """;

        jdbcTemplate.update(sql, importJobId);
    }

    private void markCompleted(UUID importJobId) {
        String sql = """
            UPDATE import_jobs
            SET status = 'COMPLETED',
                completed_at = CURRENT_TIMESTAMP,
                error_message = NULL
            WHERE import_job_id = ?
        """;

        jdbcTemplate.update(sql, importJobId);
    }

    private void markFailed(UUID importJobId, String errorMessage) {
        String sql = """
            UPDATE import_jobs
            SET status = 'FAILED',
                completed_at = CURRENT_TIMESTAMP,
                error_message = ?
            WHERE import_job_id = ?
        """;

        jdbcTemplate.update(sql, errorMessage, importJobId);
    }
}