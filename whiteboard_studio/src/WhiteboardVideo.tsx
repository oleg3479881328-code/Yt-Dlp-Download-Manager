import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { useMemo } from "react";
import { useSceneSpec } from "./scene-loader";
import { WhiteboardScene } from "./WhiteboardScene";
import type { WhiteboardVideoProps } from "./sceneTypes";

export const WhiteboardVideo: React.FC<WhiteboardVideoProps> = ({ specSrc }) => {
  const spec = useSceneSpec(specSrc);
  const { fps } = useVideoConfig();

  const scenesWithFrames = useMemo(() => {
    let cursor = 0;
    return spec.scenes.map((scene) => {
      const durationInFrames = Math.max(1, Math.round(scene.durationSec * fps));
      const item = {
        scene,
        from: cursor,
        durationInFrames,
      };
      cursor += durationInFrames;
      return item;
    });
  }, [fps, spec.scenes]);

  return (
    <AbsoluteFill
      style={{
        background: "linear-gradient(180deg, #fff9ec 0%, #f1e3cb 100%)",
      }}
    >
      {scenesWithFrames.map(({ scene, from, durationInFrames }) => (
        <Sequence key={scene.id} from={from} durationInFrames={durationInFrames}>
          <WhiteboardScene scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
