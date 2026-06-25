import "./index.css";
import { Composition, staticFile, type CalculateMetadataFunction } from "remotion";
import { WhiteboardVideo } from "./WhiteboardVideo";
import { DEFAULT_WHITEBOARD_PROPS } from "./default-props";
import { getTotalDurationInFrames } from "./scene-loader";
import type { SceneSpecFile, WhiteboardVideoProps } from "./sceneTypes";

const FALLBACK_DURATION = 30 * 30;

const calculateMetadata: CalculateMetadataFunction<WhiteboardVideoProps> = async ({
  defaultProps,
}) => {
  const props = defaultProps as WhiteboardVideoProps;

  try {
    const response = await fetch(staticFile(props.specSrc));
    if (!response.ok) {
      return { durationInFrames: FALLBACK_DURATION };
    }

    const payload = (await response.json()) as SceneSpecFile;
    const fps = payload.meta?.fps ?? 30;
    return { durationInFrames: getTotalDurationInFrames(payload, fps) };
  } catch {
    return { durationInFrames: FALLBACK_DURATION };
  }
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="WhiteboardVideo"
      component={WhiteboardVideo}
      defaultProps={DEFAULT_WHITEBOARD_PROPS}
      calculateMetadata={calculateMetadata}
      fps={30}
      width={1080}
      height={1920}
    />
  );
};
