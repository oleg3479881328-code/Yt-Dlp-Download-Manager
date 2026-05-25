import "./index.css";
import { Composition } from "remotion";
import { KaraokeVideo } from "./KaraokeVideo";
import { DEFAULT_KARAOKE_PROPS } from "./default-props";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="KaraokeVideo"
        component={KaraokeVideo}
        defaultProps={DEFAULT_KARAOKE_PROPS}
        durationInFrames={240}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
