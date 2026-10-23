#!/usr/bin/env python3
"""Word-level transcripts for the interview footage (faster-whisper, CPU).

  python3 transcribe.py footage/*.MP4            # -> footage/<name>.words.json + <name>.txt
  python3 transcribe.py clip.mp4 --lang hi --model large-v3-turbo

The .txt has one line per segment with source timestamps, for picking hook lines and the story arc.
The .words.json word times are what edl.json captions use (source time).
"""
import argparse, json, os, subprocess
import numpy as np
from faster_whisper import WhisperModel

# biases Hindi output toward Roman-script Hinglish instead of Devanagari
HINGLISH_PROMPT = "Haan bilkul, maine apna business zero se shuru kiya tha. Log bolte the ye nahi chalega, lekin humne mehnat ki."

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='+')
    ap.add_argument('--model', default='large-v3-turbo')
    ap.add_argument('--lang', default=None, help='hi / en; default auto-detect')
    ap.add_argument('--roman', action='store_true', help='prompt for Roman-script Hinglish')
    a = ap.parse_args()
    model = WhisperModel(a.model, device='cpu', compute_type='int8')
    for f in a.files:
        # decode with ffmpeg ourselves (faster-whisper's PyAV path breaks on some av versions)
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                             capture_output=True, check=True).stdout
        audio = np.frombuffer(raw, np.float32).copy()
        segs, info = model.transcribe(audio, language=a.lang, word_timestamps=True, vad_filter=True,
                                      beam_size=5, initial_prompt=HINGLISH_PROMPT if a.roman else None)
        out, lines = [], []
        for s in segs:
            ws = [{'w': w.word.strip(), 't0': round(w.start, 3), 't1': round(w.end, 3), 'p': round(w.probability, 2)}
                  for w in (s.words or []) if w.word.strip()]
            out.append({'t0': round(s.start, 3), 't1': round(s.end, 3), 'text': s.text.strip(), 'words': ws})
            lines.append(f'[{s.start:7.2f} - {s.end:7.2f}] {s.text.strip()}')
        stem = os.path.splitext(f)[0]
        json.dump({'file': os.path.basename(f), 'language': info.language, 'segments': out},
                  open(stem + '.words.json', 'w'), ensure_ascii=False, indent=1)
        open(stem + '.txt', 'w').write('\n'.join(lines) + '\n')
        print(f'{f}: {info.language} ({info.language_probability:.2f}), {len(out)} segments')

if __name__ == '__main__':
    main()
