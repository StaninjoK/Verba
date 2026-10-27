import assert from "node:assert/strict";
import { test } from "node:test";
import {
  activeSegmentIndex,
  findMatches,
  formatBytes,
  formatClock,
  formatDuration,
  segmentsToText,
  wordCount,
} from "./format.ts";

const segs = [
  { id: 0, start: 0, end: 2.5, text: "Hello world" },
  { id: 1, start: 2.5, end: 5, text: "  hello again, WORLD " },
  { id: 2, start: 10, end: 12, text: "" },
];

test("formatClock", () => {
  assert.equal(formatClock(0), "0:00");
  assert.equal(formatClock(5.9), "0:05");
  assert.equal(formatClock(754), "12:34");
  assert.equal(formatClock(3723), "1:02:03");
  assert.equal(formatClock(-1), "0:00");
  assert.equal(formatClock(Number.NaN), "0:00");
});

test("formatDuration", () => {
  assert.equal(formatDuration(0.2), "1 s");
  assert.equal(formatDuration(42), "42 s");
  assert.equal(formatDuration(600), "10 min");
  assert.equal(formatDuration(3840), "1 h 4 min");
  assert.equal(formatDuration(7200), "2 h");
  assert.equal(formatDuration(null), "–");
});

test("formatBytes", () => {
  assert.equal(formatBytes(512), "512 B");
  assert.equal(formatBytes(1536), "1.5 KB");
  assert.equal(formatBytes(500 * 1024 * 1024), "500 MB");
  assert.equal(formatBytes(1536, "de"), "1,5 KB");
});

test("segmentsToText skips empty segments", () => {
  assert.equal(segmentsToText(segs), "Hello world\n\nhello again, WORLD");
});

test("findMatches is case-insensitive and ordered", () => {
  const m = findMatches(segs, "world");
  assert.deepEqual(m.map((x) => [x.segmentId, x.start]), [[0, 6], [1, 15]]);
  assert.equal(findMatches(segs, "   ").length, 0);
  assert.equal(findMatches(segs, "HELLO").length, 2);
});

test("activeSegmentIndex", () => {
  assert.equal(activeSegmentIndex(segs, 0), 0);
  assert.equal(activeSegmentIndex(segs, 3), 1);
  assert.equal(activeSegmentIndex(segs, 8), -1);
  assert.equal(activeSegmentIndex(segs, 11), 2);
  assert.equal(activeSegmentIndex([], 1), -1);
});

test("wordCount", () => {
  assert.equal(wordCount(segs), 5);
});
