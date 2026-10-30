# Sushi-Da OCR Auto Typer (Python)

[日本語](#日本語) | [English](#english)

An **unofficial** Windows Python project that experiments with OCR-based text recognition and simulated keyboard input. The script reads a selected region of the screen, recognizes a line of Roman letters, and types the detected text using configurable speed settings.

> [!WARNING]
> **The official Sushi-Da website explicitly prohibits the use of external tools/programs for automated or improper typing, as well as tests and experiments outside ordinary typing practice.** This project is not affiliated with or endorsed by Sushi-Da or Neutral. The instructions below describe how to set up and test the software **only in environments where you have permission** (for example, your own typing practice page). **A disclaimer, educational purpose, or public availability of source code does not grant permission to use this tool on the official game.**
>
> Official rules: https://keyx0.net/about.html · Official game: https://sushida.net/

---

<a id="日本語"></a>
## 日本語

### 概要

Pythonで画面上のローマ字をOCR（Tesseract）で読み取り、キーボード入力を自動化する個人開発・技術検証用のスクリプトです。画面の指定範囲をキャプチャし、文字認識・簡易補正を行ってから入力します。

**機能（v5）**

- マウスでOCR対象の1行を範囲選択
- OCR結果の確認、デバッグ画像の保存
- 文字の自動入力と一時停止
- 「安定」「高速」「超高速」の3段階速度切替（初期設定：高速）
- `!` / `?` のキー入力対応、末尾 `i` の取りこぼし軽減
- OCR失敗時の再試行（5回連続失敗で自動停止）

**動作環境**

- Windows 11（Windows 10でも動く可能性がありますが、未検証）
- Python 3.10以上を推奨
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)（英語認識データ `eng` を利用）
- Webブラウザなど、**自分に操作権限があるテスト対象**

### インストール

**1. Pythonを準備**

Pythonが利用できるかPowerShellで確認します。

```powershell
py --version
```

**2. Tesseract OCRをインストール**

WindowsのPowerShellで次を実行します。

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

手動で導入する場合は上記Tesseractのリンクを参照してください。標準のインストール先は `C:\Program Files\Tesseract-OCR\tesseract.exe` です。これ以外の場所にインストールした場合は、`tesseract` コマンドがPATHから見つかるよう設定してください。

**3. 必要なPythonパッケージを導入**

`requirements.txt` がある場合：

```powershell
py -m pip install -r requirements.txt
```

ない場合：

```powershell
py -m pip install keyboard mss Pillow pyautogui
```

> `pytesseract` は **v5では不要** です。v5はTesseractの実行ファイルを直接呼び出します。

### 起動と操作方法

1. `sushida_auto_v5.py` を任意のフォルダに置きます。
2. PowerShellでそのフォルダに移動して、次を実行します。

   ```powershell
   py sushida_auto_v5.py
   ```

3. 使用許可のあるテスト画面で、認識対象のローマ字が**半角英字で1行に表示**されるよう準備します。対象アプリの入力欄にフォーカスを移すと、自動入力がその画面に送られます。
4. **F6** を押し、ローマ字が表示される行をマウスでドラッグして選択します。**Esc** で選択をキャンセルできます。
5. 必要に応じて **F7** で認識結果を確認します。
6. 入力先の画面をクリックしてフォーカスを合わせ、**F8** で自動入力を開始します。
7. **F9** で停止し、**Ctrl + Shift + Q** で終了します。

| キー | 操作 |
|---|---|
| `F6` | OCR認識範囲を選択 |
| `F7` | OCR結果を表示し、`ocr_preview.png` を保存 |
| `F8` | 自動入力を開始・再開 |
| `F9` | 自動入力を停止 |
| `F10` | 速度を切替：高速 → 超高速 → 安定 → 高速… |
| `Ctrl + Shift + Q` | プログラム終了 |
| マウスを画面左上へ | PyAutoGUIの緊急停止機能 |

### 速度設定

- **安定**：文字間の待機を長めに取り、誤入力を抑えやすい設定
- **高速（初期設定）**：速度と安定性のバランスを取った設定
- **超高速**：待機時間を短縮した設定。環境によって入力漏れ・誤入力が増える場合があります

速度の実測値を保証するものではありません。キー送信処理、PC負荷、OCR処理、対象アプリの応答速度により変わります。詳細はスクリプト内の `SPEED_MODES` を確認してください。

### トラブルシューティング

| 症状 | 確認・対処 |
|---|---|
| `Tesseract OCR が見つかりません` | Tesseractのインストール先、PATHを確認。PowerShellを開き直して再実行 |
| OCR結果が空・間違っている | **F6** でローマ字1行のみを選択し直す。**F7** の表示と `ocr_preview.png` を確認 |
| 入力先に文字が入らない | 入力したいアプリの画面やテキスト欄をクリックしてフォーカスを合わせ、IMEを半角英数にする |
| `!` / `?` が入力されない | キーボード配列とShiftキーの動作を確認。v5は `Shift+1` / `Shift+/` を送信 |
| 末尾の `i` が抜ける | 「安定」モードで試し、必要に応じて再認識結果を確認。補正が過剰になる場合もある |
| OCRエラーが連続する | 5回連続で自動停止。**F7** で確認後、問題を直して **F8** で再開 |
| 予期せず別の場所に入力される | まず **F9** で停止。対象アプリにフォーカスがあることを確認 |

### 利用上の注意・免責事項

- **寿司打の公式サイトでは外部ツールによる自動入力、およびタイピング練習以外のテスト・実験は禁止されています。** このリポジトリは公式ゲームでの使用を許可・推奨するものではありません。利用する場合は**対象サービスの利用規約と許諾**を必ず確認してください。
- 学習目的・研究目的であることやREADMEへの注意書きは、サービスの禁止事項を解除しません。
- ランキング操作、第三者のサービスへの過剰なアクセス、他者の迷惑となる行為を推奨しません。
- 自動キー入力は**現在フォーカスのあるウィンドウ**へ送信されます。パスワード欄、チャット欄、業務アプリなどに誤送信しないよう注意してください。
- **F7で保存される `ocr_preview.png` は画面の一部を含む可能性があります。** 公開前に内容を確認し、Gitへコミットしないでください。
- すべての環境での動作・認識精度・入力成功率を保証しません。使用に伴う問題は、適用される法律の範囲で利用者の責任で対応してください。
- 「寿司打」および関連する名称・コンテンツの権利は、それぞれの権利者に帰属します。本プロジェクトは**非公式・非提携**です。ゲーム本体の画像、音源、データは同梱しません。

**公式情報：** [寿司打](https://sushida.net/) / [Neutral「サイトのご利用について」](https://keyx0.net/about.html) / [寿司打 Q&A](https://sushida.net/qa.html)

### ライセンス

**未設定**です。公開前に、作者が希望するライセンスを決め、`LICENSE` ファイルを追加してください。ライセンスを付けずにGitHubで公開しても、第三者に自由な再利用・再配布の権利が自動的に与えられるわけではありません。

---

<a id="english"></a>
## English

### Overview

This is a personal Python experiment in **OCR-driven keyboard automation**. It captures a selected region of the screen, recognizes a single line of Roman characters using Tesseract OCR, applies basic text normalization, and sends simulated keystrokes.

**Features (v5)**

- Select a single-line OCR region by dragging the mouse
- Inspect OCR output and save a debug preview
- Start and stop automatic typing
- Three speed presets: **Stable / Fast / Ultra-fast** (default: Fast)
- Support for `!` and `?`, plus mitigation for missed trailing `i` characters
- Automatic OCR retries; typing stops after five consecutive OCR failures

**Requirements**

- Windows 11 (Windows 10 may work but has not been verified)
- Python 3.10 or newer recommended
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki), including English language data (`eng`)
- A test application or page **you are authorized to automate**

### Installation

**1. Check Python**

```powershell
py --version
```

**2. Install Tesseract OCR**

```powershell
winget install --id UB-Mannheim.TesseractOCR -e
```

Alternatively, install Tesseract manually using the link above. The script checks `C:\Program Files\Tesseract-OCR\tesseract.exe` first, then searches for `tesseract` on your PATH.

**3. Install Python dependencies**

If the repository includes `requirements.txt`:

```powershell
py -m pip install -r requirements.txt
```

Otherwise:

```powershell
py -m pip install keyboard mss Pillow pyautogui
```

> **Note:** v5 does **not** require `pytesseract`. It invokes the Tesseract executable directly.

### How to run

1. Put `sushida_auto_v5.py` in a local folder.
2. Open PowerShell in that folder and run:

   ```powershell
   py sushida_auto_v5.py
   ```

3. Open a **permitted local test page or application** that shows a single line of Roman letters. Make sure the intended input target can receive keyboard input.
4. Press **F6** and drag to select only the line of text. Press **Esc** to cancel selection.
5. Optionally press **F7** to preview the recognized text.
6. Click the intended input window or field to focus it, then press **F8** to start.
7. Press **F9** to stop or **Ctrl + Shift + Q** to quit.

| Key | Action |
|---|---|
| `F6` | Select the OCR region |
| `F7` | Show OCR output and save `ocr_preview.png` |
| `F8` | Start / resume typing |
| `F9` | Stop typing |
| `F10` | Cycle speeds: Fast → Ultra-fast → Stable → Fast… |
| `Ctrl + Shift + Q` | Exit the program |
| Move mouse to the top-left corner | PyAutoGUI emergency fail-safe |

### Speed settings

- **Stable:** Longer delays between keystrokes; may reduce missed input
- **Fast (default):** A balance of speed and reliability
- **Ultra-fast:** Shorter delays; may increase errors on some systems

These are configuration presets, **not guaranteed measured typing speeds**. Real performance depends on the machine, OCR, keyboard injection, and the target application. The settings can be found in `SPEED_MODES` in the script.

### Troubleshooting

| Issue | Suggested check |
|---|---|
| `Tesseract OCR が見つかりません` | Verify installation and PATH; reopen PowerShell if necessary |
| Empty or incorrect OCR output | Re-select only one line with **F6**; inspect **F7** output and `ocr_preview.png` |
| No text appears | Click the intended input field/window and switch the IME to half-width English input |
| `!` or `?` fails | Check the keyboard layout. v5 sends `Shift+1` and `Shift+/` respectively |
| Final `i` is missed | Try Stable mode. OCR correction can also introduce false positives |
| Repeated OCR failures | The program stops after five consecutive failures; inspect with **F7** and restart with **F8** |
| Text appears in the wrong window | Press **F9** immediately and refocus the intended test application |

### Usage restrictions, safety, and disclaimer

- **The official Sushi-Da service prohibits external tools/programs for automated or improper typing, and testing/experimentation unrelated to ordinary typing practice.** This repository does **not** authorize or encourage use against the official game. Only automate targets where you have **explicit permission**.
- Describing the software as educational, experimental, or non-commercial — or including this disclaimer — **does not override third-party terms of service**.
- Do not use this project to manipulate rankings, overload third-party services, or disrupt other users.
- Simulated input goes to the **currently focused window**. Avoid accidental input into passwords, messages, work applications, or other sensitive fields.
- **`ocr_preview.png` may contain a screen capture.** Review it carefully and avoid committing it to a public repository.
- The software is supplied **without a guarantee of compatibility, OCR accuracy, or successful input**. Users are responsible for complying with applicable rules and laws.
- Sushi-Da and associated names/content belong to their respective owners. This project is **unofficial and unaffiliated**. No game assets, audio, or data are included.

**Official references:** [Sushi-Da](https://sushida.net/) / [Neutral website usage rules (Japanese)](https://keyx0.net/about.html) / [Sushi-Da Q&A (Japanese)](https://sushida.net/qa.html)

### License

**Not yet specified.** Before publishing, choose a license and add a `LICENSE` file. Uploading code to GitHub without a license does not automatically permit others to reuse or redistribute it.
