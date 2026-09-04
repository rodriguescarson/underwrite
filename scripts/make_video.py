"""Fallback demo video: deck.pdf pages (+ the live dashboard screenshot) narrated with macOS TTS, assembled by ffmpeg.
Usage: python scripts/make_video.py [voice]"""
import re, subprocess, sys
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = ROOT / "build" / "video"
OUT.mkdir(parents=True, exist_ok=True)
voice = sys.argv[1] if len(sys.argv) > 1 else "Daniel"

paras = [p.strip() for p in re.split(r"\n(?=\d+\.\s)", (DOCS / "NARRATION.md").read_text().split("\n", 2)[2]) if p.strip()]
paras = [re.sub(r"^\d+\.\s*", "", p) for p in paras]
doc = pymupdf.open(DOCS / "deck.pdf")
frames = []
for i, page in enumerate(doc):
    img = OUT / f"slide{i+1}.png"
    page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False).save(img)
    frames.append(img)
if (DOCS / "dashboard.jpg").exists() and len(frames) >= 5:
    frames[4] = DOCS / "dashboard.jpg"  # slide 5 = the live session → show the real dashboard
assert len(paras) == len(frames), (len(paras), len(frames))
concat = []
for i, (img, text) in enumerate(zip(frames, paras)):
    aiff = OUT / f"n{i+1}.aiff"; wav = OUT / f"n{i+1}.wav"
    subprocess.run(["say", "-v", voice, "-r", "178", "-o", str(aiff), text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "48000", "-ac", "2", str(wav)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)], capture_output=True, text=True).stdout.strip()) + 0.6
    seg = OUT / f"seg{i+1}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(img), "-i", str(wav), "-t", f"{dur:.2f}", "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=white,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-shortest", str(seg)], check=True)
    concat.append(f"file '{seg}'")
(OUT / "concat.txt").write_text("\n".join(concat) + "\n")
final = DOCS / "underwrite-fallback.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "concat.txt"), "-c", "copy", str(final)], check=True)
d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(final)], capture_output=True, text=True).stdout.strip()
print(f"wrote {final} ({final.stat().st_size//1024} KB), duration {float(d):.0f}s, voice {voice}, {len(frames)} slides")
