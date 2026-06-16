package com.echoshield.api.controller;

import com.echoshield.api.dto.ImportJobResponse;
import com.echoshield.api.dto.ImportJobStatusDto;
import com.echoshield.api.service.ImportService;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.UUID;

@RestController
@RequestMapping("/api/imports")
public class ImportController {

    private final ImportService importService;

    public ImportController(ImportService importService) {
        this.importService = importService;
    }

    @PostMapping("/youtube-watch-history")
    public ImportJobResponse uploadWatchHistory(
        @RequestParam("file") MultipartFile file,
        @RequestParam(value = "displayName", required = false) String displayName
    ) {
        return importService.createWatchHistoryImport(file, displayName);
    }

    @GetMapping("/{importJobId}")
    public ImportJobStatusDto getImportJobStatus(@PathVariable UUID importJobId) {
        return importService.getImportJobStatus(importJobId);
    }
}