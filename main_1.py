import os
import argparse
import logging
from faster_whisper import WhisperModel
# from dotenv import load_dotenv

# Setup
# load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="input.mp4", help="Input video file")
    parser.add_argument("--model", default="small", help="Whisper model size")
    return parser.parse_args()

def validate_input_file(input_video):
    if not os.path.exists(input_video):
        raise FileNotFoundError(f"Input file {input_video} not found!")

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")

def transcribe_audio_directly(input_video, model_size):
    try:
        model = WhisperModel(model_size)
        segments, info = model.transcribe(input_video)
        return info.language, list(segments)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise

def segments_to_srt(segments, language, input_video):
    output_path = f"{os.path.splitext(input_video)[0]}.{language}.srt"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_time(segment.start)
            end = format_time(segment.end)
            text = segment.text.strip().replace(",", "\\,")
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

if __name__ == "__main__":
    args = parse_args()
    validate_input_file(args.input)
    language, segments = transcribe_audio_directly(args.input, args.model)
    segments_to_srt(segments, language, args.input)
    logger.info(f"SRT file generated with {len(segments)} subtitles.")