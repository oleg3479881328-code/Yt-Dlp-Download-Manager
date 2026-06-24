const SRT_TIME_RE = /^\s*(\d{1,2}:\d{2}(?::\d{2})?[,.]\d{1,3}|\d{1,2}:\d{2}(?::\d{2})?)\s*-->\s*(\d{1,2}:\d{2}(?::\d{2})?[,.]\d{1,3}|\d{1,2}:\d{2}(?::\d{2})?)\s*$/;
const TIMESTAMPED_LINE_RE = /^\s*(\d{1,2}:\d{2}(?::\d{2})?(?:[,.]\d{1,3})?)\s+(.+?)\s*$/;

export function parseTranscriptTime(value) {
  const raw = String(value || "").trim().replace(",", ".");
  if (!raw) {
    throw new Error("Timestamp is required");
  }
  const parts = raw.split(":");
  if (parts.length < 2 || parts.length > 3) {
    throw new Error(`Unsupported timestamp: ${value}`);
  }

  const secondsPart = Number(parts.at(-1));
  const minutesPart = Number(parts.at(-2));
  const hoursPart = parts.length === 3 ? Number(parts[0]) : 0;

  if ([hoursPart, minutesPart, secondsPart].some((part) => Number.isNaN(part))) {
    throw new Error(`Unsupported timestamp: ${value}`);
  }
  if (minutesPart >= 60 || secondsPart >= 60) {
    throw new Error(`Invalid timestamp: ${value}`);
  }
  return roundSeconds(hoursPart * 3600 + minutesPart * 60 + secondsPart);
}

export function parseTranscriptText(text) {
  const normalized = String(text || "").replace(/\r\n/g, "\n").trim();
  if (!normalized) {
    throw new Error("Transcript text is required");
  }

  const srtEntries = parseSrtBlocks(normalized);
  if (srtEntries.length) {
    return srtEntries;
  }

  const timestampedEntries = parseTimestampedLines(normalized);
  if (timestampedEntries.length) {
    return timestampedEntries;
  }

  throw new Error("Could not parse transcript. Use SRT or timestamped lines.");
}

export function resolveTranscriptEntryEnd(entries, index) {
  const entry = entries[index];
  if (!entry) return null;
  if (entry.end !== null && entry.end !== undefined) return entry.end;
  if (entries[index + 1]) return entries[index + 1].start;
  return null;
}

export function buildTranscriptSelection(entries, startIndex, endIndex) {
  if (!Array.isArray(entries) || !entries.length) {
    throw new Error("Transcript entries are required");
  }
  if (startIndex === null || endIndex === null) {
    throw new Error("Start and end lines are required");
  }

  const lower = Math.min(startIndex, endIndex);
  const upper = Math.max(startIndex, endIndex);
  const startEntry = entries[lower];
  const endEntry = entries[upper];
  const end = resolveTranscriptEntryEnd(entries, upper);
  if (!startEntry || !endEntry || end === null) {
    throw new Error("Selected transcript range has no end time");
  }
  if (end <= startEntry.start) {
    throw new Error("Selected transcript range must have positive duration");
  }

  const snippet = entries
    .slice(lower, upper + 1)
    .map((entry) => entry.text)
    .filter(Boolean)
    .join(" ")
    .trim();

  return {
    start: startEntry.start,
    end,
    duration: roundSeconds(end - startEntry.start),
    snippet,
    label: buildEpisodeLabel(snippet),
    startIndex: lower,
    endIndex: upper,
  };
}

export function buildEpisodeLabel(text, maxWords = 6) {
  const words = String(text || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, maxWords);
  return words.join(" ");
}

function parseSrtBlocks(text) {
  const blocks = text.split(/\n\s*\n+/);
  const entries = [];

  for (const block of blocks) {
    const lines = block
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length < 2) continue;

    const timeLineIndex = lines.findIndex((line) => line.includes("-->"));
    if (timeLineIndex === -1) continue;

    const match = lines[timeLineIndex].match(SRT_TIME_RE);
    if (!match) continue;

    const textValue = lines.slice(timeLineIndex + 1).join(" ").trim();
    if (!textValue) continue;

    entries.push({
      start: parseTranscriptTime(match[1]),
      end: parseTranscriptTime(match[2]),
      text: textValue,
      source: "srt",
    });
  }

  return entries;
}

function parseTimestampedLines(text) {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const entries = [];

  for (const line of lines) {
    const match = line.match(TIMESTAMPED_LINE_RE);
    if (!match) continue;

    entries.push({
      start: parseTranscriptTime(match[1]),
      end: null,
      text: match[2].trim(),
      source: "timestamped",
    });
  }

  return entries;
}

function roundSeconds(value) {
  return Math.round(Number(value) * 1000) / 1000;
}
