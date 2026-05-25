import type { TikTokPage } from "@remotion/captions";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { KARAOKE_PRESET_V1 } from "./KaraokePresetV1";

export const CaptionPage: React.FC<{ page: TikTokPage }> = ({ page }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const absoluteTimeMs = page.startMs + (frame / fps) * 1000;

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: KARAOKE_PRESET_V1.safeBottom,
        paddingLeft: 56,
        paddingRight: 56,
      }}
    >
      <div
        style={{
          maxWidth: KARAOKE_PRESET_V1.maxWidth,
          width: "100%",
          textAlign: "center",
          background: KARAOKE_PRESET_V1.panelBackground,
          border: KARAOKE_PRESET_V1.panelBorder,
          borderRadius: KARAOKE_PRESET_V1.borderRadius,
          padding: `${KARAOKE_PRESET_V1.paddingY}px ${KARAOKE_PRESET_V1.paddingX}px`,
          boxShadow: KARAOKE_PRESET_V1.boxShadow,
          backdropFilter: "blur(12px)",
          whiteSpace: "pre-wrap",
        }}
      >
        {page.tokens.map((token) => {
          const isActive = token.fromMs <= absoluteTimeMs && token.toMs > absoluteTimeMs;
          const tokenStartFrame = ((token.fromMs - page.startMs) / 1000) * fps;
          const pulse = spring({
            frame: frame - tokenStartFrame,
            fps,
            config: {
              damping: 16,
              stiffness: 220,
              mass: 0.55,
            },
          });
          const inactiveScale = interpolate(pulse, [0, 1], [1, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const activeScale = interpolate(pulse, [0, 1], [0.92, 1.08], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          return (
            <span
              key={`${token.fromMs}-${token.toMs}-${token.text}`}
              style={{
                display: "inline-block",
                fontSize: KARAOKE_PRESET_V1.fontSize,
                lineHeight: KARAOKE_PRESET_V1.lineHeight,
                fontWeight: KARAOKE_PRESET_V1.fontWeight,
                letterSpacing: KARAOKE_PRESET_V1.letterSpacing,
                color: isActive
                  ? KARAOKE_PRESET_V1.activeColor
                  : KARAOKE_PRESET_V1.inactiveColor,
                background: isActive ? KARAOKE_PRESET_V1.activeFill : "transparent",
                borderRadius: 18,
                padding: isActive ? "0.02em 0.16em" : "0.02em 0",
                transform: `scale(${isActive ? activeScale : inactiveScale})`,
                textShadow: KARAOKE_PRESET_V1.textShadow,
                WebkitTextStroke: `${KARAOKE_PRESET_V1.strokeWidth} ${KARAOKE_PRESET_V1.strokeColor}`,
              }}
            >
              {token.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
