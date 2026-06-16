import { useState } from "react";
import { Upload, Loader2, CheckCircle2, AlertTriangle } from "lucide-react";
import {
  getImportJobStatus,
  uploadWatchHistory,
  type ImportJobStatus,
} from "@/lib/echo/client";

type Props = {
  onProfileReady: (profileId: string) => void;
};

export function WatchHistoryUpload({ onProfileReady }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [status, setStatus] = useState<ImportJobStatus | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pollImport(importJobId: string) {
    const intervalId = window.setInterval(async () => {
      try {
        const nextStatus = await getImportJobStatus(importJobId);
        setStatus(nextStatus);

        if (nextStatus.status === "COMPLETED") {
          window.clearInterval(intervalId);
          localStorage.setItem("echoshield_profile_id", nextStatus.profileId);
          onProfileReady(nextStatus.profileId);
        }

        if (nextStatus.status === "FAILED") {
          window.clearInterval(intervalId);
          setError(nextStatus.errorMessage ?? "Import failed.");
        }
      } catch (err) {
        window.clearInterval(intervalId);
        setError(err instanceof Error ? err.message : "Failed to poll import status.");
      }
    }, 3000);
  }

  async function handleUpload() {
    if (!file) {
      setError("Please choose a Google Takeout watch-history HTML or JSON file.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadWatchHistory(file, displayName || undefined);

      setStatus({
        importJobId: response.importJobId,
        profileId: response.profileId,
        source: "google_takeout_youtube_watch_history",
        status: "PROCESSING",
        originalFilename: file.name,
        totalEvents: 0,
        insertedEvents: 0,
        errorMessage: null,
        createdAt: new Date().toISOString(),
        startedAt: null,
        completedAt: null,
      });

      await pollImport(response.importJobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <section className="panel p-6">
      <div className="mb-5">
        <p className="eyebrow">New profile</p>
        <h2 className="text-2xl font-semibold text-foreground">
          Upload YouTube watch history
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Upload a Google Takeout YouTube watch-history HTML or JSON file to create
          a pseudonymised profile and generate exposure analytics.
        </p>
      </div>

      <div className="grid gap-4">
        <label className="grid gap-2">
          <span className="text-sm text-muted-foreground">Display name</span>
          <input
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Demo User"
            className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none"
          />
        </label>

        <label className="grid gap-2">
          <span className="text-sm text-muted-foreground">
            Google Takeout watch-history file
          </span>
          <input
            type="file"
            accept=".html,.json"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground"
          />
        </label>

        <button
        onClick={handleUpload}
        disabled={isUploading}
        className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isUploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          Upload and analyse
        </button>

        {status && (
          <div className="rounded-md border border-border bg-muted/40 p-4 text-sm">
            <div className="flex items-center gap-2">
              {status.status === "COMPLETED" ? (
                <CheckCircle2 className="h-4 w-4 text-sev-low" />
              ) : status.status === "FAILED" ? (
                <AlertTriangle className="h-4 w-4 text-sev-high" />
              ) : (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              )}
              <span className="font-medium text-foreground">
                Import status: {status.status}
              </span>
            </div>

            <p className="mt-2 text-muted-foreground">
              Profile: <span className="font-mono">{status.profileId}</span>
            </p>
          </div>
        )}

        {error && (
          <div className="rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}
      </div>
    </section>
  );
}