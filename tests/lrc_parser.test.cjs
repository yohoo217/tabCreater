const assert = require("node:assert/strict");
const { test } = require("node:test");

require("../chord_sections/static/lrc.js");

const { parseLrcLyrics } = globalThis.ChordSectionsLrc;

test("parses timestamped LRC and removes copied trailing backslashes", () => {
  const source = [
    "### Muni Long - Made For Me (Official Music Video) Lyrics (.LRC)",
    "",
    "[00:06.51]Le - let me open the door baby\\",
    "[00:17.56]The smell of your perfume\\",
    "[00:21.40]I thought I was immune\\",
    "[02:51.80]Just for me\\",
    "[02:54.22]Mmm\\",
  ].join("\n");

  const result = parseLrcLyrics(source, 180);

  assert.equal(result.isLrc, true);
  assert.equal(result.dropped, 0);
  assert.deepEqual(result.lines.slice(0, 3), [
    { start: 6.51, end: 17.56, text: "Le - let me open the door baby" },
    { start: 17.56, end: 21.4, text: "The smell of your perfume" },
    { start: 21.4, end: 171.8, text: "I thought I was immune" },
  ]);
  assert.deepEqual(result.lines.at(-1), { start: 174.22, end: 180, text: "Mmm" });
});

test("uses an offset and supports multiple timestamps for one lyric", () => {
  const result = parseLrcLyrics("[offset:500]\n[00:01.00][00:03.00]Hello", 10);

  assert.deepEqual(result.lines, [
    { start: 1.5, end: 3.5, text: "Hello" },
    { start: 3.5, end: 5.5, text: "Hello" },
  ]);
});
