import "./index.css";
import { Composition, staticFile, type CalculateMetadataFunction } from "remotion";
import { WhiteboardVideo } from "./WhiteboardVideo";
import { DEFAULT_WHITEBOARD_PROPS, HORSE_WHITEBOARD_PROPS } from "./default-props";
import { getTotalDurationInFrames } from "./scene-loader";
import type { SceneSpecFile, WhiteboardVideoProps } from "./sceneTypes";

const COMPOSITION_FPS = 30;
const FALLBACK_DURATION = COMPOSITION_FPS * 30;

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
    return { durationInFrames: getTotalDurationInFrames(payload, COMPOSITION_FPS) };
  } catch {
    return { durationInFrames: FALLBACK_DURATION };
  }
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="WhiteboardVideo"
        component={WhiteboardVideo}
        defaultProps={DEFAULT_WHITEBOARD_PROPS}
        calculateMetadata={calculateMetadata}
        fps={COMPOSITION_FPS}
        width={1080}
        height={1920}
      />
      <Composition
        id="PencilHorseVideo"
        component={WhiteboardVideo}
        defaultProps={HORSE_WHITEBOARD_PROPS}
        calculateMetadata={calculateMetadata}
        fps={COMPOSITION_FPS}
        width={1080}
        height={1920}
      />
    </>
  );
};
