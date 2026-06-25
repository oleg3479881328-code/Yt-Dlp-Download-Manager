import { staticFile } from "remotion";
import { useEffect, useState } from "react";
import type { SceneSpecFile } from "./sceneTypes";

const FALLBACK_SPEC: SceneSpecFile = {
  meta: {
    title: "Почему небо голубое?",
    fps: 30,
    width: 1080,
    height: 1920,
  },
  scenes: [],
};

export const useSceneSpec = (specSrc: string): SceneSpecFile => {
  const [spec, setSpec] = useState<SceneSpecFile>(FALLBACK_SPEC);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      const url = staticFile(specSrc);
      const response = await fetch(url);
      const payload = (await response.json()) as SceneSpecFile;
      if (!cancelled) {
        setSpec(payload);
      }
    };

    load().catch(() => {
      if (!cancelled) {
        setSpec(FALLBACK_SPEC);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [specSrc]);

  return spec;
};

export const getTotalDurationInFrames = (spec: SceneSpecFile, fps: number): number => {
  const totalSec = spec.scenes.reduce((sum, scene) => sum + scene.durationSec, 0);
  return Math.max(Math.ceil(totalSec * fps), fps * 12);
};
