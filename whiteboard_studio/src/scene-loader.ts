import { cancelRender, continueRender, delayRender, staticFile } from "remotion";
import { useEffect, useState } from "react";
import type { PathGroupElement, SceneSpecFile, StrokePathStep } from "./sceneTypes";

const FALLBACK_SPEC: SceneSpecFile = {
  meta: {
    title: "Почему небо голубое?",
    fps: 30,
    width: 1080,
    height: 1920,
  },
  scenes: [],
};

type ApprovedPathGroupTimelineItem = {
  id: string;
  svgGroupId: string;
  startSec: number;
  durationSec: number;
  stroke: string;
  strokeWidth: number;
  opacity: number;
};

type ApprovedPencilHorseSpecFile = {
  meta: {
    title: string;
    fps: number;
    width: number;
    height: number;
    durationSec?: number;
  };
  assets: {
    drawingSvg: string;
  };
  pathGroupTimeline: ApprovedPathGroupTimelineItem[];
  renderInstructions?: {
    background?: string;
    finalHoldSec?: number;
  };
};

type SvgPathGroup = {
  id: string;
  paths: StrokePathStep[];
};

const extractAttribute = (source: string, attribute: string): string | null => {
  const escapedAttribute = attribute.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = source.match(new RegExp(`(?:^|\\s)${escapedAttribute}="([^"]+)"`));
  return match ? match[1] : null;
};

const resolveSiblingAssetPath = (specSrc: string, assetPath: string): string => {
  if (assetPath.includes("/") || assetPath.includes("\\")) {
    return assetPath.replace(/\\/g, "/");
  }

  const normalizedSpec = specSrc.replace(/\\/g, "/");
  const lastSlashIndex = normalizedSpec.lastIndexOf("/");
  if (lastSlashIndex === -1) {
    return assetPath;
  }

  return `${normalizedSpec.slice(0, lastSlashIndex + 1)}${assetPath}`;
};

const parseSvgPathGroups = (svgMarkup: string): Map<string, SvgPathGroup> => {
  const groups = new Map<string, SvgPathGroup>();
  const groupPattern = /<g\b([^>]*)id="([^"]+)"([^>]*)>([\s\S]*?)<\/g>/g;

  for (const match of svgMarkup.matchAll(groupPattern)) {
    const [, beforeId, id, afterId, content] = match;
    const attributeSource = `${beforeId} id="${id}" ${afterId}`;
    const paths: StrokePathStep[] = [];
    const pathPattern = /<path\b([^>]*)\/?>/g;

    for (const pathMatch of content.matchAll(pathPattern)) {
      const attributes = pathMatch[1];
      const d = extractAttribute(attributes, "d");
      if (!d) {
        continue;
      }

      paths.push({
        id: extractAttribute(attributes, "id") ?? `${id}-${paths.length}`,
        d,
        stroke: extractAttribute(attributes, "stroke") ?? extractAttribute(attributeSource, "stroke") ?? undefined,
        strokeWidth: Number(
          extractAttribute(attributes, "stroke-width") ??
            extractAttribute(attributeSource, "stroke-width") ??
            "0",
        ) || undefined,
        opacity: Number(
          extractAttribute(attributes, "opacity") ?? extractAttribute(attributeSource, "opacity") ?? "0",
        ) || undefined,
      });
    }

    groups.set(id, { id, paths });
  }

  return groups;
};

const isApprovedPencilHorseSpec = (
  payload: SceneSpecFile | ApprovedPencilHorseSpecFile,
): payload is ApprovedPencilHorseSpecFile => {
  return (
    "pathGroupTimeline" in payload &&
    Array.isArray(payload.pathGroupTimeline) &&
    "assets" in payload &&
    typeof payload.assets?.drawingSvg === "string"
  );
};

const buildApprovedPencilHorseSpec = (
  payload: ApprovedPencilHorseSpecFile,
  svgMarkup: string,
): SceneSpecFile => {
  const svgGroups = parseSvgPathGroups(svgMarkup);
  const finalHoldSec = payload.renderInstructions?.finalHoldSec ?? 0;
  const timelineEndSec = payload.pathGroupTimeline.reduce((max, group) => {
    return Math.max(max, group.startSec + group.durationSec);
  }, 0);
  const durationSec = Math.max(payload.meta.durationSec ?? 0, timelineEndSec + finalHoldSec);
  const elements: PathGroupElement[] = payload.pathGroupTimeline.map((group) => ({
    id: group.id,
    type: "pathGroup",
    startSec: group.startSec,
    durationSec: group.durationSec,
    stroke: group.stroke,
    strokeWidth: group.strokeWidth,
    opacity: group.opacity,
    paths: svgGroups.get(group.svgGroupId)?.paths ?? [],
  }));

  return {
    meta: {
      title: payload.meta.title,
      fps: payload.meta.fps,
      width: payload.meta.width,
      height: payload.meta.height,
    },
    scenes: [
      {
        id: "approved-pencil-horse-scene",
        title: "",
        caption: "",
        durationSec,
        background: payload.renderInstructions?.background ?? "#faf9f5",
        canvasHeight: payload.meta.height,
        layout: "fullBleed",
        elements,
      },
    ],
  };
};

export const loadSceneSpec = async (
  specSrc: string,
  payload: SceneSpecFile | ApprovedPencilHorseSpecFile,
): Promise<SceneSpecFile> => {
  if (!isApprovedPencilHorseSpec(payload)) {
    return payload;
  }

  const drawingSvgPath = resolveSiblingAssetPath(specSrc, payload.assets.drawingSvg);
  const response = await fetch(staticFile(drawingSvgPath));
  if (!response.ok) {
    throw new Error(`Failed to load SVG asset: ${drawingSvgPath}`);
  }

  const svgMarkup = await response.text();
  return buildApprovedPencilHorseSpec(payload, svgMarkup);
};

export const useSceneSpec = (specSrc: string): SceneSpecFile => {
  const [spec, setSpec] = useState<SceneSpecFile>(FALLBACK_SPEC);
  const [handle] = useState(() => delayRender(`Loading whiteboard scene spec: ${specSrc}`));

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      const url = staticFile(specSrc);
      const response = await fetch(url);
      const payload = (await response.json()) as SceneSpecFile | ApprovedPencilHorseSpecFile;
      const normalized = await loadSceneSpec(specSrc, payload);
      if (!cancelled) {
        setSpec(normalized);
        continueRender(handle);
      }
    };

    load().catch(() => {
      if (!cancelled) {
        setSpec(FALLBACK_SPEC);
        cancelRender(new Error(`Failed to load whiteboard scene spec: ${specSrc}`));
      }
    });

    return () => {
      cancelled = true;
    };
  }, [handle, specSrc]);

  return spec;
};

export const getTotalDurationInFrames = (spec: SceneSpecFile, fps: number): number => {
  const totalSec = spec.scenes.reduce((sum, scene) => sum + scene.durationSec, 0);
  return Math.max(Math.ceil(totalSec * fps), fps * 12);
};
