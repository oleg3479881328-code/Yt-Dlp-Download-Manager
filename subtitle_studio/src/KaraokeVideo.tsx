import { createTikTokStyleCaptions } from "@remotion/captions";
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  staticFile,
  useVideoConfig,
} from "remotion";
import { useMemo } from "react";
import { CaptionPage } from "./CaptionPage";
import { KARAOKE_PRESET_V1 } from "./KaraokePresetV1";
import { useCaptionSource } from "./caption-loader";
import type { KaraokeVideoProps } from "./types";

export const KaraokeVideo: React.FC<KaraokeVideoProps> = ({
  videoSrc,
  captionsSrc,
  combineTokensWithinMilliseconds = KARAOKE_PRESET_V1.pageSwitchMs,
}) => {
  const { fps } = useVideoConfig();
  const captions = useCaptionSource(captionsSrc);

  const { pages } = useMemo(() => {
    return createTikTokStyleCaptions({
      captions,
      combineTokensWithinMilliseconds,
    });
  }, [captions, combineTokensWithinMilliseconds]);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#050816",
      }}
    >
      <AbsoluteFill
        style={{
          padding: "84px 54px 224px",
        }}
      >
        <OffthreadVideo
          src={staticFile(videoSrc)}
          delayRenderTimeoutInMilliseconds={120000}
          delayRenderRetries={5}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            borderRadius: 42,
            boxShadow: "0 30px 90px rgba(0, 0, 0, 0.42)",
            backgroundColor: "rgba(2, 6, 18, 0.8)",
          }}
        />
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          background: KARAOKE_PRESET_V1.overlayGradient,
        }}
      />

      {pages.map((page, index) => {
        const nextPage = pages[index + 1] ?? null;
        const startFrame = Math.floor((page.startMs / 1000) * fps);
        const endFrame = Math.ceil(
          nextPage
            ? (nextPage.startMs / 1000) * fps
            : ((page.startMs + page.durationMs) / 1000) * fps,
        );
        const durationInFrames = Math.max(1, endFrame - startFrame);

        return (
          <Sequence key={`${page.startMs}-${page.text}`} from={startFrame} durationInFrames={durationInFrames}>
            <CaptionPage page={page} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
