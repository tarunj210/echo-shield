import type { TrajectoryTimelineItem } from "@/lib/echo/types";

type Props = {
  items: TrajectoryTimelineItem[];
};

export function SessionTimeline({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No videos found in this session.
      </p>
    );
  }

  return (
    <div className="max-h-[620px] space-y-3 overflow-y-auto pr-1">
      {items.map((item, index) => {
        const isFinal = index === items.length - 1;

        return (
          <div
            key={item.eventId}
            className={`rounded-lg border p-3 ${
              isFinal
                ? "border-yellow-400/60 bg-yellow-400/10"
                : "border-border bg-surface-1"
            }`}
          >
            <div className="flex items-start gap-3">
              {item.thumbnailUrl ? (
                <img
                  src={item.thumbnailUrl}
                  alt=""
                  className="h-14 w-20 rounded-md object-cover"
                />
              ) : (
                <div className="h-14 w-20 rounded-md bg-surface-2" />
              )}

              <div className="min-w-0 flex-1">
                <div className="line-clamp-2 text-sm text-foreground">
                  {item.sequenceIndex}. {item.title}
                </div>

                <div className="mt-1 truncate text-xs text-muted-foreground">
                  {item.channelTitle}
                </div>

                <div className="mt-1 flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                  <span>{formatTime(item.watchedAt)}</span>

                  {item.minutesSincePrevious != null && (
                    <span>+{item.minutesSincePrevious}m</span>
                  )}

                  {isFinal && (
                    <span className="rounded-full bg-yellow-400/15 px-2 py-0.5 text-yellow-300">
                      current
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString("en-AU", {
    hour: "numeric",
    minute: "2-digit",
  });
}