import type { Caption } from "@remotion/captions";

export type CaptionSource = Caption[];

export type KaraokeVideoProps = {
  videoSrc: string;
  captionsSrc: string;
  title?: string;
  combineTokensWithinMilliseconds?: number;
};
