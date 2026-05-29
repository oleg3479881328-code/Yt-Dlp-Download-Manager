import "./index.css";
import { Composition, CalculateMetadataFunction, staticFile } from "remotion";
import { KaraokeVideo } from "./KaraokeVideo";
import { DEFAULT_KARAOKE_PROPS } from "./default-props";
import type { Caption } from "@remotion/captions";
import type { KaraokeVideoProps } from "./types";

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

const computeDurationFromCaptions = (captions: Caption[]): number => {
  if (captions.length === 0) return 240;
  const maxEndMs = Math.max(...captions.map((c: Caption) => c.endMs));
  const bufferMs = 500;
  const totalMs = maxEndMs + bufferMs;
  const fps = 30;
  return Math.ceil((totalMs / 1000) * fps);
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const calculateMetadata: CalculateMetadataFunction<any> = async ({
  defaultProps,
}) => {
  // 1. Check if captions array was passed directly (via --props with captions field)
  const directCaptions = defaultProps.captions as Caption[] | undefined;
  if (directCaptions && directCaptions.length > 0) {
    return { durationInFrames: computeDurationFromCaptions(directCaptions) };
  }

  // 2. Try to load via captionsSrc using staticFile + fetch
  //    In render mode, Remotion downloads public/ files and serves them via staticFile()
  const props = defaultProps as KaraokeVideoProps;
  if (props.captionsSrc) {
    try {
      const url = staticFile(props.captionsSrc);
      const response = await fetch(url);
      if (response.ok) {
        const payload = (await response.json()) as unknown;
        if (Array.isArray(payload) && payload.length > 0 && payload.some((item) => isCaption(item))) {
          return { durationInFrames: computeDurationFromCaptions(payload as Caption[]) };
        }
      }
    } catch {
      // fetch failed, continue to fallback
    }
  }

  // 3. Final fallback: 240 frames (8 seconds)
  return { durationInFrames: 240 };
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="KaraokeVideo"
        component={KaraokeVideo}
        defaultProps={DEFAULT_KARAOKE_PROPS}
        calculateMetadata={calculateMetadata}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
