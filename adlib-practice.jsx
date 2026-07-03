import React, { useState, useEffect, useCallback, useRef } from "react";
import * as Tone from "tone";

// ---------- theory data ----------

const SCALES = {
  ionian: { intervals: [0, 2, 4, 5, 7, 9, 11], ja: "アイオニアン" },
  dorian: { intervals: [0, 2, 3, 5, 7, 9, 10], ja: "ドリアン" },
  phrygian: { intervals: [0, 1, 3, 5, 7, 8, 10], ja: "フリジアン" },
  lydian: { intervals: [0, 2, 4, 6, 7, 9, 11], ja: "リディアン" },
  mixolydian: { intervals: [0, 2, 4, 5, 7, 9, 10], ja: "ミクソリディアン" },
  aeolian: { intervals: [0, 2, 3, 5, 7, 8, 10], ja: "エオリアン (Nマイナー)" },
  locrian: { intervals: [0, 1, 3, 5, 6, 8, 10], ja: "ロクリアン" },
  harmonicMinor: { intervals: [0, 2, 3, 5, 7, 8, 11], ja: "ハーモニックマイナー" },
  melodicMinor: { intervals: [0, 2, 3, 5, 7, 9, 11], ja: "メロディックマイナー" },
  locrianNat2: { intervals: [0, 2, 3, 5, 6, 8, 10], ja: "ロクリアン♮2" },
  altered: { intervals: [0, 1, 3, 4, 6, 8, 10], ja: "オルタード" },
  lydianDominant: { intervals: [0, 2, 4, 6, 7, 9, 10], ja: "リディアン7th" },
  wholeHalfDim: { intervals: [0, 2, 3, 5, 6, 8, 9, 11], ja: "コンビネーションディミニッシュ(W-H)" },
};

const CHORD_SUFFIX = {
  maj7: "maj7",
  m7: "m7",
  7: "7",
  m7b5: "m7♭5",
  dim7: "°7",
  mMaj7: "m(maj7)",
};

// offsets are semitones above the chosen key's tonic
const ENTRIES = [
  { id: "I", roman: "Ⅰ△7", chordRootOffset: 0, chordType: "maj7", scaleRootOffset: 0, scaleId: "ionian", category: "diatonic" },
  { id: "ii", roman: "ⅱm7", chordRootOffset: 2, chordType: "m7", scaleRootOffset: 2, scaleId: "dorian", category: "diatonic" },
  { id: "iii", roman: "ⅲm7", chordRootOffset: 4, chordType: "m7", scaleRootOffset: 4, scaleId: "phrygian", category: "diatonic" },
  { id: "IV", roman: "Ⅳ△7", chordRootOffset: 5, chordType: "maj7", scaleRootOffset: 5, scaleId: "lydian", category: "diatonic" },
  { id: "V", roman: "Ⅴ7", chordRootOffset: 7, chordType: "7", scaleRootOffset: 7, scaleId: "mixolydian", category: "diatonic" },
  { id: "vi", roman: "ⅵm7", chordRootOffset: 9, chordType: "m7", scaleRootOffset: 9, scaleId: "aeolian", category: "diatonic" },
  { id: "vii", roman: "ⅶø7", chordRootOffset: 11, chordType: "m7b5", scaleRootOffset: 11, scaleId: "locrian", category: "diatonic" },

  { id: "V7ii", roman: "Ⅴ7/ⅱ", chordRootOffset: 9, chordType: "7", scaleRootOffset: 9, scaleId: "mixolydian", category: "secondary" },
  { id: "V7iii", roman: "Ⅴ7/ⅲ", chordRootOffset: 11, chordType: "7", scaleRootOffset: 11, scaleId: "mixolydian", category: "secondary" },
  { id: "V7IV", roman: "Ⅴ7/Ⅳ (=Ⅰ7)", chordRootOffset: 0, chordType: "7", scaleRootOffset: 0, scaleId: "mixolydian", category: "secondary" },
  { id: "V7V", roman: "Ⅴ7/Ⅴ", chordRootOffset: 2, chordType: "7", scaleRootOffset: 2, scaleId: "mixolydian", category: "secondary" },
  { id: "V7vi", roman: "Ⅴ7/ⅵ", chordRootOffset: 4, chordType: "7", scaleRootOffset: 9, scaleId: "harmonicMinor", category: "secondary" },

  { id: "subV", roman: "sub Ⅴ7 (裏コード)", chordRootOffset: 1, chordType: "7", scaleRootOffset: 1, scaleId: "lydianDominant", category: "subs" },
  { id: "subV_ii", roman: "sub Ⅴ7/ⅱ (裏コード)", chordRootOffset: 3, chordType: "7", scaleRootOffset: 3, scaleId: "lydianDominant", category: "subs" },
  { id: "vii_dim7", roman: "ⅶ°7 (パッシング)", chordRootOffset: 11, chordType: "dim7", scaleRootOffset: 11, scaleId: "wholeHalfDim", category: "subs" },

  { id: "iiø_minor", roman: "ⅱø7 (borrowed)", chordRootOffset: 2, chordType: "m7b5", scaleRootOffset: 2, scaleId: "locrianNat2", category: "minorii" },
  { id: "V7alt_minor", roman: "Ⅴ7alt (borrowed)", chordRootOffset: 7, chordType: "7", scaleRootOffset: 7, scaleId: "altered", category: "minorii" },
  { id: "i_mMaj7", roman: "ⅰm(maj7) (tonic minor)", chordRootOffset: 0, chordType: "mMaj7", scaleRootOffset: 0, scaleId: "melodicMinor", category: "minorii" },
];

const KEYS = [
  { name: "C", pc: 0, flats: false },
  { name: "G", pc: 7, flats: false },
  { name: "D", pc: 2, flats: false },
  { name: "A", pc: 9, flats: false },
  { name: "E", pc: 4, flats: false },
  { name: "B", pc: 11, flats: false },
  { name: "F#", pc: 6, flats: false },
  { name: "F", pc: 5, flats: true },
  { name: "B♭", pc: 10, flats: true },
  { name: "E♭", pc: 3, flats: true },
  { name: "A♭", pc: 8, flats: true },
  { name: "D♭", pc: 1, flats: true },
];

const SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLAT_NAMES = ["C", "D♭", "D", "E♭", "E", "F", "G♭", "G", "A♭", "A", "B♭", "B"];

function noteName(pc, useFlats) {
  const arr = useFlats ? FLAT_NAMES : SHARP_NAMES;
  return arr[((pc % 12) + 12) % 12];
}

const CATEGORY_META = {
  diatonic: { label: "ダイアトニック", color: "#2F5C7A", bg: "#D9E6EC" },
  secondary: { label: "セカンダリードミナント", color: "#B5651D", bg: "#F1DDB8" },
  subs: { label: "代理・ディミニッシュ", color: "#8A3B3B", bg: "#EACFCB" },
  minorii: { label: "マイナーⅱ-Ⅴ-ⅰ (借用)", color: "#5B4B8A", bg: "#DBD3EC" },
};

const COLORS = {
  paper: "#F5EFDD",
  paperEdge: "#E3D9BC",
  ink: "#20242B",
  inkSoft: "#5A6070",
};

// ---------- component ----------

export default function App() {
  const [keyIndex, setKeyIndex] = useState(0);
  const [categories, setCategories] = useState({
    diatonic: true,
    secondary: true,
    subs: false,
    minorii: false,
  });

  const [currentEntry, setCurrentEntry] = useState(ENTRIES[0]);
  const lastIdRef = useRef(ENTRIES[0].id);

  const [bpm, setBpm] = useState(96);
  const [beatsPerBar, setBeatsPerBar] = useState(4);
  const [barsPerChord, setBarsPerChord] = useState(2);
  const [autoAdvance, setAutoAdvance] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentBeat, setCurrentBeat] = useState(0);

  const tapTimesRef = useRef([]);

  const pickRandom = useCallback(() => {
    const pool = ENTRIES.filter((e) => categories[e.category]);
    const source = pool.length > 0 ? pool : ENTRIES;
    let idx;
    do {
      idx = Math.floor(Math.random() * source.length);
    } while (source.length > 1 && source[idx].id === lastIdRef.current);
    lastIdRef.current = source[idx].id;
    setCurrentEntry(source[idx]);
  }, [categories]);

  // live bpm update
  useEffect(() => {
    Tone.Transport.bpm.value = bpm;
  }, [bpm]);

  useEffect(() => {
    Tone.Transport.timeSignature = beatsPerBar;
  }, [beatsPerBar]);

  // click loop
  useEffect(() => {
    if (!isPlaying) return;
    Tone.Transport.bpm.value = bpm;
    Tone.Transport.timeSignature = beatsPerBar;

    const hi = new Tone.Synth({
      oscillator: { type: "triangle" },
      envelope: { attack: 0.001, decay: 0.04, sustain: 0, release: 0.01 },
    }).toDestination();
    const lo = new Tone.Synth({
      oscillator: { type: "triangle" },
      envelope: { attack: 0.001, decay: 0.06, sustain: 0, release: 0.01 },
    }).toDestination();
    hi.volume.value = -8;
    lo.volume.value = -4;

    let beat = 0;
    const loop = new Tone.Loop((time) => {
      const beatInBar = beat % beatsPerBar;
      const down = beatInBar === 0;
      (down ? lo : hi).triggerAttackRelease(down ? "C5" : "G5", "32n", time);
      Tone.Draw.schedule(() => setCurrentBeat(beatInBar), time);
      beat++;
    }, "4n").start(0);

    Tone.Transport.start();

    return () => {
      loop.dispose();
      hi.dispose();
      lo.dispose();
      Tone.Transport.stop();
      Tone.Transport.cancel();
      setCurrentBeat(0);
    };
  }, [isPlaying, beatsPerBar]);

  // auto-advance loop
  useEffect(() => {
    if (!isPlaying || !autoAdvance) return;
    const chordLoop = new Tone.Loop((time) => {
      Tone.Draw.schedule(() => pickRandom(), time);
    }, `${barsPerChord}m`).start(0);
    return () => chordLoop.dispose();
  }, [isPlaying, autoAdvance, barsPerChord, beatsPerBar, pickRandom]);

  const togglePlay = async () => {
    if (!isPlaying) {
      await Tone.start();
      setIsPlaying(true);
    } else {
      setIsPlaying(false);
    }
  };

  const handleTap = () => {
    const now = performance.now();
    const arr = tapTimesRef.current.filter((t) => now - t < 2500);
    arr.push(now);
    tapTimesRef.current = arr.slice(-5);
    if (arr.length >= 2) {
      const intervals = [];
      for (let i = 1; i < arr.length; i++) intervals.push(arr[i] - arr[i - 1]);
      const avg = intervals.reduce((a, b) => a + b, 0) / intervals.length;
      const newBpm = Math.round(60000 / avg);
      if (newBpm >= 30 && newBpm <= 300) setBpm(newBpm);
    }
  };

  const key = KEYS[keyIndex];
  const chordRootPc = (key.pc + currentEntry.chordRootOffset) % 12;
  const chordRootName = noteName(chordRootPc, key.flats);
  const chordLabel = chordRootName + CHORD_SUFFIX[currentEntry.chordType];

  const scale = SCALES[currentEntry.scaleId];
  const scaleRootPc = (key.pc + currentEntry.scaleRootOffset) % 12;
  const scaleRootName = noteName(scaleRootPc, key.flats);
  const scaleNotes = scale.intervals.map((iv) => noteName(scaleRootPc + iv, key.flats)).join("  ");
  const meta = CATEGORY_META[currentEntry.category];

  const toggleCategory = (cat) =>
    setCategories((c) => ({ ...c, [cat]: !c[cat] }));

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4"
      style={{ background: "#EDE7D3", fontFamily: "Georgia, 'Times New Roman', serif" }}
    >
      <div
        className="w-full max-w-md rounded-sm shadow-xl overflow-hidden"
        style={{ background: COLORS.paper, border: `1px solid ${COLORS.paperEdge}` }}
      >
        {/* header, staff-line texture */}
        <div
          className="px-5 pt-5 pb-4 flex items-center justify-between"
          style={{
            backgroundImage:
              "repeating-linear-gradient(to bottom, transparent 0px, transparent 7px, rgba(32,36,43,0.10) 7px, rgba(32,36,43,0.10) 8px)",
            backgroundPosition: "0 18px",
            backgroundSize: "100% 40px",
            backgroundRepeat: "no-repeat",
            borderBottom: `1px solid ${COLORS.paperEdge}`,
          }}
        >
          <div>
            <div className="text-[10px] tracking-[0.2em] uppercase" style={{ color: COLORS.inkSoft }}>
              Ad-lib Practice
            </div>
            <div className="text-xl font-bold flex items-center gap-1" style={{ color: COLORS.ink }}>
              <span className="text-2xl leading-none">𝄞</span> コード & スケール
            </div>
          </div>
          <select
            value={keyIndex}
            onChange={(e) => setKeyIndex(Number(e.target.value))}
            className="text-sm rounded px-2 py-1 border font-sans"
            style={{ borderColor: COLORS.paperEdge, background: "white", color: COLORS.ink }}
          >
            {KEYS.map((k, i) => (
              <option key={k.name} value={i}>
                Key: {k.name}
              </option>
            ))}
          </select>
        </div>

        {/* flash card */}
        <div className="px-5 py-6 text-center" style={{ background: meta.bg }}>
          <div
            className="inline-block text-xs font-sans font-semibold px-2 py-0.5 rounded-sm mb-3"
            style={{ background: "white", color: meta.color, border: `1px solid ${meta.color}` }}
          >
            {currentEntry.roman} ・ {meta.label}
          </div>
          <div className="text-6xl font-bold tracking-tight" style={{ color: COLORS.ink }}>
            {chordLabel}
          </div>
          <div className="mt-2 text-lg font-sans" style={{ color: meta.color }}>
            {scaleRootName} {scale.ja}
          </div>
          <div className="mt-1 text-sm font-mono tracking-wide" style={{ color: COLORS.inkSoft }}>
            {scaleNotes}
          </div>
        </div>

        {/* metronome strip */}
        <div className="px-5 py-4 font-sans" style={{ background: COLORS.ink }}>
          <div className="flex items-center justify-center gap-2 mb-3">
            {Array.from({ length: beatsPerBar }).map((_, i) => (
              <div
                key={i}
                className="w-3 h-3 rounded-full transition-colors"
                style={{
                  background:
                    isPlaying && i === currentBeat
                      ? i === 0
                        ? "#E4A93B"
                        : "#EDEBE2"
                      : "rgba(255,255,255,0.18)",
                }}
              />
            ))}
          </div>

          <div className="flex items-center justify-center gap-3 mb-3">
            <button
              onClick={() => setBpm((b) => Math.max(30, b - 1))}
              className="w-7 h-7 rounded-full text-white/80 border border-white/20 text-sm"
            >
              −
            </button>
            <div className="font-mono text-3xl text-white w-24 text-center tabular-nums">{bpm}</div>
            <button
              onClick={() => setBpm((b) => Math.min(300, b + 1))}
              className="w-7 h-7 rounded-full text-white/80 border border-white/20 text-sm"
            >
              ＋
            </button>
          </div>
          <input
            type="range"
            min={30}
            max={300}
            value={bpm}
            onChange={(e) => setBpm(Number(e.target.value))}
            className="w-full mb-3"
          />

          <div className="grid grid-cols-3 gap-2 text-white/80 text-xs mb-3">
            <label className="flex flex-col gap-1">
              拍子
              <select
                value={beatsPerBar}
                onChange={(e) => setBeatsPerBar(Number(e.target.value))}
                className="text-black rounded px-1 py-0.5"
              >
                {[2, 3, 4, 5, 6].map((n) => (
                  <option key={n} value={n}>
                    {n}/4
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              小節/コード
              <select
                value={barsPerChord}
                onChange={(e) => setBarsPerChord(Number(e.target.value))}
                className="text-black rounded px-1 py-0.5"
              >
                {[1, 2, 4, 8].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                checked={autoAdvance}
                onChange={() => setAutoAdvance((v) => !v)}
              />
              自動進行
            </label>
          </div>

          <div className="flex gap-2">
            <button
              onClick={togglePlay}
              className="flex-1 rounded-sm py-2 font-semibold text-sm"
              style={{ background: isPlaying ? "#8A3B3B" : "#E4A93B", color: COLORS.ink }}
            >
              {isPlaying ? "■ 停止" : "▶ 開始"}
            </button>
            <button
              onClick={handleTap}
              className="rounded-sm px-3 py-2 text-sm text-white border border-white/25"
            >
              TAP
            </button>
            <button
              onClick={pickRandom}
              className="rounded-sm px-3 py-2 text-sm text-white border border-white/25"
            >
              次のコード
            </button>
          </div>
        </div>

        {/* category filters */}
        <div className="px-5 py-4 font-sans flex flex-wrap gap-2 text-xs" style={{ background: COLORS.paper }}>
          {Object.entries(CATEGORY_META).map(([key2, m]) => (
            <button
              key={key2}
              onClick={() => toggleCategory(key2)}
              className="px-2 py-1 rounded-sm border font-semibold"
              style={{
                borderColor: m.color,
                color: categories[key2] ? "white" : m.color,
                background: categories[key2] ? m.color : "white",
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
