import { staticFile, useDelayRender } from "remotion";
import type { Caption } from "@remotion/captions";
import { useCallback, useEffect, useMemo, useState } from "react";

const isCaption = (value: unknown): value is Caption => {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.text === "string" &&
    typeof candidate.startMs === "number" &&
    typeof candidate.endMs === "number" &&
    typeof candidate.timestampMs === "number" &&
    (candidate.confidence === null || typeof candidate.confidence === "number")
  );
};

export const useCaptionSource = (captionsSrc: string): Caption[] => {
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  const [handle] = useState(() => delayRender(`load-captions:${captionsSrc}`));

  const fetchCaptions = useCallback(async () => {
    try {
      const response = await fetch(staticFile(captionsSrc));
      if (!response.ok) {
        throw new Error(`Failed to load captions: ${captionsSrc}`);
      }

      const payload = (await response.json()) as unknown;
      if (!Array.isArray(payload) || payload.some((item) => !isCaption(item))) {
        throw new Error("Captions JSON must be an array of Remotion Caption objects");
      }

      setCaptions(payload);
      continueRender(handle);
    } catch (error) {
      cancelRender(error);
    }
  }, [cancelRender, captionsSrc, continueRender, handle]);

  useEffect(() => {
    fetchCaptions();
  }, [fetchCaptions]);

  return useMemo(() => captions ?? [], [captions]);
};
