# -*- coding: utf-8 -*-
"""
aoi_voice_lab.py — アオイ独自声の探索キット(モーフィング実査 + 音響加工候補の一括生成)
【v2 2026-07-19】波形分析によりB4_aoi_sigを採用版に確定(AOI_VOICE_DECISION.md参照)

使い方(WindowsローカルPC、VOICEVOXエンジン起動済みで):
  Start-Process "$env:LOCALAPPDATA\\Programs\\VOICEVOX\\vv-engine\\run.exe" -WindowStyle Hidden
  py -3.11 -X utf8 -m pip install praat-parselmouth numpy
  py -3.11 -X utf8 aoi_voice_lab.py survey            # ① モーフィング許可ペアの全数調査
  py -3.11 -X utf8 aoi_voice_lab.py generate          # ② 候補声を一括生成 → output/voice_samples/aoi_lab/
  py -3.11 -X utf8 aoi_voice_lab.py process <wav>     # ③ 既存ナレーションWAVにB4を適用

surveyの出力(aoi_lab_survey.json)にひまりと混ぜられる相手がいれば、
generateがモーフィング候補も自動生成する。無ければ加工系候補のみ。
"""
import sys, json, urllib.request, urllib.parse
from pathlib import Path

ENGINE = "http://127.0.0.1:50021"
OUT = Path("output/voice_samples/aoi_lab")

# 現行アオイ公式声(基準)
AOI = dict(speaker=14, pitchScale=-0.05, intonationScale=1.25, speedScale=1.10)

# 比較用の固定テキスト(挨拶+本文。全候補で同一)
TEST_TEXT = (
    "こんにちは、アオイです。今日は、集中力の話です。"
    "集中できないのは、あなたの意志が弱いからではありません。"
    "脳の設計に、逆らっているだけなんです。ここが、本当に、面白いところです。"
)

# 音響加工チェーン候補(parselmouthのChange gender: フォルマント比, ピッチ中央値Hz(0=維持), ピッチレンジ倍率)
# フォルマント比<1.0=声道が長い印象(大人・落ち着き)、>1.0=幼く明るい
FX_VARIANTS = {
    "B1_mature":   dict(formant=0.94, pitch_median=0,   pitch_range=1.0),   # 少し大人・AIらしい静けさ
    "B2_bright":   dict(formant=1.05, pitch_median=0,   pitch_range=1.0),   # 少し明るく個性寄せ
    "B3_old":      dict(formant=0.96, pitch_median=195, pitch_range=0.9),   # 旧案(抑揚が3%減るため非推奨)
    "B4_aoi_sig":  dict(formant=0.95, pitch_median=0,   pitch_range=1.10),  # 【採用】抑揚+22%・強弱保持・音色シフト最大
}


def api(path, params=None, method="GET", body=None):
    url = ENGINE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method, data=body,
                                 headers={"Content-Type": "application/json"} if body else {})
    with urllib.request.urlopen(req, timeout=120) as r:
        ct = r.headers.get("Content-Type", "")
        data = r.read()
    return json.loads(data) if "json" in ct else data


def survey():
    """全話者の permitted_synthesis_morphing と、実際にモーフィング可能なペアを列挙する。"""
    speakers = api("/speakers")
    rows = []
    for sp in speakers:
        feat = (sp.get("supported_features") or {}).get("permitted_synthesis_morphing", "(未設定=許可)")
        for st in sp["styles"]:
            rows.append(dict(name=sp["name"], style=st["name"], id=st["id"], policy=feat))
    print(f"{'id':>4}  {'policy':12} name / style")
    for r in sorted(rows, key=lambda x: x["id"]):
        print(f"{r['id']:>4}  {r['policy']:12} {r['name']} / {r['style']}")

    # ひまり(14)からモーフィングできる相手を実査
    print("\n--- 冥鳴ひまり(id=14) とモーフィング可能な相手(/morphable_targets 実査) ---")
    targets = api("/morphable_targets", method="POST",
                  body=json.dumps([14]).encode())[0]
    ok = [k for k, v in targets.items() if v.get("is_morphable")]
    for sid in ok:
        m = next((r for r in rows if str(r["id"]) == str(sid)), None)
        if m:
            print(f"  id={sid}: {m['name']} / {m['style']}")
    if not ok:
        print("  (なし = ひまりはSELF_ONLY。クロスモーフィング候補は他のALL同士のペアから探す)")

    all_ids = [r for r in rows if r["policy"] == "ALL"]
    Path("aoi_lab_survey.json").write_text(
        json.dumps(dict(all_speakers=rows, himari_morphable=ok, all_policy=all_ids),
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n全データを aoi_lab_survey.json に保存。ALLポリシーのスタイル数: {len(all_ids)}")


def synth(text, speaker, **params):
    q = api("/audio_query", dict(text=text, speaker=speaker), method="POST")
    for k, v in params.items():
        if k in q:
            q[k] = v
    q["prePhonemeLength"] = 0.15
    q["postPhonemeLength"] = 0.35
    q["outputSamplingRate"] = 44100
    return api("/synthesis", dict(speaker=speaker), method="POST",
               body=json.dumps(q).encode())


def synth_morph(text, base, target, rate, **params):
    q = api("/audio_query", dict(text=text, speaker=base), method="POST")
    for k, v in params.items():
        if k in q:
            q[k] = v
    return api("/synthesis_morphing",
               dict(base_speaker=base, target_speaker=target, morph_rate=rate),
               method="POST", body=json.dumps(q).encode())


def apply_fx(wav_bytes_or_path, formant, pitch_median, pitch_range, out_path):
    """Praat 'Change gender' でフォルマント/ピッチを独立加工(=声質の署名づくり)。"""
    import parselmouth
    from parselmouth.praat import call
    if isinstance(wav_bytes_or_path, (bytes, bytearray)):
        tmp = Path("_aoi_tmp_in.wav"); tmp.write_bytes(wav_bytes_or_path)
        src = str(tmp)
    else:
        src = str(wav_bytes_or_path)
    snd = parselmouth.Sound(src)
    mod = call(snd, "Change gender", 75, 600, formant, pitch_median, pitch_range, 1.0)
    mod.save(str(out_path), "WAV")
    return out_path


def generate():
    OUT.mkdir(parents=True, exist_ok=True)
    print("A: 現行アオイ公式声(基準)...")
    base = synth(TEST_TEXT, **AOI)
    (OUT / "A_current_official.wav").write_bytes(base)

    for name, fx in FX_VARIANTS.items():
        print(f"{name}: 加工候補...")
        apply_fx(base, fx["formant"], fx["pitch_median"], fx["pitch_range"], OUT / f"{name}.wav")

    sv = Path("aoi_lab_survey.json")
    if sv.exists():
        data = json.loads(sv.read_text(encoding="utf-8"))
        if data.get("himari_morphable"):
            for sid in data["himari_morphable"][:3]:
                for rate in (0.25, 0.5):
                    print(f"C: ひまり×id{sid} rate={rate}...")
                    w = synth_morph(TEST_TEXT, 14, int(sid), rate,
                                    pitchScale=AOI["pitchScale"],
                                    intonationScale=AOI["intonationScale"],
                                    speedScale=AOI["speedScale"])
                    (OUT / f"C_morph_himari_x{sid}_{int(rate*100)}.wav").write_bytes(w)
        else:
            print("C: ひまりのクロスモーフィングは不許可のためスキップ(B4で独自化する)")
    print(f"\n完了 → {OUT}/  最終確認はB4(採用版)と基準Aの聞き比べでOK")


def process(path):
    """採用チェーン(B4_aoi_sig)を既存ナレーションWAVへ適用する。"""
    fx = FX_VARIANTS["B4_aoi_sig"]
    out = Path(path).with_name(Path(path).stem + "_SIG.wav")
    apply_fx(path, fx["formant"], fx["pitch_median"], fx["pitch_range"], out)
    print(f"→ {out}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "generate"
    if cmd == "survey":
        survey()
    elif cmd == "generate":
        generate()
    elif cmd == "process":
        process(sys.argv[2])
    else:
        print(__doc__)
