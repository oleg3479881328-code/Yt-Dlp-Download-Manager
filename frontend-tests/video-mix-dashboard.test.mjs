import test from "node:test";
import assert from "node:assert/strict";

import {
  buildEmptyProjectWorkspaceState,
  collectDraftNotesFromElements,
  filterSelectedCandidateIdsToVisible,
  resolveInitialLocale,
  resolveReviewNoteValue,
  translate,
} from "../app/static/video-mix-dashboard.js";

test("buildEmptyProjectWorkspaceState resets project-scoped dashboard state to defaults", () => {
  const debugLogs = [{ at: "12:00:00", kind: "info", message: "keep log" }];
  const workspace = buildEmptyProjectWorkspaceState(debugLogs);

  assert.equal(workspace.dashboard, null);
  assert.equal(workspace.workDir, "");
  assert.equal(workspace.quickMixEstimate.status, "idle");
  assert.deepEqual(workspace.lastExportedPaths, []);
  assert.equal(workspace.sourceScan, null);
  assert.equal(workspace.quickMixResult, null);
  assert.equal(workspace.sourceWorkDirAuto, true);
  assert.deepEqual([...workspace.selectedCandidateIds], []);
  assert.deepEqual([...workspace.draftNotesByCandidateId.entries()], []);
  assert.deepEqual(workspace.debugLogs, debugLogs);
  assert.deepEqual(workspace.filters, {
    status: "all",
    warnings: "all",
    search: "",
    sort: "score_desc",
  });
});

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
  assert.equal(translate("ru", "quickmix_music_label"), "Музыкальный трек (опционально)");
  assert.equal(translate("ru", "source_drop_zip"), "Перетащите папку или ZIP сюда");
  assert.equal(translate("en", "selected_count", { count: 3 }), "3 selected");
});
