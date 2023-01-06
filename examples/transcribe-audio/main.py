import os

from interval_sdk import Interval, IO, action_ctx_var

import whisper
import numpy as np
import ffmpeg

interval = Interval(
    os.environ.get("INTERVAL_API_KEY"),
)

model = whisper.load_model("base")


def audio_from_bytes(inp: bytes, sr: int = 16000):
    try:
        out, _ = (
            ffmpeg.input("pipe:", threads=0)
            .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
            .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=inp)
        )
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0


@interval.action
async def transcribe_audio(io: IO):

    file = await io.input.file(
        "Upload a file to transcribe", allowed_extensions=[".wav", ".mp3"]
    )

    ctx = action_ctx_var.get()
    await ctx.loading.start("Transcribing audio...")

    audio = audio_from_bytes(file.read())
    result = model.transcribe(audio)

    await io.group(
        io.display.heading("Transcription results"), io.display.markdown(result["text"])
    )

    return "All done!"


interval.listen()
