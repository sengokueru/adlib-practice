# -*- coding: utf-8 -*-
"""VOICEVOX一括音声合成: ナレーションtxt → 章別WAV
使い方: py -3.11 voicevox_batch.py <narration.txt> <出力フォルダ> <speaker_id> [speed]
VOICEVOX(GUI or engine)が起動している必要あり(port 50021)
"""
import json, sys, io, wave, urllib.request, urllib.parse, os
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:50021"

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

def synth_paragraph(text, speaker, speed):
    q = audio_query(text, speaker)
    q["speedScale"] = speed
    q["prePhonemeLength"] = 0.15
    q["postPhonemeLength"] = 0.35
    return synthesis(q, speaker)

def wav_params_and_frames(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return w.getparams(), w.readframes(w.getnframes())

def main():
    src = sys.argv[1]
    outdir = sys.argv[2]
    speaker = int(sys.argv[3])
    speed = float(sys.argv[4]) if len(sys.argv) > 4 else 1.10
    os.makedirs(outdir, exist_ok=True)

    raw = open(src, encoding="utf-8").read()
    # 段落 = 空行区切り
    paragraphs = [p.strip().replace("\n", "") for p in raw.split("\n\n") if p.strip()]
    print(f"段落数: {len(paragraphs)} / speaker={speaker} / speed={speed}")

    params = None
    frames = bytearray()
    gap = None  # 段落間0.45秒の無音

    for i, p in enumerate(paragraphs):
        wav = synth_paragraph(p, speaker, speed)
        pr, fr = wav_params_and_frames(wav)
        if params is None:
            params = pr
            gap = b"\x00" * int(pr.framerate * 0.45) * pr.sampwidth * pr.nchannels
        frames.extend(fr)
        frames.extend(gap)
        print(f"  [{i+1}/{len(paragraphs)}] {p[:24]}... OK")

    name = os.path.splitext(os.path.basename(src))[0] + ".wav"
    out = os.path.join(outdir, name)
    with wave.open(out, "wb") as w:
        w.setparams(params)
        w.writeframes(bytes(frames))
    dur = len(frames) / (params.framerate * params.sampwidth * params.nchannels)
    print(f"完成: {out} ({dur/60:.1f}分)")

if __name__ == "__main__":
    main()
