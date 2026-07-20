# -*- coding: utf-8 -*-
"""VOICEVOX対話型合成: 【そら】/【玄野】の話者を切り替えて1本のWAVに結合

台本フォーマット:
【そら】
セリフ1行目
セリフ2行目

【玄野】
セリフ...

使い方: py -3.11 voicevox_dialogue.py <台本.md> <出力WAV>
"""
import sys, os, io, wave, re, json, urllib.request, urllib.parse
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:50021"

# 話者設定: (speaker_id, speed, gap_after_sec)
SPEAKERS = {
    "そら": (15, 1.15, 0.50),   # 九州そらあまあま・話速速め・玄野の考える間
    "玄野": (11, 1.10, 0.35),   # 玄野武宏ノーマル・標準
    "そら先生": (15, 1.15, 0.50),
    # 他のキャラ追加はここに
}
DEFAULT = ("玄野", 11, 1.10, 0.35)

def audio_query(text, speaker):
    url = f"{BASE}/audio_query?" + urllib.parse.urlencode({"text": text, "speaker": speaker})
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def synthesis(query, speaker):
    url = f"{BASE}/synthesis?" + urllib.parse.urlencode({"speaker": speaker})
    data = json.dumps(query).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()

def synth(text, speaker, speed):
    q = audio_query(text, speaker)
    q["speedScale"] = speed
    q["prePhonemeLength"] = 0.12
    q["postPhonemeLength"] = 0.20
    return synthesis(q, speaker)

def wav_parts(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getparams(), w.readframes(w.getnframes())

def parse_script(text):
    """Return list of (character, [line, line, ...])"""
    blocks = []
    current = None
    lines = []
    pat = re.compile(r"^【(.+?)】\s*$")
    for raw in text.splitlines():
        line = raw.strip()
        m = pat.match(line)
        if m:
            if current and lines:
                blocks.append((current, lines))
            current = m.group(1)
            lines = []
            continue
        if not line:
            continue
        if line.startswith("#") or line.startswith("---") or line.startswith("**"):
            continue  # metadata line
        if current:
            lines.append(line)
    if current and lines:
        blocks.append((current, lines))
    return blocks

def main():
    src = sys.argv[1]
    out = sys.argv[2]

    text = open(src, encoding="utf-8").read()
    blocks = parse_script(text)
    print(f"対話ブロック数: {len(blocks)}")

    params = None
    frames = bytearray()

    for i, (char, ls) in enumerate(blocks):
        cfg = SPEAKERS.get(char)
        if not cfg:
            print(f"  警告: 未定義キャラ '{char}' → 玄野で代用")
            cfg = SPEAKERS["玄野"]
        speaker, speed, gap = cfg

        # 各行を個別合成して結合(1発話内の自然な間)
        for j, line in enumerate(ls):
            wav = synth(line, speaker, speed)
            pr, fr = wav_parts(wav)
            if params is None:
                params = pr
            frames.extend(fr)
            # 行内は0.1秒、発話終わりは指定gap
            if j < len(ls) - 1:
                frames.extend(b"\x00" * int(pr.framerate * 0.10) * pr.sampwidth * pr.nchannels)

        # 話者切替の間
        frames.extend(b"\x00" * int(params.framerate * gap) * params.sampwidth * params.nchannels)

        if (i + 1) % 5 == 0 or (i + 1) == len(blocks):
            print(f"  [{i+1}/{len(blocks)}] {char}: {ls[0][:20]}...")

    os.makedirs(os.path.dirname(out), exist_ok=True)
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(bytes(frames))
    dur = len(frames) / (params.framerate * params.sampwidth * params.nchannels)
    mb = os.path.getsize(out) / (1024 * 1024)
    print(f"完成: {out} ({dur/60:.1f}分, {mb:.1f}MB)")

if __name__ == "__main__":
    main()
