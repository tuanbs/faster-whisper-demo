import os
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
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
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel threads")
    return parser.parse_args()

def validate_input_file(input_video):
    if not os.path.exists(input_video):
        raise FileNotFoundError(f"Input file {input_video} not found!")

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")

def transcribe_segment(segment):
    """Helper function for parallel processing"""
    return (
        segment.start,
        segment.end,
        segment.text.strip().replace(",", "\\,")
    )

def transcribe_audio_directly(input_video, model_size, num_workers):
    try:
        model = WhisperModel(model_size)
        
        # Transcribe in parallel
        segments, info = model.transcribe(input_video)
        segments = list(segments)  # Convert generator to list for parallel processing
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            processed_segments = list(executor.map(transcribe_segment, segments))
        
        # Reconstruct segments with original order
        results = [
            {"start": start, "end": end, "text": text}
            for start, end, text in processed_segments
        ]
        
        return info.language, results
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise

def segments_to_srt(segments, language, input_video):
    output_path = f"{os.path.splitext(input_video)[0]}.{language}.srt"
    with open(output_path, "w", encoding="utf-8-sig") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_time(segment["start"])
            end = format_time(segment["end"])
            text = segment["text"]
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

if __name__ == "__main__":
    args = parse_args()
    validate_input_file(args.input)
    
    logger.info(f"Starting transcription with {args.workers} workers...")
    language, segments = transcribe_audio_directly(
        args.input, 
        args.model, 
        args.workers
    )
    
    segments_to_srt(segments, language, args.input)
    logger.info(f"SRT file generated with {len(segments)} subtitles.")