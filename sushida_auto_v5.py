"""寿司打 OCR 自動入力 v5 (Windows)

F6: ローマ字表示領域を選択 / F7: OCR確認・プレビュー保存
F8: 開始 / F9: 停止 / F10: 速度切替 / Ctrl+Shift+Q: 終了

v5:
- F10で 安定 / 高速 / 超高速 の入力速度を切替（初期設定は高速）
- キー押下間隔と単語間の待機を短縮。超高速モードはOCR確認回数も減らす
- 末尾iの長押しと必要な場合の再送、記号、OCRエラー復旧などv4の対策を維持

※公式サイトでは外部ツールの使用が禁止されています。
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
import io
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk

import keyboard
import mss
from PIL import Image, ImageOps
import pyautogui

# キーの押下時間・文字間の待ち時間（秒）。
# 設定上の速度の目安は 1/(key_hold + key_gap) 文字/秒です。
@dataclass(frozen=True)
class SpeedMode:
    name: str
    key_hold: float
    key_gap: float
    i_hold: float
    last_i_hold: float
    last_i_before: float
    last_i_after: float
    after_word: float
    confirmations: int
    ocr_wait: float


SPEED_MODES = (
    SpeedMode("安定",   0.020, 0.020, 0.055, 0.100, 0.045, 0.065, 0.120, 2, 0.035),
    SpeedMode("高速",   0.013, 0.010, 0.028, 0.055, 0.012, 0.025, 0.055, 2, 0.020),
    SpeedMode("超高速", 0.008, 0.006, 0.020, 0.035, 0.008, 0.012, 0.025, 1, 0.005),
)
speed_index = 1  # 初期設定: 高速 / 0=安定, 1=高速, 2=超高速

# 末尾 i 入力後、画面のローマ字が同じままなら再送（1回限り）。
TAIL_I_RETRY_AFTER = 0.48  # 画面切り替え待機。誤入力する場合は0.65程度に増やす
TAIL_I_RECHECK_GAP = 0.07 # 2度のOCRが一致した場合のみ再送
# F6で選択した枠より少し広く撮影。特に右端の細い i が切れないように。
OCR_EXTRA_LEFT = 12
OCR_EXTRA_RIGHT = 38
OCR_EXTRA_TOP = 4
OCR_EXTRA_BOTTOM = 4

# OCRが i を l / 1 と誤読するケースへの対策。
# 「ltu」「lya」など実際に l を使う表示が多ければ False にしてください。
FIX_I_OCR = True

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except (AttributeError, OSError):
    pass

TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if TESSERACT.is_file():
    TESSERACT_CMD = str(TESSERACT)
else:
    TESSERACT_CMD = shutil.which("tesseract")
if not TESSERACT_CMD:
    raise SystemExit("Tesseract OCR が見つかりません。インストールしてください。")

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

run_event = threading.Event()
select_event = threading.Event()
test_event = threading.Event()
speed_toggle_event = threading.Event()
exit_event = threading.Event()
region: tuple[int, int, int, int] | None = None


def select_region() -> tuple[int, int, int, int] | None:
    result = None
    screen = tk.Tk()
    screen.title("寿司打 OCR 範囲選択")
    screen.attributes("-fullscreen", True)
    screen.attributes("-alpha", 0.30)
    screen.attributes("-topmost", True)
    screen.configure(bg="#000000")
    screen.focus_force()

    canvas = tk.Canvas(screen, bg="#111111", highlightthickness=0, cursor="crosshair")
    canvas.pack(fill="both", expand=True)
    canvas.create_text(24, 30, anchor="w", text="ローマ字の1行だけドラッグして囲む（Escで中止）",
                       fill="white", font=("Meiryo", 17, "bold"))
    start = [0, 0]
    rect = [None]

    def mouse_down(e):
        start[0], start[1] = e.x_root, e.y_root
        if rect[0] is not None:
            canvas.delete(rect[0])
        rect[0] = canvas.create_rectangle(e.x, e.y, e.x, e.y,
                                          outline="#00ffdd", width=3)

    def mouse_move(e):
        if rect[0] is not None:
            canvas.coords(rect[0], start[0] - screen.winfo_rootx(),
                          start[1] - screen.winfo_rooty(), e.x, e.y)

    def mouse_up(e):
        nonlocal result
        x, y = min(start[0], e.x_root), min(start[1], e.y_root)
        w, h = abs(e.x_root - start[0]), abs(e.y_root - start[1])
        if w >= 30 and h >= 10:
            result = (x, y, w, h)
            screen.destroy()

    canvas.bind("<ButtonPress-1>", mouse_down)
    canvas.bind("<B1-Motion>", mouse_move)
    canvas.bind("<ButtonRelease-1>", mouse_up)
    screen.bind("<Escape>", lambda e: screen.destroy())
    screen.mainloop()
    return result


def normalize_ocr(raw: str) -> str:
    # 和文記号を含む認識結果を半角にそろえる
    result = raw.lower().replace("！", "!").replace("？", "?").replace("－", "-")
    result = re.sub(r"[^a-z0-9!?-]", "", result)
    if FIX_I_OCR and re.search(r"[a-z]", result):
        # 寿司打の標準ローマ字表示では数字や l はほぼ出ないため、i に補正
        result = re.sub(r"(?<![0-9])1(?![0-9])", "i", result)
        result = result.replace("l", "i")
    return result


def read_romaji(sct, target_region, save_preview=False, debug=False, psm=7):
    x, y, w, h = target_region
    # 選択枠の右端にある i のドットや縦棒が切れてOCRに無視されることを防止。
    # 単に白い余白を足すのではなく、実際のゲーム画面を右に広く撮る。
    left = x - OCR_EXTRA_LEFT
    top = y - OCR_EXTRA_TOP
    grab_w = w + OCR_EXTRA_LEFT + OCR_EXTRA_RIGHT
    grab_h = h + OCR_EXTRA_TOP + OCR_EXTRA_BOTTOM
    shot = sct.grab({"left": left, "top": top, "width": grab_w, "height": grab_h})
    pic = Image.frombytes("RGB", shot.size, shot.rgb)
    gray = ImageOps.grayscale(pic)
    gray = gray.resize((grab_w * 4, grab_h * 4), Image.Resampling.LANCZOS)
    bw = gray.point(lambda v: 0 if v >= 160 else 255)
    # Tesseractが行末の細い文字を無視しにくいよう、四辺に背景色の余白を追加。
    bw = ImageOps.expand(bw, border=(20, 12, 20, 12), fill=255)
    if save_preview:
        bw.save(Path(__file__).with_name("ocr_preview.png"))
    # TesseractにPNGバイト列を直接渡す。Tempフォルダに画像を作らない。
    png = io.BytesIO()
    bw.save(png, format="PNG")
    command = [
        TESSERACT_CMD, "stdin", "stdout", "-l", "eng", "--oem", "3", "--psm", str(psm),
        "-c", "tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!?-",
    ]
    try:
        proc = subprocess.run(
            command, input=png.getvalue(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=5, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("TesseractのOCRが5秒以内に完了しませんでした") from exc
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"Tesseract OCRエラー (code={proc.returncode}): {err[:250]}")
    raw = proc.stdout.decode("utf-8", errors="replace")
    result = normalize_ocr(raw)
    if len(result) > 70:
        result = ""
    if debug:
        return result, raw
    return result


def switch_speed_if_requested():
    """Hotkey callbackから直接ゲーム処理を変更せず、メイン側で切り替える。"""
    global speed_index
    if speed_toggle_event.is_set():
        speed_toggle_event.clear()
        speed_index = (speed_index + 1) % len(SPEED_MODES)
        selected = SPEED_MODES[speed_index]
        print(f"入力速度を『{selected.name}』に切替（F10で再切替）", flush=True)


def send_char(ch: str, final_i: bool = False):
    """キーの押下と解放。設定モードに応じて文字ごとに速度を変える。"""
    mode = SPEED_MODES[speed_index]
    if final_i and ch == "i":
        time.sleep(mode.last_i_before)
    # 記号はShiftとの同時押しで送信。
    target = {"!": "1", "?": "/"}.get(ch, ch)
    shifted = ch in ("!", "?")
    if shifted:
        pyautogui.keyDown("shift")
    try:
        pyautogui.keyDown(target)
        try:
            hold = mode.last_i_hold if final_i and ch == "i" else (mode.i_hold if ch == "i" else mode.key_hold)
            time.sleep(hold)
        finally:
            pyautogui.keyUp(target)
    finally:
        if shifted:
            pyautogui.keyUp("shift")
    time.sleep(mode.last_i_after if final_i and ch == "i" else mode.key_gap)


def send_word(word: str) -> bool:
    """停止指示を文字間で受け付ける。全て送信できた場合のみTrue。"""
    for idx, ch in enumerate(word):
        if not run_event.is_set() or exit_event.is_set():
            return False
        switch_speed_if_requested()
        send_char(ch, final_i=(ch == "i" and idx == len(word) - 1))
    return True


def main():
    global region
    keyboard.add_hotkey("f6", select_event.set)
    keyboard.add_hotkey("f7", test_event.set)
    keyboard.add_hotkey("f8", run_event.set)
    keyboard.add_hotkey("f9", run_event.clear)
    keyboard.add_hotkey("f10", speed_toggle_event.set)
    keyboard.add_hotkey("ctrl+shift+q", exit_event.set)

    print("【寿司打 自動入力 v5：速度切替版】")
    print("F6：領域選択 / F7：OCR確認 / F8：開始 / F9：停止 / F10：速度切替")
    print(f"現在の速度: {SPEED_MODES[speed_index].name}（初期設定：高速）")
    print("Ctrl+Shift+Q：終了 / マウスを画面左上：緊急停止")
    print("事前にブラウザを半角英数入力にし、ローマ字表示をONにしてください。")
    last_sent = ""
    pending = ""
    stable_count = 0
    previously_running = False
    ocr_errors = 0
    # 一度送った末尾 i が未反映だった場合に、同じ問題か確かめて最大1回だけ再送する。
    tail_i_word = ""
    tail_i_due = 0.0
    tail_i_confirm = 0
    last_sent_at = 0.0
    last_missing_i_checked = False
    try:
        with mss.MSS() as sct:
            while not exit_event.is_set():
                switch_speed_if_requested()
                if select_event.is_set():
                    select_event.clear()
                    run_event.clear()
                    picked = select_region()
                    if picked:
                        region = picked
                        last_sent = pending = ""
                        stable_count = 0
                        tail_i_word = ""
                        last_missing_i_checked = False
                        print(f"認識範囲: {region}（右側{OCR_EXTRA_RIGHT}pxも追加認識）。画面をクリックしF8で開始。")
                    continue

                if test_event.is_set():
                    test_event.clear()
                    if region:
                        try:
                            msg, raw = read_romaji(sct, region, save_preview=True, debug=True)
                            print(f"OCR元の文字: {raw!r} / 修正後: {msg!r}（ocr_preview.png 保存）")
                        except Exception as exc:
                            print("OCR失敗:", exc)
                    else:
                        print("先にF6でローマ字の領域を選択してください。")
                    continue

                active = run_event.is_set() and region is not None
                if not active:
                    if previously_running:
                        last_sent = pending = ""
                        stable_count = 0
                        tail_i_word = ""
                        last_missing_i_checked = False
                    previously_running = False
                    time.sleep(0.04)
                    continue
                previously_running = True

                try:
                    word = read_romaji(sct, region)
                    ocr_errors = 0
                except Exception as exc:
                    ocr_errors += 1
                    print(f"OCR失敗（{ocr_errors}/5）: {exc}", flush=True)
                    pending = ""
                    stable_count = 0
                    tail_i_word = ""
                    last_missing_i_checked = False
                    if ocr_errors >= 5:
                        run_event.clear()
                        ocr_errors = 0
                        print("OCRが5回連続で失敗したため自動入力を停止しました。F7で確認し、F8で再開できます。")
                    time.sleep(0.2)
                    continue
                # 完了済みの問題から画面が切り替われば、末尾 i の再送を中止。
                # 同一文字列が残り続け、かつ2度のOCRが同じ場合のみ慎重に再送する。
                if tail_i_word:
                    if word != tail_i_word:
                        tail_i_word = ""
                        tail_i_confirm = 0
                    elif time.monotonic() >= tail_i_due:
                        tail_i_confirm += 1
                        if tail_i_confirm >= 2:
                            if run_event.is_set() and not exit_event.is_set():
                                print(f"末尾 i が反映されていない可能性：i を1回再送 ({tail_i_word})", flush=True)
                                send_char("i", final_i=True)
                            tail_i_word = ""   # この問題では二度と再送しない
                            tail_i_confirm = 0
                        else:
                            time.sleep(TAIL_I_RECHECK_GAP)
                        continue

                # 1文字目から最後まで入力したはずなのにローマ字が変わらない場合、
                # 最後の細い i をOCRが読まず、word が本当は word+'i' だった可能性がある。
                # 誤入力防止のため、別の認識方式で2回続けて末尾 i が確認できたときのみ補完。
                if (word and word == last_sent and not word.endswith("i")
                        and not last_missing_i_checked
                        and time.monotonic() - last_sent_at >= 0.55):
                    last_missing_i_checked = True
                    try:
                        alternative_1 = read_romaji(sct, region, psm=13)
                        time.sleep(0.06)
                        alternative_2 = read_romaji(sct, region, psm=13)
                        if alternative_1 == word + "i" and alternative_2 == word + "i":
                            print(f"OCRが末尾 i を省略した可能性：{word} → {alternative_2}。i のみ補完", flush=True)
                            send_char("i", final_i=True)
                    except Exception as exc:
                        print(f"末尾 i の再認識は失敗（続行します）: {exc}", flush=True)

                if not word or word == last_sent:
                    pending = ""
                    stable_count = 0
                    time.sleep(SPEED_MODES[speed_index].ocr_wait)
                    continue

                if word == pending:
                    stable_count += 1
                else:
                    pending, stable_count = word, 1
                if stable_count < SPEED_MODES[speed_index].confirmations:
                    time.sleep(SPEED_MODES[speed_index].ocr_wait)
                    continue

                print("自動入力:", word, flush=True)
                sent_all = send_word(word)
                if sent_all:
                    last_sent = word
                    last_sent_at = time.monotonic()
                    last_missing_i_checked = False
                    if word.endswith("i"):
                        tail_i_word = word
                        tail_i_due = time.monotonic() + TAIL_I_RETRY_AFTER
                        tail_i_confirm = 0
                    else:
                        tail_i_word = ""
                pending = ""
                stable_count = 0
                time.sleep(SPEED_MODES[speed_index].after_word)
    except pyautogui.FailSafeException:
        print("緊急停止しました。")
    except KeyboardInterrupt:
        print("終了します。")
    finally:
        keyboard.unhook_all_hotkeys()
        print("終了")


if __name__ == "__main__":
    main()
