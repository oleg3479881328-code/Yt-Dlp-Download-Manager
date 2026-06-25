import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import rough from "roughjs/bin/rough";
import type { Drawable, OpSet } from "roughjs/bin/core";
import type {
  CircleElement,
  DotsElement,
  LineElement,
  SceneElement,
  TextElement,
  WaveElement,
} from "../sceneTypes";

const roughGenerator = rough.generator();
const DASH_LENGTH = 2400;

const getDrawableStrokeWidth = (drawable: Drawable) => {
  return drawable.options.strokeWidth ?? 2.2;
};

const getDrawableFillWeight = (drawable: Drawable) => {
  const fillWeight = drawable.options.fillWeight;
  if (typeof fillWeight === "number" && fillWeight >= 0) {
    return fillWeight;
  }

  return (drawable.options.strokeWidth ?? 2.2) / 2;
};

const getReveal = (startFrame: number, endFrame: number, frame: number) => {
  return interpolate(frame, [startFrame, endFrame], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
};

const getPathStyle = (set: OpSet, drawable: Drawable, fallbackStroke: string) => {
  const stroke = drawable.options.stroke ?? fallbackStroke;
  const fill = drawable.options.fill ?? "none";

  if (set.type === "fillPath") {
    return {
      d: roughGenerator.opsToPath(set),
      stroke: "none",
      fill,
      strokeWidth: 0,
      opacity: 1,
      strokeLinecap: "round" as const,
      strokeLinejoin: "round" as const,
    };
  }

  if (set.type === "fillSketch") {
    return {
      d: roughGenerator.opsToPath(set),
      stroke: fill,
      fill: "none",
      strokeWidth: getDrawableFillWeight(drawable),
      opacity: 1,
      strokeLinecap: "round" as const,
      strokeLinejoin: "round" as const,
    };
  }

  return {
    d: roughGenerator.opsToPath(set),
    stroke,
    fill: "none",
    strokeWidth: getDrawableStrokeWidth(drawable),
    opacity: 1,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
};

const RoughDrawable: React.FC<{
  drawable: Drawable;
  progress: number;
  stroke: string;
}> = ({ drawable, progress, stroke }) => {
  return (
    <>
      {drawable.sets.map((set, index) => {
        const pathStyle = getPathStyle(set, drawable, stroke);
        const isStrokeReveal = pathStyle.stroke !== "none";
        return (
          <path
            key={`${drawable.shape}-${index}`}
            d={pathStyle.d}
            stroke={pathStyle.stroke}
            fill={pathStyle.fill}
            strokeWidth={pathStyle.strokeWidth}
            strokeDasharray={isStrokeReveal ? DASH_LENGTH : undefined}
            strokeDashoffset={isStrokeReveal ? DASH_LENGTH * (1 - progress) : undefined}
            opacity={isStrokeReveal ? pathStyle.opacity : progress}
            strokeLinecap={pathStyle.strokeLinecap}
            strokeLinejoin={pathStyle.strokeLinejoin}
          />
        );
      })}
    </>
  );
};

const makeLineDrawable = (element: LineElement) => {
  const baseOptions = {
    roughness: element.roughness ?? 1.3,
    stroke: element.stroke ?? "#22313b",
    strokeWidth: element.strokeWidth ?? 4,
    bowing: 1.5,
  };

  if (element.type === "arrow") {
    const dx = element.to.x - element.from.x;
    const dy = element.to.y - element.from.y;
    const angle = Math.atan2(dy, dx);
    const headLength = 26;
    const left = {
      x: element.to.x - headLength * Math.cos(angle - Math.PI / 6),
      y: element.to.y - headLength * Math.sin(angle - Math.PI / 6),
    };
    const right = {
      x: element.to.x - headLength * Math.cos(angle + Math.PI / 6),
      y: element.to.y - headLength * Math.sin(angle + Math.PI / 6),
    };

    return [
      roughGenerator.line(element.from.x, element.from.y, element.to.x, element.to.y, baseOptions),
      roughGenerator.line(left.x, left.y, element.to.x, element.to.y, baseOptions),
      roughGenerator.line(right.x, right.y, element.to.x, element.to.y, baseOptions),
    ];
  }

  return [roughGenerator.line(element.from.x, element.from.y, element.to.x, element.to.y, baseOptions)];
};

const makeCircleDrawable = (element: CircleElement) => {
  return [
    roughGenerator.circle(element.center.x, element.center.y, element.radius * 2, {
      roughness: element.roughness ?? 1.4,
      stroke: element.stroke ?? "#22313b",
      strokeWidth: element.strokeWidth ?? 4,
      fill: element.fill,
      fillStyle: "solid",
    }),
  ];
};

const makeWavePath = (element: WaveElement) => {
  if (element.points.length === 0) {
    return "";
  }

  return element.points.reduce((acc, point, index) => {
    if (index === 0) {
      return `M ${point.x} ${point.y}`;
    }

    const prev = element.points[index - 1];
    const controlX = (prev.x + point.x) / 2;
    return `${acc} Q ${controlX} ${prev.y} ${point.x} ${point.y}`;
  }, "");
};

const DotsDrawable: React.FC<{ element: DotsElement; progress: number }> = ({
  element,
  progress,
}) => {
  const visibleDots = Math.max(0, Math.floor(element.points.length * progress));
  return (
    <>
      {element.points.slice(0, visibleDots).map((point, index) => (
        <circle
          key={`${element.id}-${index}`}
          cx={point.x}
          cy={point.y}
          r={element.radius}
          fill={element.fill ?? "#b8c8d9"}
          stroke={element.stroke ?? "#22313b"}
          strokeWidth={1.5}
          opacity={0.9}
        />
      ))}
    </>
  );
};

const TextDrawable: React.FC<{ element: TextElement; progress: number }> = ({
  element,
  progress,
}) => {
  const offsetY = 18 * (1 - progress);
  return (
    <foreignObject
      x={element.position.x}
      y={element.position.y + offsetY}
      width={element.maxWidth ?? 420}
      height={220}
      style={{ overflow: "visible", opacity: progress }}
    >
      <div
        style={{
          color: element.color ?? "#20303c",
          fontSize: element.fontSize,
          fontWeight: 700,
          lineHeight: 1.15,
          textAlign: element.align ?? "left",
          fontFamily: '"Comic Sans MS", "Trebuchet MS", sans-serif',
        }}
      >
        {element.text}
      </div>
    </foreignObject>
  );
};

export const SketchElement: React.FC<{ element: SceneElement }> = ({ element }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const startFrame = Math.floor(element.startSec * fps);
  const endFrame = Math.max(startFrame + 1, Math.ceil((element.startSec + element.durationSec) * fps));
  const progress = getReveal(startFrame, endFrame, frame);

  if (element.type === "text") {
    return <TextDrawable element={element} progress={progress} />;
  }

  if (element.type === "dots") {
    return <DotsDrawable element={element} progress={progress} />;
  }

  if (element.type === "wave") {
    return (
      <path
        d={makeWavePath(element)}
        fill="none"
        stroke={element.stroke ?? "#3b78ff"}
        strokeWidth={element.strokeWidth ?? 6}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray={DASH_LENGTH}
        strokeDashoffset={DASH_LENGTH * (1 - progress)}
      />
    );
  }

  const drawables =
    element.type === "circle" ? makeCircleDrawable(element) : makeLineDrawable(element);

  return (
    <>
      {drawables.map((drawable, index) => (
        <RoughDrawable
          key={`${element.id}-${index}`}
          drawable={drawable}
          progress={progress}
          stroke={element.stroke ?? "#22313b"}
        />
      ))}
    </>
  );
};
