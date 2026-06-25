export type Point = {
  x: number;
  y: number;
};

type BaseElement = {
  id: string;
  startSec: number;
  durationSec: number;
  stroke?: string;
  strokeWidth?: number;
  roughness?: number;
  opacity?: number;
};

export type LineElement = BaseElement & {
  type: "line" | "arrow";
  from: Point;
  to: Point;
};

export type CircleElement = BaseElement & {
  type: "circle";
  center: Point;
  radius: number;
  fill?: string;
};

export type WaveElement = BaseElement & {
  type: "wave";
  points: Point[];
};

export type DotsElement = BaseElement & {
  type: "dots";
  points: Point[];
  radius: number;
  fill?: string;
};

export type TextElement = BaseElement & {
  type: "text";
  text: string;
  position: Point;
  fontSize: number;
  color?: string;
  maxWidth?: number;
  align?: "left" | "center" | "right";
};

export type StrokePathStep = {
  id: string;
  d: string;
  startOffsetSec?: number;
  durationSec?: number;
  stroke?: string;
  strokeWidth?: number;
  opacity?: number;
};

export type StrokePathElement = BaseElement & {
  type: "strokePath";
  d: string;
};

export type PathGroupElement = BaseElement & {
  type: "pathGroup";
  paths: StrokePathStep[];
};

export type SceneElement =
  | LineElement
  | CircleElement
  | WaveElement
  | DotsElement
  | TextElement
  | StrokePathElement
  | PathGroupElement;

export type SceneSpec = {
  id: string;
  title: string;
  durationSec: number;
  caption: string;
  background?: string;
  accent?: string;
  elements: SceneElement[];
};

export type SceneSpecFile = {
  meta: {
    title: string;
    fps: number;
    width: number;
    height: number;
  };
  scenes: SceneSpec[];
};

export type WhiteboardVideoProps = {
  specSrc: string;
  title: string;
};
