import os
import subprocess

ENABLE_TTS = os.environ.get('ENABLE_TTS', '0') == '1'

class TTSAdapter:
    async def synthesize(self, text: str, voice: str | None = None):
        if not ENABLE_TTS:
            return {"type":"placeholder","text_length": len(text), "voice": voice}
        try:
            # Try using Coqui TTS CLI 'tts' if installed
            cmd = ['tts', '--text', text, '--out_path', '/tmp/cort_tts.wav']
            if voice:
                cmd += ['--speaker', voice]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if os.path.exists('/tmp/cort_tts.wav'):
                return {'type':'file','path':'/tmp/cort_tts.wav'}
            return {'type':'error','message': res.stderr}
        except Exception as e:
            return {'type':'error','message': str(e)}
