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
- 拍速自動估計；使用者可覆寫 BPM、拍號、和弦分析間隔、小節分段長度與第一拍偏移。
- CLI 以固定秒數切片；網頁介面依所選拍速與拍號換算每段小節長度。段落仍是聲學相似分組，不是正式曲式辨識。
- 不會下載或上傳音訊，也不會自動抓取 YouTube。請只分析你有權使用的音訊。

## 網頁操作與 PDF

安裝專案後，在虛擬環境執行：

```bash
chord-sections-ui
```

或：

```bash
python -m chord_sections.web
```

工具會開啟 `http://127.0.0.1:8765`。選取本機音檔後，可填入已知 BPM 或使用自動估計，並設定拍號、每幾拍估一次和弦、每段幾小節、第一拍偏移及分析解析度。分析完成後可預覽時間軸、點時間跳轉播放並下載 PDF。音檔只暫存在本機記憶體／短暫暫存檔，分析後刪除；PDF 結果暫存在服務記憶體，最多保留最近 5 份，重啟服務即清除。服務只綁定本機 `127.0.0.1`。

分析後可校正原調、選擇目標移調（±半音）及 Capo 位置。PDF 會保留原曲和弦、移調後的實際和弦、Capo 指型。計算方式：移調後和弦 = 原曲和弦 + 移調半音；Capo 指型 = 移調後和弦 - Capo 品數。例如原曲 C，升 2 半音後是 D；使用 Capo 2 時彈 C 指型即可。選「原調校正」會依所選主音整體平移辨識和弦，和弦的大／小調品質仍沿用分析結果。

此儲存庫程式碼採 MIT 授權；Demucs、Whisper 等第三方模型權重有各自的授權條款，請依模型來源頁面確認。

若也要移調音訊，選好半音後按「下載移調後 WAV」；系統會另存保持大致原速度的 WAV，不覆寫原檔，也不會改變頁面上的原音播放。這種音高移調可能產生音質瑕疵；來源若是 MP3，輸出 WAV 不會恢復原本已損失的音質。

### 本機人聲分離與歌詞辨識

先依上方指令安裝 `.[ai]`，再重新啟動網頁服務。分析歌曲後，在「人聲歌詞與和弦對齊」區選擇辨識語言及 Whisper 模型，按下辨識按鈕。可選擇先用 Demucs 分離人聲；辨識出的每段歌詞會附時間範圍，點時間可回聽，修改後按「儲存歌詞到 PDF」，PDF 會列出歌詞、該段時間內的和弦及時間範圍。

第一次使用時，模型權重會從 Hugging Face 下載並快取在本機：Whisper Base 約 145 MB、Small 約 484 MB；啟用人聲分離時另需 Demucs 模型約 84 MB。推論在本機 CPU 執行，音檔不會上傳；下載模型本身需要網路。首次載入及長音檔辨識可能需要較久。歌唱辨識容易受伴奏、混音及發音影響，請逐段回聽校正。

也可以匯入 `.txt` 歌詞校正文字，但必須每一行對應一段已辨識結果；匯入只會替換文字、保留原時間，不會從歌詞文字自動推算演唱時間。若辨識結果沒有分段，請先執行語音辨識。

若拍速或拍號已知，正確填寫有助於讓和弦窗格與段落邊界對齊；錯誤設定反而可能降低結果品質。延長運算時間本身不會提升準確度；高解析 CQT 或 HPSS 只是可比較的分析方法。信心分數是模型內部的啟發式排序，並未用人工答案校準；要讓它代表可信的錯誤機率，需要有多段人工確認和弦及時間戳的資料，才能做校準與留出測試。

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

```bash
chord-sections-ui
```

Or run `python -m chord_sections.web`. Open `http://127.0.0.1:8765`, choose an audio file, set the tempo and meter if known, and analyze it. The interface supports Traditional Chinese and English; use the language button in the header to switch. It can preview chord timestamps, transpose the chart, show capo shapes, recognize lyrics locally, align chords with lyric segments, and export PDFs. PDF analysis results stay in service memory (up to five reports) and are cleared when the service stops.

For lyrics, choose a recognition language and model, optionally separate vocals, then review the recognized timestamps and text. You can import a `.txt` file to replace text one line per recognized segment; importing text does not infer singing timestamps. Save edited lyrics to include them in the PDF.

### Analysis notes and limitations

- Chord confidence is a heuristic based on template fit and the margin over the next candidate. It is not a calibrated probability or accuracy score.
- Harmonic emphasis and high-resolution CQT provide alternative analysis methods; longer processing alone does not guarantee better results.
- Correct BPM, meter, and beat offset can help align analysis windows. Incorrect settings may reduce quality.
- The app does not download or upload audio and does not fetch audio from YouTube. Only analyze audio you have the right to use.
- For MP3 decoding problems, install FFmpeg or convert the file to WAV first.

### Development and tests

```bash
python -m unittest discover -s tests -v
```
