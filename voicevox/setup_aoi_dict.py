# -*- coding: utf-8 -*-
"""アオイ用のVOICEVOX発音辞書を登録(新PCセットアップ用・再実行安全)
前提: VOICEVOXエンジンが起動中(port 50021)
"""
import json, urllib.request, urllib.parse, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:50021"

# (表記, 発音カタカナ, アクセント位置)
ENTRIES = [
    ("Yale", "イェール", 1),
    ("イェール", "イェール", 1),
    ("Wharton", "ウォートン", 1),
    ("Claude", "クロード", 1),
    ("TRAPPIST", "トラピスト", 3),
    ("JWST", "ジェームズウェッブ", 3),
    ("Anthropic", "アンスロピック", 4),
    ("DeepMind", "ディープマインド", 4),
]

def existing_words():
    with urllib.request.urlopen(f"{BASE}/user_dict", timeout=10) as r:
        d = json.load(r)
    return {v["surface"] for v in d.values()}

def add(surface, pron, accent):
    params = {"surface": surface, "pronunciation": pron,
              "accent_type": accent, "word_type": "PROPER_NOUN"}
    url = f"{BASE}/user_dict_word?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        r.read()

def main():
    try:
        have = existing_words()
    except Exception as e:
        print(f"エンジン未起動? {e}")
        sys.exit(1)
    for surface, pron, accent in ENTRIES:
        if surface in have:
            print(f"skip {surface} (登録済み)")
            continue
        try:
            add(surface, pron, accent)
            print(f"OK   {surface} → {pron}")
        except Exception as e:
            print(f"FAIL {surface}: {e}")
    print("辞書登録 完了")

if __name__ == "__main__":
    main()
