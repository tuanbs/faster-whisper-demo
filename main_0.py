import logging
import os

import re

from faster_whisper import WhisperModel

# Configure logging to show DEBUG messages
# logging.basicConfig(
#     level=logging.DEBUG, # Forces the logger to display messages of level DEBUG and above (including INFO, WARNING, ERROR, etc.). Without this, only WARNING/ERROR/CRITICAL messages appear by default.
#     format='%(asctime)s - %(name)s - %(levelName)s - %(message)s' # Simple log format
# )
# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_TAG = 'Main'
input_video = "input.mp4"
input_video_name = input_video.replace(".mp4", "")
# Get the parent folder `faster-whisper-models` to save `Whisper` models from `OpenAi`. > So other apps can reuse it.
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
download_root = os.path.join(parent_dir, "faster-whisper-models")  # Points to ../faster-whisper-models
language = 'en'
model_size_or_path = 'large-v2' # Best for now: 'large-v2 > medium'.
device = 'cpu'

# Helper functions
def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")

# Public functions.
def transcribe_audio_directly(input_video):
    try:
        # Faster-Whisper decodes audio internally via PyAV
        whisperModel = WhisperModel(
            model_size_or_path = model_size_or_path, # device = device,
            download_root = download_root)
        segments, info = whisperModel.transcribe(input_video, language=language)
        
        return info.language, list(segments)
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise

def _align_subtitles_chatGpt(subtitles_path):
    sentence_end_pattern = re.compile(r'[.?!]["\']?$')  # Match '.', '?', or '!' optionally followed by quotes

    with open(subtitles_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = []
    index, start, end, text = None, None, None, ""

    def write_entry(idx, start_time, end_time, content):
        return f"{idx}\n{start_time} --> {end_time}\n{content.strip()}\n\n"

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.isdigit():
            index = int(line)
            i += 1
            start_end_line = lines[i].strip()
            start, end = start_end_line.split(' --> ')
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            full_text = ' '.join(text_lines)
            text += " " + full_text if text else full_text
            # If sentence ends, push to entries
            if sentence_end_pattern.search(full_text):
                entries.append((start, end, text.strip()))
                text = ""
        i += 1

    # Write remaining text if any
    if text:
        entries.append((start, end, text.strip()))

    # Save the aligned subtitles
    aligned_path = os.path.join(
        os.path.dirname(subtitles_path),
        f"aligned_{os.path.basename(subtitles_path)}"
    )

    with open(aligned_path, "w", encoding='utf-8') as f:
        for idx, (start, end, text) in enumerate(entries, start=1):
            f.write(write_entry(idx, start, end, text))

    logging.info(f"Aligned subtitles saved to {aligned_path}")

def _align_subtitles_deepSeek(subtitles_path: str) -> str:
    """
    Merges subtitle lines based on punctuation for better readability.
    Args:
        subtitles_path: Path to the original SRT file
    Returns:
        Path to the aligned SRT file
    """
    logger.debug(f"{_TAG}: _align_subtitles(): in")
    
    # Read original subtitles
    with open(subtitles_path, 'r') as f:
        lines = f.readlines()
    
    # Parse SRT segments
    segments = []
    current_segment = None
    
    for line in lines:
        line = line.strip()
        if line.isdigit():  # Segment number
            if current_segment is not None:
                segments.append(current_segment)
            current_segment = {"num": int(line), "lines": []}
        elif "-->" in line:  # Timecode
            if current_segment is not None:
                start_end = line.split(" --> ")
                current_segment["start"] = start_end[0].strip()
                current_segment["end"] = start_end[1].strip()
        elif line:  # Text
            if current_segment is not None:
                current_segment["lines"].append(line)
    
    if current_segment is not None:
        segments.append(current_segment)
    
    # Merge logic (punctuation-based)
    merged_segments = []
    current_merge = None
    
    for seg in segments:
        text = " ".join(seg["lines"])
        last_char = text[-1] if text else ""
        
        if current_merge is None:
            current_merge = seg.copy()
        else:
            # Merge if previous segment doesn't end with proper punctuation
            if last_char not in {'.', '?', '!', ':', '"', "'"}:
                current_merge["lines"] += seg["lines"]
                current_merge["end"] = seg["end"]
            else:
                merged_segments.append(current_merge)
                current_merge = seg.copy()
    
    if current_merge is not None:
        merged_segments.append(current_merge)
    
    # Generate aligned SRT
    aligned_path = f"aligned_{subtitles_path}"
    with open(aligned_path, 'w') as f:
        for i, seg in enumerate(merged_segments, 1):
            f.write(f"{i}\n")
            f.write(f"{seg['start']} --> {seg['end']}\n")
            f.write(f"{' '.join(seg['lines'])}\n\n")
    
    logger.info(f"Aligned subtitles saved to: {aligned_path}")
    return aligned_path

def segments_to_srt(segments, language, align = False):
    logger.debug(f"{_TAG}: segments_to_srt(): in")

    output_path = f"{input_video_name}.{language}.srt"
    with open(output_path, "w") as f:
        for i, segment in enumerate(segments, start=1):
            start = format_time(segment.start)
            end = format_time(segment.end)
            text = segment.text.strip()  # Trim the " " at the beginning of text.
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")

    if align:
        output_path = _align_subtitles_deepSeek(output_path)

    logger.debug(f"{_TAG}: segments_to_srt(): out")
    return output_path

# Startup.
if __name__ == "__main__":
    output_path = _align_subtitles_chatGpt('input.en.srt')

    # language, segments = transcribe_audio_directly("input.mp4")
    # segments_to_srt(segments, language, align=True)
    # logger.info(f"SRT file generated with {len(segments)} subtitles.")