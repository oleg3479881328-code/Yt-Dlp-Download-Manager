import test from "node:test";
import assert from "node:assert/strict";

import {
  collectDraftNotesFromElements,
  filterSelectedCandidateIdsToVisible,
  resolveInitialLocale,
  resolveReviewNoteValue,
  translate,
} from "../app/static/video-mix-dashboard.js";

test("filterSelectedCandidateIdsToVisible excludes selected candidates hidden by filters", () => {
  const selected = new Set(["cand_hidden", "cand_visible", "cand_other_hidden"]);
  const visible = ["cand_visible", "cand_unselected"];

  assert.deepEqual(filterSelectedCandidateIdsToVisible(selected, visible), ["cand_visible"]);
});

test("collectDraftNotesFromElements captures in-progress textarea values", () => {
  const drafts = collectDraftNotesFromElements([
    {
      dataset: { noteFor: "cand_1" },
      value: "Unsaved note draft",
    },
  ]);

  assert.equal(drafts.get("cand_1"), "Unsaved note draft");
});

test("resolveReviewNoteValue prefers draft notes over persisted notes", () => {
  const candidate = {
    candidate_id: "cand_1",
    review_notes: "Persisted note",
  };
  const drafts = new Map([["cand_1", "Unsaved note draft"]]);

  assert.equal(resolveReviewNoteValue(candidate, drafts), "Unsaved note draft");
});

test("resolveInitialLocale prefers query param over stored locale", () => {
  assert.equal(resolveInitialLocale("?lang=en", "ru"), "en");
  assert.equal(resolveInitialLocale("", "en"), "en");
  assert.equal(resolveInitialLocale("", ""), "ru");
});

test("translate returns locale-specific dashboard strings", () => {
  assert.equal(translate("ru", "hero_title"), "Локальный дашборд для Quick Mix, ревью и экспорта");
  assert.equal(translate("en", "hero_title"), "Local dashboard for Quick Mix, review, and export");
  assert.equal(translate("en", "selected_count", { count: 3 }), "3 selected");
});
