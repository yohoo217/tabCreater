# Chord Sections

[繁體中文](#繁體中文) · [English](#english)

## 繁體中文

從本機音訊估計和弦時間軸，並把和聲相似的片段標成 A、B、C 等段落。可用命令列或本機網頁操作，並下載易讀 PDF。

> 和弦是訊號處理的估計結果，不等同人工聽寫；目前辨識大調與小調三和弦。段落分組是固定時間片段的和聲相似度，不會自動判斷「主歌／副歌」。

## 安裝

需要 Python 3.10 以上。建議使用虛擬環境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

WAV 可直接使用 libsndfile 讀取。MP3 會先嘗試 libsndfile，再使用 audioread；若系統沒有可用的 MP3 解碼器，請安裝 FFmpeg，或先把音訊轉成 WAV。

## 使用

```bash
chord-sections song.mp3
chord-sections song.wav --output song-chords.md
chord-sections song.mp3 --format csv --output song-chords.csv
chord-sections song.mp3 --format json --output song-chords.json
```

若尚未安裝命令列入口，也可以在專案目錄執行：

```bash
python -m chord_sections song.mp3
```

若要使用本機人聲分離與歌詞辨識，安裝 AI 選用套件：

```bash
python -m pip install -e '.[ai]'
```

調整分析視窗、段落長度及片段相似門檻：

```bash
chord-sections song.wav --window-seconds 1.5 --section-seconds 8 --similarity-threshold 0.88
```

Markdown 報告包含段落摘要及完整和弦時間軸。CSV 每列是一個和弦事件，並附上對應段落；JSON 則保留和弦、信心差距及段落資訊。

## 分析方式與限制

- 以 librosa 讀取單聲道音訊、計算 chroma，再比對 12 個大調與 12 個小調三和弦模板。
- MP3 的 audioread 後端需要系統解碼器（例如 FFmpeg；macOS 也可使用 Core Audio）。
- 和弦信心分數結合模板符合度與第一、第二候選的差距，是啟發式參考，不是統計校準後的機率或辨識準確率。
- 可選擇 HPSS 和聲強調，減少鼓與瞬態聲響干擾；也可切換高解析 CQT 分析。兩者會改變分析方法／耗時，但不保證結果一定更準。
- 拍速會嘗試自動估計，估計到才顯示；目前不推測拍號。CLI 可覆寫 BPM、拍號、和弦分析間隔、小節分段長度與第一拍偏移。
- CLI 以固定秒數切片；網頁會以自動估計的拍速安排和弦分析窗格。段落仍是聲學相似分組，不是正式曲式辨識。
- 不會下載或上傳音訊，也不會自動抓取 YouTube。請只分析你有權使用的音訊。

## 網頁操作與 PDF

此專案提供給使用者下載後在自己的電腦執行，並不是公開音檔上傳網站。音檔、模型快取與分析結果都保留在執行工具的電腦上。若發現問題或有功能建議，請透過 [GitHub 回饋表單](https://github.com/yohoo217/tabCreater/issues/new?template=feedback.yml) 回報。

安裝專案後，在虛擬環境執行：

```bash
chord-sections-ui
```

或：

```bash
python -m chord_sections.web
```

工具會開啟 `http://127.0.0.1:8765`。選取本機音檔後按「轉換歌曲」，工具會依序分離人聲、辨識歌詞，再用伴奏分析和弦；這個自動流程需要安裝 Demucs 與 faster-whisper（`.[ai]`）。若缺少套件或模型處理失敗，介面會顯示錯誤，不會改用原混音假裝完成。辨識語言、模型及進階分析方法可在結果的進階設定調整；歌詞辨識也可在需要時重新執行。主要結果以歌詞搭配和弦呈現；自動估計到 BPM 才會顯示，拍號目前不會推測。拍速、調性、段落及完整和弦時間軸預設收合，可展開查看。可下載只含歌曲標題、歌詞與和弦的簡潔歌譜，或包含段落、時間軸與信心指標的完整分析 PDF。音檔只暫存在本機記憶體／短暫暫存檔，分析後刪除；PDF 結果暫存在服務記憶體，最多保留最近 5 份，重啟服務即清除。服務只綁定本機 `127.0.0.1`。

分析後可校正原調、選擇目標移調（±半音）及 Capo 位置。PDF 會保留原曲和弦、移調後的實際和弦、Capo 指型。計算方式：移調後和弦 = 原曲和弦 + 移調半音；Capo 指型 = 移調後和弦 - Capo 品數。例如原曲 C，升 2 半音後是 D；使用 Capo 2 時彈 C 指型即可。選「原調校正」會依所選主音整體平移辨識和弦，和弦的大／小調品質仍沿用分析結果。

此儲存庫程式碼採 MIT 授權；Demucs、Whisper 等第三方模型權重有各自的授權條款，請依模型來源頁面確認。

若也要移調音訊，選好半音後按「下載移調後 WAV」；系統會另存保持大致原速度的 WAV，不覆寫原檔，也不會改變頁面上的原音播放。這種音高移調可能產生音質瑕疵；來源若是 MP3，輸出 WAV 不會恢復原本已損失的音質。

### 本機人聲分離與歌詞辨識

先依上方指令安裝 `.[ai]`，再重新啟動網頁服務。每次按「轉換歌曲」都會先用 Demucs 分離人聲，接著以 faster-whisper 辨識歌詞，最後從伴奏音軌分析和弦。可在上傳歌曲的「進階分析設定」先指定語言；歌曲主要使用單一語言時，指定正確語言可避免自動偵測錯認，混合多語言則使用自動偵測。辨識出的每段歌詞會附時間範圍，點時間可回聽；前奏、間奏及尾奏等沒有辨識歌詞的長區段仍會顯示和弦。可在進階設定重新辨識或校正文字，儲存後匯出 PDF。

第一次使用時，模型權重會從 Hugging Face 下載並快取在本機：Whisper Base 約 145 MB、Small 約 484 MB；啟用人聲分離時另需 Demucs 模型約 84 MB。推論在本機 CPU 執行，音檔不會上傳；下載模型本身需要網路。首次載入及長音檔辨識可能需要較久。歌唱辨識容易受伴奏、混音及發音影響，請逐段回聽校正。

也可以匯入 `.txt` 或 `.lrc` 歌詞校正文字。LRC 的 `[mm:ss.xx]歌詞` 時間戳會用來對齊各句，多時間戳及 `[offset:毫秒]` 也會解析；超過音檔長度的行不匯入，最後一句結束時間則依相鄰歌詞間隔估計。純文字每行一句，行數不必和辨識結果相同：行數相同時保留原時間，行數不同時把目前歌詞涵蓋範圍平均分配，時間僅為估計，請試播核對後儲存。Whisper 若產生異常重複的長句，系統會保留前兩次重複以抑制明顯的循環幻覺；仍建議回聽校正。

CLI 使用時，若已知拍速或拍號，正確填寫有助於和弦窗格與段落邊界對齊；錯誤設定反而可能降低結果品質。網頁版會嘗試自動估計 BPM，估計不到就不顯示；目前不會推測拍號。延長運算時間本身不會提升準確度；高解析 CQT 或 HPSS 只是可比較的分析方法。信心分數是模型內部的啟發式排序，並未用人工答案校準；要讓它代表可信的錯誤機率，需要有多段人工確認和弦及時間戳的資料，才能做校準與留出測試。

要協助改善／評估結果，最有用的是：高音質、未剪裁的原始音檔；若有，提供純吉他或和聲 stem；至少 30–60 秒人工核對過、包含和弦與起訖時間的片段；以及已知的調性、BPM、拍號。歌詞文字可用來校正辨識內容，但歌詞本身不足以可靠推斷每句實際唱進來的時間。

介面參考了 [Moises 的音訊同步和弦進行](https://moises.ai/features/chord-finder/)、[Chordify 的 PDF 和弦表](https://support.chordify.net/hc/en-us/articles/360002164538-How-to-use-Premium-features)，以及 [Chord AI 的小節／拍號網格](https://www.chordai.net/beat-and-downbeat-tracking/)概念。這是本機簡化版，並非完整移植上述產品功能。

## 開發與測試

```bash
python -m unittest discover -s tests -v
```

---

## English

Chord Sections analyzes local audio to estimate chord timelines and group harmonically similar passages into sections. Use the command line or local web interface, and export a readable PDF.

> Chords are signal-processing estimates, not human transcriptions. The analyzer currently recognizes major and minor triads. Section labels reflect harmonic similarity; they do not identify verse or chorus.

### Requirements and installation

Python 3.10 or newer is required. Create a virtual environment and install the project:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. If your system cannot decode MP3 files, install FFmpeg or convert the audio to WAV.

For local vocal separation and lyric transcription, install the optional AI dependencies:

```bash
python -m pip install '.[ai]'
```

The AI models run locally on CPU. On first use, model weights are downloaded from Hugging Face and cached on your computer: Whisper Base is about 145 MB, Whisper Small about 484 MB, and the Demucs vocal-separation model about 84 MB. Your audio is not uploaded. Singing transcription can omit or mishear words, so review and edit the timed segments.

The source code in this repository is licensed under MIT. Third-party weights such as Demucs and Whisper are subject to their own licenses; check the model pages before using or redistributing them.

### Use the command line

```bash
chord-sections song.mp3
chord-sections song.wav --output song-chords.md
chord-sections song.mp3 --format csv --output song-chords.csv
chord-sections song.mp3 --format json --output song-chords.json
```

If you installed the project in editable mode, you can also run `python -m chord_sections song.mp3`.

### Use the web interface

This project is distributed for people to run on their own computers, not as a public audio-upload website. Audio, model caches, and analysis results remain on the computer running the tool. Report problems or ideas through the [GitHub feedback form](https://github.com/yohoo217/tabCreater/issues/new?template=feedback.yml).

```bash
chord-sections-ui
```

Or run `python -m chord_sections.web`. Open `http://127.0.0.1:8765`, choose an audio file, then select **Convert song**. The app separates vocals, transcribes lyrics, and analyzes chords from the instrumental in that order. This automatic flow requires the Demucs and faster-whisper dependencies (`.[ai]`); missing dependencies or model failures are reported rather than silently falling back to mixed-audio analysis. Language, model, and analysis options are available under advanced settings. The main result is lyrics paired with chords; BPM appears only when estimated, and meter is not currently inferred. Key, sections, and the full chord timeline are collapsed until opened. The interface supports Traditional Chinese and English; use the language button in the header to switch. It can preview chord timestamps, transpose the chart, show capo shapes, and export either a clean lyrics-and-chords sheet or a full analysis PDF. PDF analysis results stay in service memory (up to five reports) and are cleared when the service stops.

By default, conversion separates vocals first, recognizes lyrics using the selected language and model, then analyzes chords from the instrumental. To retry or change options, open advanced lyric settings. Import `.lrc` files to align phrases to `[mm:ss.xx]` timestamps (including multiple timestamps per line and `[offset:milliseconds]`), or import `.txt` with one phrase per line. Matching plain-text line counts preserve recognized timestamps; different counts are assigned evenly across the current lyric time range, so preview and verify before saving. Extreme repeated phrases from speech recognition are reduced to two repetitions to limit looping hallucinations.

### Analysis notes and limitations

- Chord confidence is a heuristic based on template fit and the margin over the next candidate. It is not a calibrated probability or accuracy score.
- Speech recognition can miss quiet sung lines at the start or end. The app disables VAD trimming to preserve song edges; review generated text and timestamps, since this may also retain occasional hallucinated text.
- Harmonic emphasis and high-resolution CQT provide alternative analysis methods; longer processing alone does not guarantee better results.
- The web app attempts to estimate BPM and shows it only when available; it does not infer meter. The CLI supports manual BPM, meter, and beat-offset settings.
- The app does not download or upload audio and does not fetch audio from YouTube. Only analyze audio you have the right to use.
- For MP3 decoding problems, install FFmpeg or convert the file to WAV first.

### Development and tests

```bash
python -m unittest discover -s tests -v
```
