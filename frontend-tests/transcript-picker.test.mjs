import test from "node:test";
import assert from "node:assert/strict";

import {
  buildEpisodeLabel,
  buildTranscriptSelection,
  parseTranscriptText,
  parseTranscriptTime,
  resolveTranscriptEntryEnd,
} from "../app/static/transcript-picker.js";

test("parseTranscriptTime supports SRT-style timestamps", () => {
  assert.equal(parseTranscriptTime("00:00:05,000"), 5);
  assert.equal(parseTranscriptTime("00:01:12.500"), 72.5);
  assert.equal(parseTranscriptTime("01:02:03"), 3723);
});

test("parseTranscriptText parses SRT blocks", () => {
  const entries = parseTranscriptText(`
1
00:00:05,000 --> 00:00:12,000
Example subtitle text

2
00:00:12,000 --> 00:00:18,500
Next subtitle line
`);

  assert.equal(entries.length, 2);
  assert.deepEqual(entries[0], {
    start: 5,
    end: 12,
    text: "Example subtitle text",
    source: "srt",
  });
});

test("parseTranscriptText parses timestamped lines and infers next end", () => {
  const entries = parseTranscriptText(`
00:00:05 Example subtitle text
00:00:12 Next subtitle line
00:00:20 Final line
`);

  assert.equal(entries.length, 3);
  assert.equal(resolveTranscriptEntryEnd(entries, 0), 12);
  assert.equal(resolveTranscriptEntryEnd(entries, 1), 20);
  assert.equal(resolveTranscriptEntryEnd(entries, 2), null);
});

test("buildTranscriptSelection returns range metadata and label", () => {
  const entries = parseTranscriptText(`
1
00:00:05,000 --> 00:00:12,000
This is the hook

2
00:00:12,000 --> 00:00:18,000
Second line continues
`);

  const selection = buildTranscriptSelection(entries, 0, 1);
  assert.equal(selection.start, 5);
  assert.equal(selection.end, 18);
  assert.equal(selection.duration, 13);
  assert.equal(selection.label, "This is the hook Second line");
  assert.match(selection.snippet, /Second line continues/);
});

test("buildEpisodeLabel keeps the first few words", () => {
  assert.equal(
    buildEpisodeLabel("One two three four five six seven eight"),
    "One two three four five six"
  );
});
