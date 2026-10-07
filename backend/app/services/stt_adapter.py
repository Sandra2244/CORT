import os
import subprocess
import base64
import tempfile

ENABLE_WHISPER = os.environ.get('ENABLE_WHISPER', '0') == '1'

class STTAdapter:
    async def transcribe(self, audio_b64: str | None):
        """If ENABLE_WHISPER=1 and whisper installed, decode audio and run whisper CLI as fallback."""
        if not audio_b64 or not ENABLE_WHISPER:
            return "[transcription placeholder]"
        try:
            audio_bytes = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as f:
                f.write(audio_bytes)
                tmp = f.name
            # use whisper CLI if available
            cmd = ['whisper', tmp, '--model', 'small', '--language', 'es']
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            # read output file
            txt_file = tmp.replace('.wav', '.txt')
            if os.path.exists(txt_file):
                with open(txt_file, 'r', encoding='utf-8') as fh:
                    text = fh.read().strip()
                return text
            return res.stdout.strip() or '[no transcription]'
        except Exception as e:
            return f'[transcription error] {e}'
