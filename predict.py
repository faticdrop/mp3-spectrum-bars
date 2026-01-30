import subprocess, tempfile
from pathlib import Path
from typing import List

import requests
from cog import BasePredictor, Input, Path as CogPath

def run(cmd: List[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)

class Predictor(BasePredictor):
    def predict(
        self,
        mp3_urls: List[str] = Input(description="MP3 indirilebilir URL listesi (sıraya göre)"),
        width: int = Input(default=1280),
        height: int = Input(default=720),
        fps: int = Input(default=30),
        bars_mode: str = Input(default="combined", description="combined veya separate"),
    ) -> CogPath:
        if not mp3_urls:
            raise ValueError("mp3_urls boş olamaz")

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            in_dir = td / "in"
            in_dir.mkdir()

            # MP3'leri indir
            for i, url in enumerate(mp3_urls, start=1):
                r = requests.get(url, timeout=300)
                r.raise_for_status()
                (in_dir / f"{i:03d}.mp3").write_bytes(r.content)

            # concat listesi
            list_txt = td / "list.txt"
            with list_txt.open("w", encoding="utf-8") as f:
                for p in sorted(in_dir.glob("*.mp3")):
                    f.write(f"file '{p.as_posix()}'\n")

            merged = td / "merged.mp3"
            out = td / "out.mp4"

            # Birleştir
            run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_txt), "-c", "copy", str(merged)])

            # Bars (spectrum)
            filt = f"showspectrum=s={width}x{height}:mode={bars_mode}:color=intensity,format=yuv420p"
            run([
                "ffmpeg", "-y", "-i", str(merged),
                "-filter_complex", filt,
                "-r", str(fps),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest",
                str(out)
            ])

            return CogPath(out)
