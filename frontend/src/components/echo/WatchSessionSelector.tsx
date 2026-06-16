import type { WatchSession } from "@/lib/echo/types";

type Props = {
  sessions: WatchSession[];
  selectedSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
};

export function WatchSessionSelector({
  sessions,
  selectedSessionId,
  onSelectSession,
}: Props) {
  if (sessions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No sessions found for this profile.
      </p>
    );
  }

  return (
    <div className="max-h-[620px] space-y-2 overflow-y-auto pr-1">
      {sessions.map((session) => {
        const selected = session.sessionId === selectedSessionId;

        return (
          <button
            key={session.sessionId}
            onClick={() => onSelectSession(session.sessionId)}
            className={`w-full rounded-lg border px-3 py-3 text-left transition ${
              selected
                ? "border-primary/60 bg-primary/10 text-foreground"
                : "border-border bg-surface-1 text-muted-foreground hover:bg-surface-2 hover:text-foreground"
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="font-mono text-xs">
                {formatDateTime(session.sessionStart)}
              </div>

              <div className="font-mono text-[11px] text-muted-foreground">
                {session.totalDurationMinutes} min
              </div>
            </div>

            <div className="mt-1 text-sm text-foreground">
              {session.videoCount} videos · {session.uniqueChannelCount} channels
            </div>

            <div className="mt-1 truncate text-xs text-muted-foreground">
              Dominant: {session.dominantChannelTitle ?? "Unknown Channel"}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("en-AU", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}