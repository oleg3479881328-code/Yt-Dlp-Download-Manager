import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { SketchElement } from "./renderers/SketchElement";
import type { SceneSpec } from "./sceneTypes";

export const WhiteboardScene: React.FC<{ scene: SceneSpec }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const headerProgress = spring({
    fps,
    frame,
    config: {
      damping: 200,
      stiffness: 120,
      mass: 0.8,
    },
  });

  return (
    <AbsoluteFill
      style={{
        background:
          scene.background ??
          "radial-gradient(circle at top, #fffdf8 0%, #f8ecd7 60%, #efdebf 100%)",
      }}
    >
      <AbsoluteFill
        style={{
          padding: "96px 72px 120px",
        }}
      >
        <div
          style={{
            width: 420,
            padding: "20px 28px",
            borderRadius: 28,
            background: "rgba(255, 251, 240, 0.86)",
            boxShadow: "0 20px 45px rgba(122, 95, 42, 0.15)",
            border: "2px solid rgba(58, 77, 92, 0.12)",
            transform: `translateY(${24 * (1 - headerProgress)}px) rotate(${(1 - headerProgress) * -1.6}deg)`,
            opacity: headerProgress,
          }}
        >
          <div
            style={{
              fontSize: 48,
              fontWeight: 800,
              lineHeight: 1.05,
              color: "#243441",
              fontFamily: '"Comic Sans MS", "Trebuchet MS", sans-serif',
            }}
          >
            {scene.title}
          </div>
        </div>

        <div
          style={{
            marginTop: 42,
            flex: 1,
            borderRadius: 54,
            background:
              "linear-gradient(180deg, rgba(255,255,255,0.55) 0%, rgba(255,250,241,0.82) 100%)",
            border: "2px solid rgba(31, 46, 57, 0.08)",
            position: "relative",
            overflow: "hidden",
            boxShadow: "inset 0 1px 0 rgba(255,255,255,0.8), 0 25px 60px rgba(72, 58, 31, 0.12)",
          }}
        >
          <svg viewBox="0 0 1080 1500" style={{ width: "100%", height: "100%" }}>
            <rect width="1080" height="1500" fill="transparent" />
            {scene.elements.map((element) => (
              <SketchElement key={element.id} element={element} />
            ))}
          </svg>
        </div>

        <div
          style={{
            marginTop: 32,
            alignSelf: "center",
            maxWidth: 760,
            padding: "22px 30px",
            borderRadius: 30,
            background: "rgba(255, 255, 255, 0.74)",
            color: "#2d4150",
            fontSize: 34,
            fontWeight: 700,
            lineHeight: 1.2,
            textAlign: "center",
            boxShadow: "0 18px 36px rgba(72, 58, 31, 0.12)",
          }}
        >
          {scene.caption}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
