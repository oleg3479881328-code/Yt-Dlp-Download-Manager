import "./index.css";
import { Composition, CalculateMetadataFunction } from "remotion";
import { KaraokeVideo } from "./KaraokeVideo";
import { DEFAULT_KARAOKE_PROPS } from "./default-props";
import type { Caption } from "@remotion/captions";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const calculateMetadata: CalculateMetadataFunction<any> = async ({
  defaultProps,
}) => {
  const captions = defaultProps.captions as Caption[] | undefined;

  if (captions && captions.length > 0) {
    const maxEndMs = Math.max(...captions.map((c: Caption) => c.endMs));
    const bufferMs = 500;
    const totalMs = maxEndMs + bufferMs;
    const fps = 30;
    const durationInFrames = Math.ceil((totalMs / 1000) * fps);
    return { durationInFrames };
  }

  // Fallback: try to read captions.json for render mode (Node.js)
  try {
    const fs = require("fs");
    const path = require("path");
    const captionsPath = path.join(
      process.cwd(),
      "public",
      "samples",
      "captions.json"
    );
    const raw = fs.readFileSync(captionsPath, "utf-8");
    const parsed: Caption[] = JSON.parse(raw);
    if (parsed.length > 0) {
      const maxEndMs = Math.max(...parsed.map((c: Caption) => c.endMs));
      const bufferMs = 500;
      const totalMs = maxEndMs + bufferMs;
      const fps = 30;
      const durationInFrames = Math.ceil((totalMs / 1000) * fps);
      return { durationInFrames };
    }
  } catch {
    // Fallback for Studio mode (browser) — try fetch
    try {
      const response = await fetch("/samples/captions.json");
      const parsed: Caption[] = await response.json();
      if (parsed.length > 0) {
        const maxEndMs = Math.max(...parsed.map((c: Caption) => c.endMs));
        const bufferMs = 500;
        const totalMs = maxEndMs + bufferMs;
        const fps = 30;
        const durationInFrames = Math.ceil((totalMs / 1000) * fps);
        return { durationInFrames };
      }
    } catch {
      // Final fallback: 240 frames (8 seconds)
      return { durationInFrames: 240 };
    }
  }

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
