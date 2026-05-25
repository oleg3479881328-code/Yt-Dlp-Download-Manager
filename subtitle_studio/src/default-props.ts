import type { KaraokeVideoProps } from "./types";

export const DEFAULT_KARAOKE_PROPS: KaraokeVideoProps = {
  videoSrc: "local-assets/validation-input.mp4",
  captionsSrc: "samples/captions.json",
  title: "KaraokePresetV1 Preview",
  combineTokensWithinMilliseconds: 1100,
};
