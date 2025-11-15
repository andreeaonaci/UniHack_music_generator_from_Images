import os
import tempfile
import shutil
import subprocess
import requests
from pydub import AudioSegment


def download_and_convert(url: str, output_path: str, timeout: int = 120) -> str:
    """Download audio from `url` and convert to WAV 16k mono saved at `output_path`.

    Returns the path to the saved file (same as `output_path`). Raises on failure.
    """
    tmp_suffix = ".mp3" if url.lower().endswith('.mp3') else ""
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=tmp_suffix)
    tmp_file = tf.name
    tf.close()
    try:
        r = requests.get(url, stream=True, timeout=timeout)
        r.raise_for_status()
        with open(tmp_file, "wb") as fh:
            for chunk in r.iter_content(8192):
                if chunk:
                    fh.write(chunk)

        # If the remote file is already WAV and caller expects WAV, move it
        ct = r.headers.get("Content-Type", "").lower()
        if "wav" in ct or url.lower().endswith('.wav'):
            shutil.move(tmp_file, output_path)
            return output_path

        # Try ffmpeg conversion first
        if shutil.which("ffmpeg"):
            try:
                subprocess.run(["ffmpeg", "-y", "-i", tmp_file, "-ar", "16000", "-ac", "1", output_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return output_path
            except Exception:
                # fall through to pydub fallback
                pass

        # pydub fallback
        try:
            sound = AudioSegment.from_file(tmp_file)
            sound = sound.set_frame_rate(16000).set_channels(1)
            sound.export(output_path, format="wav")
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to convert downloaded audio to WAV: {e}")
    finally:
        try:
            if os.path.exists(tmp_file):
                os.unlink(tmp_file)
        except Exception:
            pass
