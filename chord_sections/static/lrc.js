(function registerLrcParser(root) {
  function parseLrcLyrics(content, audioDuration) {
    const source = content.replace(/^\uFEFF/, "");
    const offsetMatch = source.match(/^\[offset:\s*(-?\d+)\s*\]/im);
    const offsetSeconds = offsetMatch ? Number(offsetMatch[1]) / 1000 : 0;
    const timestampPattern = /^\[(\d{1,2}):([0-5]\d)(?:[.,](\d{1,3}))?\]/;
    const entries = [];
    let hasTimestamp = false;

    for (const rawLine of source.split(/\r?\n/)) {
      let remaining = rawLine.trim();
      const timestamps = [];
      while (true) {
        const match = timestampPattern.exec(remaining);
        if (!match) break;
        hasTimestamp = true;
        const fraction = match[3] ? Number(`0.${match[3]}`) : 0;
        timestamps.push(Math.max(0, Number(match[1]) * 60 + Number(match[2]) + fraction + offsetSeconds));
        remaining = remaining.slice(match[0].length);
      }

      // Some copied lyric pages add a trailing backslash as a visual line break.
      // It is not part of the lyric text.
      const text = remaining.trim().replace(/\\+$/, "").trimEnd();
      if (!text || !timestamps.length) continue;
      for (const start of timestamps) entries.push({ start, text });
    }
    if (!hasTimestamp) return { isLrc: false, lines: [], dropped: 0 };

    entries.sort((left, right) => left.start - right.start);
    const validEntries = entries.filter((entry) => entry.start < audioDuration);
    const distinctStarts = [...new Set(validEntries.map((entry) => entry.start))];
    const intervals = distinctStarts.slice(1)
      .map((start, index) => start - distinctStarts[index])
      .filter((interval) => interval > 0);
    intervals.sort((left, right) => left - right);
    const finalLineDuration = intervals.length
      ? Math.min(6, Math.max(2, intervals[Math.floor(intervals.length / 2)]))
      : 4;

    const lines = validEntries.map((entry) => {
      const nextStart = distinctStarts.find((start) => start > entry.start);
      const minimumEnd = entry.start + Math.min(0.1, audioDuration - entry.start);
      const end = nextStart ?? Math.min(
        audioDuration,
        Math.max(minimumEnd, entry.start + finalLineDuration),
      );
      return { start: entry.start, end, text: entry.text };
    });
    const inRangeLines = lines.filter((line) => line.start < audioDuration && line.end <= audioDuration);
    return {
      isLrc: true,
      lines: inRangeLines,
      dropped: entries.length - inRangeLines.length,
    };
  }

  root.ChordSectionsLrc = { parseLrcLyrics };
}(typeof window === "undefined" ? globalThis : window));
