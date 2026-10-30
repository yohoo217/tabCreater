const form = document.querySelector("#analysis-form");
const fileInput = document.querySelector("#audio");
const fileName = document.querySelector("#file-name");
const audioPreview = document.querySelector("#audio-preview");
const timeSignatureSelect = document.querySelector("#time-signature");
const errorMessage = document.querySelector("#error-message");
const analyzeButton = document.querySelector("#analyze-button");
const resultsEmpty = document.querySelector("#results-empty");
const resultsContent = document.querySelector("#results-content");
const originalKeySelect = document.querySelector("#original-key");
const transposeSelect = document.querySelector("#transpose-semitones");
const capoSelect = document.querySelector("#capo-fret");
const transposedAudioButton = document.querySelector("#download-transposed-audio");
const transcribeButton = document.querySelector("#transcribe-button");
const lyricsStatus = document.querySelector("#lyrics-status");
const lyricsList = document.querySelector("#lyrics-list");
const saveLyricsButton = document.querySelector("#save-lyrics");
const lyricsCorrection = document.querySelector("#lyrics-correction");
const lyricsReference = document.querySelector("#lyrics-reference");
const lyricsFile = document.querySelector("#lyrics-file");
const separateVocalsCheckbox = document.querySelector("#separate-vocals");
const languageToggle = document.querySelector("#language-toggle");
const lyricsEmpty = document.querySelector("#lyrics-empty");
const lyricsSettings = document.querySelector("#lyrics-settings");

let currentObjectUrl = null;
let currentAnalysis = null;
let currentLyrics = [];
let aiEngines = { demucs: false, faster_whisper: false };
let currentLanguage = localStorage.getItem("chord-sections-language") === "en" ? "en" : "zh";
const translations = {
  zh: {
    page_title: "和弦整理室",
    home: "和弦整理室首頁",
    brand: "和弦整理室",
    privacy: "音檔只在這台電腦處理",
    hero_title: "把一首歌，整理成看得懂的和弦表。",
    hero_copy: "選擇音檔、調整拍子設定，分析後即可預覽和下載 PDF。",
    setup_title: "歌曲與拍子",
    local_badge: "只在本機",
    song_title: "歌曲名稱",
    song_title_placeholder: "可留空，使用檔名",
    choose_audio: "選擇音訊",
    choose_file: "點此選擇歌曲檔案",
    supported_formats: "WAV、MP3、M4A、FLAC、OGG 或 AIFF，最大 300 MB",
    tempo: "速度 BPM",
    auto_estimate: "自動估計",
    tempo_help: "知道歌曲速度時可手動填寫；留空會自動估計。",
    time_signature: "拍號",
    meter_44: "4 / 4 常見拍",
    meter_34: "3 / 4 圓舞曲",
    meter_help: "自動偵測不一定可靠，請依歌曲需要修改。",
    advanced_timing: "進階拍子設定",
    beats_per_chord: "每幾拍估一次和弦",
    every_beat: "每 1 拍（較細）",
    every_two_beats: "每 2 拍（建議）",
    every_four_beats: "每 4 拍（較平滑）",
    bars_per_section: "每段幾小節",
    bars_2: "2 小節",
    bars_4: "4 小節（建議）",
    bars_8: "8 小節",
    downbeat_offset: "第一拍偏移（秒）",
    downbeat_help: "若前奏或檔案開頭有空白，可微調分拍起點。",
    analysis_resolution: "分析解析度",
    resolution_fast: "一般（較快）",
    resolution_cqt: "高解析 CQT（可比較）",
    resolution_help: "耗時依音檔和電腦而異；可比較結果，但不保證每首歌都更準。",
    harmonic_focus: "加強和聲分析",
    harmonic_focus_help: "弱化鼓與瞬態聲響；不保證每首歌都會更準。",
    analyze_song: "分析這首歌",
    confidence_title: "關於信心分數",
    confidence_note: "它是模型符合度與候選差距的啟發式指標，不是準確率。不要只為了分數變高而更改 BPM 或拍號。",
    results_empty_title: "分析結果會在這裡",
    results_empty_copy: "選擇歌曲並分析後，主要結果會以歌詞搭配和弦的方式呈現。",
    chord_diagram_title: "吉他指法",
    unavailable_chord_shape: "目前沒有這個和弦的常用指法圖。",
    shape_label: "指法",
    chord_shape_info: "指法 {shape} · {capo}",
    download_pdf: "下載 PDF",
    transposition_title: "調性、移調與 Capo",
    transposition_subtitle: "和弦譜或另存移調後音檔",
    original_key: "原調校正",
    use_estimate: "使用自動估計",
    target_transposition: "目標移調",
    capo_position: "Capo 位置",
    download_transposed_wav: "下載移調後 WAV",
    audio_shift_help: "這會另存一份 WAV，不會覆寫原檔；原音檔播放器保持不變。",
    confidence_explainer: "信心分數為啟發式參考，不代表真實辨識準確率。",
    section_chords: "段落和弦",
    section_subtitle: "相似段落使用相同標記",
    lyrics_title: "歌詞搭配和弦",
    lyrics_subtitle: "辨識結果可修改，時間以音檔為準",
    lyrics_settings: "歌詞辨識設定",
    open_lyrics_settings: "開啟歌詞辨識設定",
    more_analysis: "更多分析結果與設定",
    song_sheet_empty: "尚未產生歌詞和弦譜。展開歌詞辨識設定，開始分離人聲並辨識歌詞。",
    lyrics_settings: "歌詞辨識設定",
    open_lyrics_settings: "開啟歌詞辨識設定",
    more_analysis: "更多分析結果與設定",
    song_sheet_empty: "尚未產生歌詞和弦譜。展開歌詞辨識設定，開始分離人聲並辨識歌詞。",
    lyrics_intro: "本機分離人聲並辨識歌詞。首次執行會從 Hugging Face 下載所選模型；Small 約 484 MB，Base 約 145 MB。歌唱辨識可能漏字或聽錯，請回聽校對。",
    recognition_language: "辨識語言",
    auto_detect: "自動偵測",
    model: "模型",
    model_small: "Small（建議，約 484 MB）",
    model_base: "Base（較小，約 145 MB）",
    separate_vocals: "先分離人聲",
    separate_vocals_help: "建議開啟；首次使用會另外下載 Demucs 模型約 84 MB。",
    transcribe_button: "分離人聲並辨識歌詞",
    checking_models: "檢查本機歌詞模型…",
    import_lyrics: "匯入文字歌詞校正（每行需對應一條辨識結果）",
    lyrics_txt: "選擇純文字歌詞 .txt",
    lyrics_placeholder: "每行歌詞對應一條辨識結果；匯入後仍可逐行編輯。",
    apply_lyrics: "依行套用歌詞",
    save_lyrics: "儲存歌詞到 PDF",
    chord_timeline: "和弦時間軸",
    timeline_help: "點選時間可跳轉聆聽",
    start: "開始",
    end: "結束",
    original_chord: "原曲和弦",
    transposed: "移調後",
    capo_shape: "Capo 指型",
    confidence: "信心",
    footer_note: "本機分析工具 · 和弦與段落為自動估計，請搭配聆聽校對。",
    no_file: "請先選擇音檔。",
    analyze_error: "分析失敗，請檢查音檔後再試。",
    analyze_failed: "分析失敗，請稍後再試。",
    estimated_unknown: "未能估計",
    length: "長度",
    tempo_stat: "速度",
    meter_stat: "拍號",
    key_target: "原調 / 目標調",
    no_sections: "沒有找到可整理的段落。",
    playback_error: "瀏覽器無法播放這個音檔，請直接使用播放器確認。",
    auto_key: "使用自動估計",
    major_key: "大調",
    minor_key: "小調",
    no_transposition: "不移調",
    semitones: "半音",
    no_capo: "不用 Capo",
    fret: "品",
    original_label: "原調",
    target_label: "目標調",
    correction_label: "（原調校正 {shift} {unit}）",
    capo_summary: " Capo {fret}：指法比移調後的實際和弦低 {shift} 個半音。",
    no_capo_summary: " 不使用 Capo。",
    download_shifted: "下載 {shift} 半音 WAV",
    download_original: "下載原調 WAV",
    ai_status_error: "無法連線檢查本機模型；請確認本機服務仍在執行。",
    ai_install_missing: "歌詞模型尚未安裝。請在專案虛擬環境執行：python -m pip install -e '.[ai]'",
    local_download_note: "音檔會留在本機；模型若尚未快取，首次使用會從 Hugging Face 下載。",
    analyze_before_transcribe: "請先分析歌曲，再開始歌詞辨識。",
    transcribing_with_separation: "正在分離人聲並辨識歌詞。首次執行會下載模型，可能需要數分鐘…",
    transcribing_only: "正在辨識歌詞。首次執行會下載 Whisper 模型，可能需要數分鐘…",
    transcribe_error: "歌詞辨識失敗。",
    transcription_note: "歌詞是自動辨識結果；唱歌辨識可能有漏字或錯字，請逐行校對。可匯入文字歌詞或直接修改，儲存後會加入 PDF。",
    no_lyrics: "沒有辨識到歌詞；可試著選擇語言、上傳較清楚的音檔，或先關閉人聲分離比較。",
    lyrics_file_too_large: "歌詞文字檔不可超過 1 MB。",
    lyrics_line_mismatch: "歌詞有 {fileLines} 行，但辨識結果有 {segments} 段。請調整成相同行數，或直接逐段編輯。",
    lyrics_applied: "文字已套用到原辨識時間。請檢查同步位置後儲存。",
    save_error: "無法儲存歌詞。",
    saved_lyrics: "已儲存 {count} 行歌詞；下載 PDF 即包含歌詞和和弦。",
    lyric_line: "歌詞第 {number} 行",
    edit_lyric: "編輯歌詞",
    finish_editing: "完成",
    transcribing_label: "正在分離與辨識…",
    transposed_generating: "正在產生 WAV…",
    transposed_error: "無法產生移調後音檔。",
    analyzing_label: "正在分析音訊…",
    server_error: "請求失敗：{message}",
    no_chord: "無和弦",
    high: "高",
    medium: "中",
    low: "低"
  },
  en: {
    page_title: "Chord Sections",
    home: "Chord Sections home",
    brand: "Chord Sections",
    privacy: "Audio stays on this computer",
    hero_title: "Turn a song into a clear chord sheet.",
    hero_copy: "Choose an audio file, set the beat details, then review and download a PDF.",
    setup_title: "Song & timing",
    local_badge: "Local only",
    song_title: "Song title",
    song_title_placeholder: "Optional; defaults to the file name",
    choose_audio: "Choose audio",
    choose_file: "Choose a song file",
    supported_formats: "WAV, MP3, M4A, FLAC, OGG or AIFF, up to 300 MB",
    tempo: "Tempo",
    auto_estimate: "Estimate automatically",
    tempo_help: "Enter the known tempo, or leave blank for an automatic estimate.",
    time_signature: "Time signature",
    meter_44: "4 / 4 Common time",
    meter_34: "3 / 4 Waltz",
    meter_help: "Automatic detection may be inaccurate; adjust as needed.",
    advanced_timing: "Advanced timing",
    beats_per_chord: "Analyze a chord every",
    every_beat: "1 beat (more detail)",
    every_two_beats: "2 beats (recommended)",
    every_four_beats: "4 beats (smoother)",
    bars_per_section: "Bars per section",
    bars_2: "2 bars",
    bars_4: "4 bars (recommended)",
    bars_8: "8 bars",
    downbeat_offset: "First beat offset (seconds)",
    downbeat_help: "Adjust the beat grid if there is silence or an intro before the first beat.",
    analysis_resolution: "Analysis resolution",
    resolution_fast: "Standard (faster)",
    resolution_cqt: "High-resolution CQT (compare)",
    resolution_help: "Time depends on the audio and computer. Compare methods; neither guarantees better results.",
    harmonic_focus: "Enhance harmonic analysis",
    harmonic_focus_help: "Reduce drums and transients; results may vary by song.",
    analyze_song: "Analyze song",
    confidence_title: "About confidence scores",
    confidence_note: "This heuristic reflects template fit and the gap to the next candidate, not accuracy. Do not change BPM or meter just to raise the score.",
    results_empty_title: "Your results will appear here",
    results_empty_copy: "Analyze a song to see the main result as lyrics paired with chords.",
    chord_diagram_title: "Guitar fingering",
    unavailable_chord_shape: "A common fingering diagram is not available for this chord yet.",
    shape_label: "shape",
    chord_shape_info: "Shape {shape} · {capo}",
    download_pdf: "Download PDF",
    transposition_title: "Key, transposition & capo",
    transposition_subtitle: "Transpose the chart or save a shifted audio file",
    original_key: "Original key correction",
    use_estimate: "Use automatic estimate",
    target_transposition: "Transpose to",
    capo_position: "Capo position",
    download_transposed_wav: "Download transposed WAV",
    audio_shift_help: "Saves a separate WAV without changing the original file or player.",
    confidence_explainer: "Confidence is a heuristic reference, not a measured recognition accuracy.",
    section_chords: "Sections & chords",
    section_subtitle: "Similar sections share a label",
    lyrics_title: "Lyrics with chords",
    lyrics_subtitle: "Edit recognized text; timings follow the audio",
    lyrics_settings: "Lyric transcription settings",
    open_lyrics_settings: "Open lyric transcription settings",
    more_analysis: "More analysis results & settings",
    song_sheet_empty: "No chord-and-lyric sheet yet. Open lyric settings to separate vocals and transcribe lyrics.",
    lyrics_settings: "Lyric transcription settings",
    open_lyrics_settings: "Open lyric transcription settings",
    more_analysis: "More analysis results & settings",
    song_sheet_empty: "No chord-and-lyric sheet yet. Open lyric settings to separate vocals and transcribe lyrics.",
    lyrics_intro: "Separate vocals and transcribe lyrics locally. Models download from Hugging Face on first use: Small ~484 MB, Base ~145 MB. Singing recognition may miss or mishear words; review by listening.",
    recognition_language: "Recognition language",
    auto_detect: "Detect automatically",
    model: "Model",
    model_small: "Small (recommended, ~484 MB)",
    model_base: "Base (smaller, ~145 MB)",
    separate_vocals: "Separate vocals first",
    separate_vocals_help: "Recommended; downloads an additional Demucs model (~84 MB) on first use.",
    transcribe_button: "Separate vocals & transcribe",
    checking_models: "Checking local speech models…",
    import_lyrics: "Import lyrics to correct text (one line per recognized segment)",
    lyrics_txt: "Choose a plain-text lyrics file (.txt)",
    lyrics_placeholder: "One lyric line per recognized segment; you can edit each line after importing.",
    apply_lyrics: "Apply lyrics by line",
    save_lyrics: "Save lyrics to PDF",
    chord_timeline: "Chord timeline",
    timeline_help: "Select a timestamp to play from that point",
    start: "Start",
    end: "End",
    original_chord: "Original chord",
    transposed: "Transposed",
    capo_shape: "Capo shape",
    confidence: "Confidence",
    footer_note: "Local audio analysis · Chords and sections are estimates; please review by listening.",
    no_file: "Please choose an audio file first.",
    analyze_error: "Analysis failed. Check the audio file and try again.",
    analyze_failed: "Analysis failed. Please try again.",
    estimated_unknown: "Unavailable",
    length: "Duration",
    tempo_stat: "Tempo",
    meter_stat: "Meter",
    key_target: "Original / target key",
    no_sections: "No sections were found.",
    playback_error: "Your browser could not play this file. Please use the audio player to review it.",
    auto_key: "Automatic estimate",
    major_key: "major",
    minor_key: "minor",
    no_transposition: "No transposition",
    semitones: "semitones",
    no_capo: "No capo",
    fret: "fret",
    original_label: "Original",
    target_label: "Target",
    correction_label: " (key correction {shift} {unit})",
    capo_summary: " Capo {fret}: play shapes {shift} semitones below the sounding chords.",
    no_capo_summary: " No capo.",
    download_shifted: "Download {shift} {unit} WAV",
    download_original: "Download original-key WAV",
    ai_status_error: "Could not check local models. Make sure the local app is running.",
    ai_install_missing: "Speech models are not installed. Run: python -m pip install -e '.[ai]'",
    local_download_note: "Audio stays on this computer. Models download from Hugging Face the first time they are used.",
    analyze_before_transcribe: "Analyze a song before transcribing lyrics.",
    transcribing_with_separation: "Separating vocals and transcribing. First use may download models and take several minutes…",
    transcribing_only: "Transcribing lyrics. First use may download the Whisper model and take several minutes…",
    transcribe_error: "Lyric transcription failed.",
    transcription_note: "Transcription finished. Review each segment, or import a text file to correct the words. Save to include lyrics in the PDF.",
    no_lyrics: "No lyrics were recognized. Try selecting a language, using a clearer recording, or turning off vocal separation.",
    lyrics_file_too_large: "The lyrics text file must be 1 MB or smaller.",
    lyrics_line_mismatch: "The file has {fileLines} lines, but there are {segments} recognized segments. Match the line counts or edit each segment manually.",
    lyrics_applied: "Text applied using the original timestamps. Review the alignment, then save.",
    save_error: "Could not save lyrics.",
    saved_lyrics: "Saved {count} lyric lines. Download the PDF to include lyrics and chords.",
    lyric_line: "Lyric line {number}",
    edit_lyric: "Edit lyrics",
    finish_editing: "Done",
    transcribing_label: "Separating and transcribing…",
    transposed_generating: "Creating WAV…",
    transposed_error: "Could not create the transposed audio.",
    analyzing_label: "Analyzing audio…",
    server_error: "Request failed: {message}",
    no_chord: "N.C.",
    high: "High",
    medium: "Medium",
    low: "Low"
  }
};

function t(key, values = {}) {
  let value = translations[currentLanguage][key] || translations.zh[key];
  if (!value) return key;
  for (const [name, replacement] of Object.entries(values)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

function applyLanguage() {
  document.documentElement.lang = currentLanguage === "en" ? "en" : "zh-Hant";
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    const key = element.dataset.i18n;
    if (translations[currentLanguage][key]) element.textContent = t(key);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    const key = element.dataset.i18nPlaceholder;
    if (translations[currentLanguage][key]) element.setAttribute("placeholder", t(key));
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((element) => {
    const key = element.dataset.i18nAriaLabel;
    if (translations[currentLanguage][key]) element.setAttribute("aria-label", t(key));
  });
  document.title = t("page_title");
  languageToggle.textContent = currentLanguage === "en" ? "繁體中文" : "English";
  languageToggle.setAttribute("aria-label", currentLanguage === "en" ? "切換為繁體中文" : "Switch to English");
  updateTranspositionOptions();
  if (fileInput.files?.[0]) fileName.textContent = fileInput.files[0].name;
  if (currentAnalysis) {
    renderStats(currentAnalysis);
    renderSections(currentAnalysis.sections);
    renderChords(currentAnalysis.chords);
    renderLyrics();
    renderTransposition();
  }
  if (analyzeButton.classList.contains("loading")) setLoading(true);
  if (transcribeButton.classList.contains("loading")) setTranscribing(true);
  updateTranscribeAvailability();
}

languageToggle.addEventListener("click", () => {
  currentLanguage = currentLanguage === "en" ? "zh" : "en";
  localStorage.setItem("chord-sections-language", currentLanguage);
  applyLanguage();
});

document.querySelector("#open-lyrics-settings").addEventListener("click", () => {
  lyricsSettings.open = true;
  lyricsSettings.scrollIntoView({ behavior: "smooth", block: "center" });
});

const noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const notePitches = new Map(noteNames.map((note, index) => [note, index]));
for (const [note, pitch] of Object.entries({ Db: 1, Eb: 3, Gb: 6, Ab: 8, Bb: 10 })) {
  notePitches.set(note, pitch);
}

function updateTranspositionOptions() {
  const previousShift = transposeSelect.value || "0";
  const shiftOptions = [];
  for (let semitones = -12; semitones <= 12; semitones += 1) {
    const option = document.createElement("option");
    option.value = String(semitones);
    option.textContent = semitones === 0
      ? `${t("no_transposition")} (${t("original_label").toLowerCase()})`
      : `${semitones > 0 ? "+" : ""}${semitones} ${t("semitones")}`;
    shiftOptions.push(option);
  }
  transposeSelect.replaceChildren(...shiftOptions);
  transposeSelect.value = previousShift;

  const previousCapo = capoSelect.value || "0";
  const capoOptions = [];
  for (let fret = 0; fret <= 11; fret += 1) {
    const option = document.createElement("option");
    option.value = String(fret);
    option.textContent = fret === 0 ? t("no_capo") : `${fret} ${t("fret")}`;
    capoOptions.push(option);
  }
  capoSelect.replaceChildren(...capoOptions);
  capoSelect.value = previousCapo;
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (!file) return;
  currentAnalysis = null;
  currentLyrics = [];
  resultsContent.hidden = true;
  resultsEmpty.hidden = false;
  lyricsList.replaceChildren();
  lyricsList.hidden = true;
  lyricsCorrection.hidden = true;
  saveLyricsButton.hidden = true;
  transposedAudioButton.disabled = true;
  fileName.textContent = file.name;
  audioPreview.hidden = false;
  if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
  currentObjectUrl = URL.createObjectURL(file);
  audioPreview.src = currentObjectUrl;
  updateTranscribeAvailability();
});

applyLanguage();
refreshAiStatus();

timeSignatureSelect.addEventListener("change", () => {
  const [numerator, denominator] = timeSignatureSelect.value.split("/");
  document.querySelector("#time-signature-numerator").value = numerator;
  document.querySelector("#time-signature-denominator").value = denominator;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorMessage.hidden = true;
  if (!fileInput.files?.length) {
    showError(t("no_file"));
    return;
  }

  const formData = new FormData(form);
  setLoading(true);
  try {
    const response = await fetch("/api/analyze", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || t("analyze_error"));
    currentAnalysis = result;
    currentLyrics = [];
    populateOriginalKeys(result.estimated_key);
    transposedAudioButton.disabled = false;
    updateTranscribeAvailability();
    lyricsList.hidden = true;
    lyricsCorrection.hidden = true;
    saveLyricsButton.hidden = true;
    renderResult(result);
  } catch (error) {
    showError(error instanceof Error ? localizeError(error.message) : t("analyze_failed"));
  } finally {
    setLoading(false);
  }
});

function renderResult(result) {
  resultsEmpty.hidden = true;
  resultsContent.hidden = false;
  document.querySelector("#result-title").textContent = result.title;
  document.querySelector("#download-pdf").href = `/api/report/${encodeURIComponent(result.report_id)}.pdf`;
  renderStats(result);
  renderSections(result.sections);
  renderChords(result.chords);
  renderLyrics();
  renderTransposition();
  requestAnimationFrame(() => resultsContent.scrollIntoView({ behavior: "smooth", block: "start" }));
}

function renderStats(result) {
  const bpm = result.tempo_bpm == null ? t("estimated_unknown") : `${formatNumber(result.tempo_bpm)} BPM`;
  const selectedKey = currentOriginalKey();
  const targetKey = transposeKey(selectedKey, Number(transposeSelect.value));
  document.querySelector("#song-sheet-meta").textContent = [
    `${t("tempo_stat")}: ${bpm}`,
    `${t("meter_stat")}: ${result.time_signature}`,
    `${t("key_target")}: ${selectedKey || t("estimated_unknown")} → ${targetKey || t("estimated_unknown")}`,
  ].join("  ·  ");
  const stats = [
    [t("length"), formatTime(result.duration)],
    [t("tempo_stat"), bpm],
    [t("meter_stat"), result.time_signature],
    [t("key_target"), `${selectedKey || t("estimated_unknown")} → ${targetKey || t("estimated_unknown")}`],
  ];
  const grid = document.querySelector("#stats-grid");
  grid.replaceChildren(...stats.map(([label, value]) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    const caption = document.createElement("span");
    caption.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    card.append(caption, strong);
    return card;
  }));
}

function renderSections(sections) {
  const list = document.querySelector("#section-list");
  if (!sections.length) {
    list.textContent = t("no_sections");
    return;
  }
  list.replaceChildren(...sections.map((section) => {
    const row = document.createElement("article");
    row.className = "section-card";
    const label = document.createElement("span");
    label.className = "section-label";
    label.textContent = section.label;
    const detail = document.createElement("div");
    detail.className = "section-detail";
    const time = document.createElement("small");
    time.textContent = `${formatTime(section.start)} – ${formatTime(section.end)}`;
    const chords = document.createElement("p");
    chords.textContent = deduplicate(section.chords.map(transposedChord)).join(" → ") || t("no_chord");
    detail.append(time, chords);
    row.append(label, detail);
    return row;
  }));
}

function renderChords(chords) {
  const body = document.querySelector("#chord-rows");
  body.replaceChildren(...chords.map((event) => {
    const row = document.createElement("tr");
    const start = document.createElement("td");
    const seek = document.createElement("button");
    seek.className = "time-link";
    seek.type = "button";
    seek.textContent = formatTime(event.start);
    seek.addEventListener("click", () => {
      audioPreview.currentTime = event.start;
      audioPreview.play().catch(() => showError(t("playback_error")));
    });
    start.append(seek);

    const end = document.createElement("td");
    end.textContent = formatTime(event.end);
    const chord = document.createElement("td");
    chord.className = "chord-cell";
    chord.textContent = event.chord;
    const transposed = document.createElement("td");
    transposed.className = "chord-cell";
    transposed.textContent = transposedChord(event.chord);
    const capoShape = document.createElement("td");
    capoShape.className = "chord-cell capo-cell";
    capoShape.textContent = transposeChord(transposedChord(event.chord), -Number(capoSelect.value));
    const confidence = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `confidence-badge ${confidenceClass(event.confidence)}`;
    badge.textContent = `${t(confidenceClass(event.confidence))} ${Math.round(event.confidence * 100)}%`;
    confidence.append(badge);
    row.append(start, end, chord, transposed, capoShape, confidence);
    return row;
  }));
}

function populateOriginalKeys(estimatedKey) {
  const options = [new Option(`${t("auto_key")}${estimatedKey ? ` (${estimatedKey})` : ""}`, "auto")];
  for (const root of noteNames) {
    options.push(new Option(`${root} ${t("major_key")}`, root));
    options.push(new Option(`${root} ${t("minor_key")}`, `${root}m`));
  }
  originalKeySelect.replaceChildren(...options);
  originalKeySelect.value = "auto";
}

function renderTransposition() {
  if (!currentAnalysis) return;
  const originalKey = currentOriginalKey();
  const shift = Number(transposeSelect.value);
  const capo = Number(capoSelect.value);
  const correctedSemitones = getOriginalKeyCorrection(currentAnalysis.estimated_key, originalKey);
  const targetKey = transposeKey(originalKey, shift);
  const pdfUrl = new URL(
    `/api/report/${encodeURIComponent(currentAnalysis.report_id)}.pdf`,
    window.location.origin,
  );
  pdfUrl.searchParams.set("semitones", String(shift));
  pdfUrl.searchParams.set("capo", String(capo));
  pdfUrl.searchParams.set("original_key", originalKeySelect.value);
  pdfUrl.searchParams.set("lang", currentLanguage);
  document.querySelector("#download-pdf").href = pdfUrl.pathname + pdfUrl.search;

  const shiftLabel = shift === 0 ? t("no_transposition") : `${shift > 0 ? "+" : ""}${shift} ${t("semitones")}`;
  const correctionLabel = correctedSemitones
    ? t("correction_label", {
      shift: `${correctedSemitones > 0 ? "+" : ""}${correctedSemitones}`,
      unit: t("semitones"),
    })
    : "";
  const separator = currentLanguage === "en" ? "; " : "；";
  const sentenceEnd = currentLanguage === "en" ? "." : "。";
  document.querySelector("#transpose-summary").textContent =
    `${t("original_label")} ${originalKey || t("estimated_unknown")} → ${t("target_label")} ${targetKey || t("estimated_unknown")}${separator}${shiftLabel}${correctionLabel}${sentenceEnd}` +
    (capo
      ? t("capo_summary", { fret: capo, shift: capo })
      : t("no_capo_summary"));
  transposedAudioButton.querySelector("[data-i18n]").textContent = shift
    ? t("download_shifted", { shift: `${shift > 0 ? "+" : ""}${shift}`, unit: t("semitones") })
    : t("download_original");

  renderStats(currentAnalysis);
  renderSections(currentAnalysis.sections);
  renderChords(currentAnalysis.chords);
  renderLyrics();
}

async function refreshAiStatus() {
  try {
    const response = await fetch("/api/ai-status");
    const status = await response.json();
    aiEngines = status.engines || aiEngines;
    updateTranscribeAvailability();
  } catch {
    lyricsStatus.textContent = t("ai_status_error");
  }
}

function updateTranscribeAvailability() {
  const missingWhisper = !aiEngines.faster_whisper;
  const missingDemucs = separateVocalsCheckbox.checked && !aiEngines.demucs;
  transcribeButton.disabled = !currentAnalysis || missingWhisper || missingDemucs;
  if (missingWhisper || missingDemucs) {
    lyricsStatus.textContent = t("ai_install_missing");
  } else if (currentAnalysis) {
    lyricsStatus.textContent = t("local_download_note");
  } else {
    lyricsStatus.textContent = t("analyze_before_transcribe");
  }
}

separateVocalsCheckbox.addEventListener("change", updateTranscribeAvailability);

transcribeButton.addEventListener("click", async () => {
  if (!currentAnalysis || !fileInput.files?.[0]) return;
  const formData = new FormData();
  formData.append("audio", fileInput.files[0]);
  formData.append("report_id", currentAnalysis.report_id);
  formData.append("language", document.querySelector("#lyrics-language").value);
  formData.append("model_size", document.querySelector("#lyrics-model").value);
  formData.append("ui_language", currentLanguage);
  if (separateVocalsCheckbox.checked) formData.append("separate_vocals", "on");
  setTranscribing(true);
  lyricsStatus.textContent = separateVocalsCheckbox.checked
    ? t("transcribing_with_separation")
    : t("transcribing_only");
  errorMessage.hidden = true;
  try {
    const response = await fetch("/api/transcribe", { method: "POST", body: formData });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || t("transcribe_error"));
    currentLyrics = result.lyrics.map((line) => ({ ...line }));
    lyricsSettings.open = false;
    lyricsStatus.textContent = currentLyrics.length
      ? t("transcription_note")
      : t("no_lyrics");
    lyricsCorrection.hidden = !currentLyrics.length;
    saveLyricsButton.hidden = !currentLyrics.length;
    renderLyrics();
  } catch (error) {
    lyricsStatus.textContent = "";
    showError(error instanceof Error ? localizeError(error.message) : t("transcribe_error"));
  } finally {
    setTranscribing(false);
  }
});

lyricsFile.addEventListener("change", async () => {
  const file = lyricsFile.files?.[0];
  if (!file) return;
  if (file.size > 1024 * 1024) {
    showError(t("lyrics_file_too_large"));
    lyricsFile.value = "";
    return;
  }
  lyricsReference.value = await file.text();
});

document.querySelector("#apply-lyrics").addEventListener("click", () => {
  const lines = lyricsReference.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length !== currentLyrics.length) {
    showError(t("lyrics_line_mismatch", { fileLines: lines.length, segments: currentLyrics.length }));
    return;
  }
  errorMessage.hidden = true;
  currentLyrics = currentLyrics.map((line, index) => ({ ...line, text: lines[index] }));
  renderLyrics();
  lyricsStatus.textContent = t("lyrics_applied");
});

saveLyricsButton.addEventListener("click", async () => {
  if (!currentAnalysis) return;
  saveLyricsButton.disabled = true;
  try {
    const response = await fetch(`/api/lyrics/${encodeURIComponent(currentAnalysis.report_id)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lyrics: currentLyrics }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || t("save_error"));
    lyricsStatus.textContent = t("saved_lyrics", { count: result.saved });
  } catch (error) {
    showError(error instanceof Error ? localizeError(error.message) : t("save_error"));
  } finally {
    saveLyricsButton.disabled = false;
  }
});

function renderLyrics() {
  lyricsEmpty.hidden = currentLyrics.length > 0;
  if (!currentAnalysis || !currentLyrics.length) {
    lyricsList.hidden = true;
    return;
  }
  lyricsList.hidden = false;
  lyricsList.replaceChildren(...currentLyrics.map((line, index) => {
    const card = document.createElement("article");
    card.className = "lyric-card";
    const meta = document.createElement("div");
    meta.className = "lyric-meta";
    const seek = document.createElement("button");
    seek.className = "time-link";
    seek.type = "button";
    seek.textContent = `${formatTime(line.start)} – ${formatTime(line.end)}  ▶`;
    seek.addEventListener("click", () => {
      audioPreview.currentTime = line.start;
      audioPreview.play().catch(() => showError(t("playback_error")));
    });
    meta.append(seek);

    const chordLine = document.createElement("div");
    chordLine.className = "lyric-chord-line";
    const events = chordEventsForLyrics(line);
    if (!events.length) {
      const noChord = document.createElement("span");
      noChord.className = "lyric-chord-empty";
      noChord.textContent = t("no_chord");
      chordLine.append(noChord);
    } else {
      const duration = Math.max(line.end - line.start, 0.001);
      events.forEach((event) => {
        const soundingChord = transposedChord(event.chord);
        const shape = transposeChord(soundingChord, -Number(capoSelect.value));
        const marker = document.createElement("span");
        const relativeStart = Math.max(0, event.start - line.start);
        const position = Math.min(96, (relativeStart / duration) * 100);
        marker.className = `lyric-chord-marker${position > 65 ? " tooltip-right" : ""}`;
        marker.style.left = `${position}%`;
        marker.append(createChordButton(soundingChord, shape));
        chordLine.append(marker);
      });
    }

    const lyricText = document.createElement("p");
    lyricText.className = "lyric-text";
    lyricText.textContent = line.text;

    const editButton = document.createElement("button");
    editButton.className = "lyric-edit-button";
    editButton.type = "button";
    editButton.textContent = t("edit_lyric");

    const text = document.createElement("textarea");
    text.rows = 2;
    text.maxLength = 500;
    text.value = line.text;
    text.setAttribute("aria-label", t("lyric_line", { number: index + 1 }));
    text.hidden = true;
    text.addEventListener("input", () => {
      currentLyrics[index] = { ...currentLyrics[index], text: text.value };
      lyricText.textContent = text.value;
    });
    editButton.addEventListener("click", () => {
      const editing = !text.hidden;
      text.hidden = editing;
      lyricText.hidden = !editing;
      editButton.textContent = editing ? t("edit_lyric") : t("finish_editing");
      if (!editing) text.focus();
    });
    card.append(meta, chordLine, lyricText, editButton, text);
    return card;
  }));
}

function chordEventsForLyrics(line) {
  const events = currentAnalysis.chords
    .filter((event) => event.end > line.start && event.start < line.end)
    .map((event) => ({
      ...event,
      start: Math.max(event.start, line.start),
      end: Math.min(event.end, line.end),
    }));
  return events.filter((event, index) => (
    index === 0 || event.chord !== events[index - 1].chord
  ));
}

function createChordButton(chord, shape) {
  const button = document.createElement("button");
  button.className = "lyric-chord";
  button.type = "button";
  button.textContent = chord;
  button.setAttribute("aria-label", `${chord} ${t("chord_diagram_title")}: ${shape}`);
  const tooltip = document.createElement("span");
  tooltip.className = "chord-tooltip";
  tooltip.setAttribute("role", "tooltip");
  const heading = document.createElement("strong");
  heading.textContent = `${chord} (${shape} ${t("shape_label")})`;
  tooltip.append(heading);
  const diagram = createChordDiagram(shape);
  if (diagram) {
    tooltip.append(diagram);
    const fingering = document.createElement("span");
    fingering.className = "chord-fingering";
    const capoPosition = Number(capoSelect.value);
    const capo = capoPosition ? `${t("capo_position")} ${capoPosition}` : t("no_capo");
    fingering.textContent = t("chord_shape_info", { shape, capo });
    tooltip.append(fingering);
  } else {
    const unavailable = document.createElement("span");
    unavailable.className = "chord-fingering";
    unavailable.textContent = t("unavailable_chord_shape");
    tooltip.append(unavailable);
  }
  button.append(tooltip);
  return button;
}

const guitarChordShapes = {
  C: { frets: ["x", 3, 2, 0, 1, 0], fingers: ["", 3, 2, "", 1, ""], base: 1 },
  "C#": { frets: ["x", 4, 6, 6, 6, 4], fingers: ["", 1, 3, 3, 3, 1], base: 4 },
  D: { frets: ["x", "x", 0, 2, 3, 2], fingers: ["", "", "", 1, 3, 2], base: 1 },
  "D#": { frets: ["x", 6, 8, 8, 8, 6], fingers: ["", 1, 3, 3, 3, 1], base: 6 },
  E: { frets: [0, 2, 2, 1, 0, 0], fingers: ["", 2, 3, 1, "", ""], base: 1 },
  F: { frets: [1, 3, 3, 2, 1, 1], fingers: [1, 3, 4, 2, 1, 1], base: 1 },
  "F#": { frets: [2, 4, 4, 3, 2, 2], fingers: [1, 3, 4, 2, 1, 1], base: 2 },
  G: { frets: [3, 2, 0, 0, 0, 3], fingers: [2, 1, "", "", "", 3], base: 1 },
  "G#": { frets: [4, 6, 6, 5, 4, 4], fingers: [1, 3, 4, 2, 1, 1], base: 4 },
  A: { frets: ["x", 0, 2, 2, 2, 0], fingers: ["", "", 1, 2, 3, ""], base: 1 },
  "A#": { frets: ["x", 1, 3, 3, 3, 1], fingers: ["", 1, 3, 3, 3, 1], base: 1 },
  B: { frets: ["x", 2, 4, 4, 4, 2], fingers: ["", 1, 3, 3, 3, 1], base: 2 },
  Cm: { frets: ["x", 3, 5, 5, 4, 3], fingers: ["", 1, 3, 4, 2, 1], base: 3 },
  "C#m": { frets: ["x", 4, 6, 6, 5, 4], fingers: ["", 1, 3, 4, 2, 1], base: 4 },
  Dm: { frets: ["x", "x", 0, 2, 3, 1], fingers: ["", "", "", 2, 3, 1], base: 1 },
  "D#m": { frets: ["x", 6, 8, 8, 7, 6], fingers: ["", 1, 3, 4, 2, 1], base: 6 },
  Em: { frets: [0, 2, 2, 0, 0, 0], fingers: ["", 2, 3, "", "", ""], base: 1 },
  Fm: { frets: [1, 3, 3, 1, 1, 1], fingers: [1, 3, 4, 1, 1, 1], base: 1 },
  "F#m": { frets: [2, 4, 4, 2, 2, 2], fingers: [1, 3, 4, 1, 1, 1], base: 2 },
  Gm: { frets: [3, 5, 5, 3, 3, 3], fingers: [1, 3, 4, 1, 1, 1], base: 3 },
  "G#m": { frets: [4, 6, 6, 4, 4, 4], fingers: [1, 3, 4, 1, 1, 1], base: 4 },
  Am: { frets: ["x", 0, 2, 2, 1, 0], fingers: ["", "", 2, 3, 1, ""], base: 1 },
  "A#m": { frets: ["x", 1, 3, 3, 2, 1], fingers: ["", 1, 3, 4, 2, 1], base: 1 },
  Bm: { frets: ["x", 2, 4, 4, 3, 2], fingers: ["", 1, 3, 4, 2, 1], base: 2 },
};

function createChordDiagram(chord) {
  const shape = guitarChordShapes[chord];
  if (!shape) return null;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.classList.add("chord-diagram");
  svg.setAttribute("viewBox", "0 0 124 126");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `${chord} ${t("chord_diagram_title")}`);
  const svgElement = (name, attributes) => {
    const element = document.createElementNS("http://www.w3.org/2000/svg", name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    return element;
  };
  const stringXs = [24, 39, 54, 69, 84, 99];
  const fretYs = [22, 42, 62, 82, 102, 122];
  const displayedStart = shape.base;
  svg.append(svgElement("line", {
    x1: 17, y1: fretYs[0], x2: 106, y2: fretYs[0],
    class: displayedStart === 1 ? "chord-nut" : "chord-fret",
  }));
  for (const x of stringXs) {
    svg.append(svgElement("line", { x1: x, y1: fretYs[0], x2: x, y2: fretYs[5], class: "chord-string" }));
  }
  for (let fret = 1; fret <= 5; fret += 1) {
    svg.append(svgElement("line", {
      x1: 17, y1: fretYs[fret], x2: 106, y2: fretYs[fret], class: "chord-fret",
    }));
  }
  if (displayedStart > 1) {
    const label = svgElement("text", { x: 2, y: 35, class: "chord-fret-number" });
    label.textContent = String(displayedStart);
    svg.append(label);
  }
  shape.frets.forEach((fret, index) => {
    const x = stringXs[index];
    if (fret === "x" || fret === 0) {
      const marker = svgElement("text", { x, y: 15, class: "chord-open-marker" });
      marker.textContent = fret === "x" ? "×" : "○";
      svg.append(marker);
      return;
    }
    const y = fretYs[fret - displayedStart] + 10;
    svg.append(svgElement("circle", { cx: x, cy: y, r: 5.5, class: "chord-finger-dot" }));
    if (shape.fingers[index]) {
      const finger = svgElement("text", { x, y: y + 2.5, class: "chord-finger-number" });
      finger.textContent = String(shape.fingers[index]);
      svg.append(finger);
    }
  });
  return svg;
}

function setTranscribing(loading) {
  transcribeButton.disabled = loading || !currentAnalysis;
  transcribeButton.classList.toggle("loading", loading);
  transcribeButton.querySelector(".button-label").textContent = loading
    ? t("transcribing_label")
    : t("transcribe_button");
}

transposedAudioButton.addEventListener("click", async () => {
  const file = fileInput.files?.[0];
  if (!file || !currentAnalysis) return;
  const formData = new FormData();
  formData.append("audio", file);
  formData.append("semitones", transposeSelect.value);
  transposedAudioButton.disabled = true;
  transposedAudioButton.querySelector("[data-i18n]").textContent = t("transposed_generating");
  errorMessage.hidden = true;
  try {
    const response = await fetch("/api/transpose-audio", { method: "POST", body: formData });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || t("transposed_error"));
    }
    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = response.headers.get("content-disposition")?.match(/filename="?([^";]+)"?/)?.[1] || "transposed.wav";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000);
  } catch (error) {
    showError(error instanceof Error ? localizeError(error.message) : t("transposed_error"));
  } finally {
    transposedAudioButton.disabled = false;
    renderTransposition();
  }
});

function currentOriginalKey() {
  if (!currentAnalysis) return null;
  return originalKeySelect.value === "auto"
    ? currentAnalysis.estimated_key
    : originalKeySelect.value;
}

function getOriginalKeyCorrection(estimatedKey, selectedKey) {
  if (!estimatedKey || !selectedKey || selectedKey === "auto") return 0;
  const estimatedPitch = notePitches.get(estimatedKey.replace(/m$/, ""));
  const selectedPitch = notePitches.get(selectedKey.replace(/m$/, ""));
  if (estimatedPitch == null || selectedPitch == null) return 0;
  let correction = (selectedPitch - estimatedPitch + 12) % 12;
  if (correction > 6) correction -= 12;
  return correction;
}

function transposedChord(chord) {
  const correction = currentAnalysis
    ? getOriginalKeyCorrection(currentAnalysis.estimated_key, currentOriginalKey())
    : 0;
  return transposeChord(chord, correction + Number(transposeSelect.value));
}

function transposeChord(chord, semitones) {
  if (chord === "N.C." || !semitones) return chord;
  const match = /^([A-G])([#b]?)(.*)$/.exec(chord);
  if (!match) return chord;
  const pitch = notePitches.get(`${match[1]}${match[2]}`);
  if (pitch == null) return chord;
  return `${noteNames[(pitch + semitones + 120) % 12]}${match[3]}`;
}

function transposeKey(key, semitones) {
  if (!key) return null;
  const match = /^([A-G])([#b]?)(m?)$/.exec(key);
  if (!match) return key;
  const pitch = notePitches.get(`${match[1]}${match[2]}`);
  if (pitch == null) return key;
  return `${noteNames[(pitch + semitones + 120) % 12]}${match[3]}`;
}

function deduplicate(chords) {
  return chords.filter((chord, index) => index === 0 || chord !== chords[index - 1]);
}

function confidenceClass(value) {
  if (value >= 0.75) return "high";
  if (value >= 0.5) return "medium";
  return "low";
}

function localizeError(message) {
  if (currentLanguage === "en" && /[\u4e00-\u9fff]/.test(message)) {
    return t("server_error", { message });
  }
  return message;
}

function formatTime(seconds) {
  const tenths = Math.max(0, Math.round(seconds * 10));
  const minutes = Math.floor(tenths / 600);
  const secondsPart = Math.floor((tenths % 600) / 10);
  const decimal = tenths % 10;
  return `${String(minutes).padStart(2, "0")}:${String(secondsPart).padStart(2, "0")}.${decimal}`;
}

function formatNumber(value) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function setLoading(loading) {
  analyzeButton.disabled = loading;
  analyzeButton.classList.toggle("loading", loading);
  analyzeButton.querySelector(".button-label").textContent = loading ? t("analyzing_label") : t("analyze_song");
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

window.addEventListener("beforeunload", () => {
  if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
});

for (const select of [originalKeySelect, transposeSelect, capoSelect]) {
  select.addEventListener("change", renderTransposition);
}
