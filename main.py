import logging, os

from faster_whisper import WhisperModel
import asyncio, httpx
from typing import List

# Configure logging to show DEBUG messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_TAG = 'Main'
default_media_file = "input.mp4"
default_media_file_name = default_media_file.replace(".mp4", "")
# Get the parent folder `faster-whisper-models` to save `Whisper` models from `OpenAi`. > So other apps can reuse it.
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
whisper_models_path = os.path.join(parent_dir, "faster-whisper-models")  # Points to ../faster-whisper-models
language = 'en'
translated_language_code = 'vi'; translated_language_name = 'Vietnamese'
whisper_model_name = 'large-v2' # Best for now: 'large-v2 > medium'.
device = 'cpu'
default_srt_file_path = f'{default_media_file_name}.{language}.srt'
# Google AI Api stuffs (For Gemini).
google_ai_api_key = 'check_your_backend_to_get_google_ai_key'
google_ai_api_url_with_key = f'https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite:generateContent?key={google_ai_api_key}'

def segments_to_srt(segments, srt_file_path) -> str:
    """
    Save segments as SRT file.
    Args:
        segments: segments.
        srt_file_path: srt file path to write to.
    Returns:
        Path to the SRT file
    """
    logger.info(f'{_TAG}: segments_to_srt: in');

    try:
        with open(srt_file_path, "w") as f:
            for segment in segments:
                f.write(f"{segment.id}\n{segment.start} --> {segment.end}\n{segment.text.strip()}\n\n")
    except Exception as ex:
        logger.error(f'{_TAG}: segments_to_srt: Exception is: {ex}')

    logger.info(f'{_TAG}: segments_to_srt: out');
    return srt_file_path

def generate_srt_file_from_media_file(
    media_file_path: str = default_media_file,
    media_file_spoken_language: str = language,
    whisper_model_name: str = whisper_model_name,
    whisper_models_path: str = whisper_models_path
) -> str:
    """
    Generate srt file from a media file.
    Args:
        media_file_path: Path to the media file.
        media_file_spoken_language: The language spoken in the media file.
        whisper_model_name: The whisper model to use.
        whisper_models_path: Path to the whisper models.
    Returns:
        Path to the SRT file.
    """
    logger.info(f'{_TAG}: generate_srt_file_from_media_file: in')

    try:
        whisperModel = WhisperModel(
            model_size_or_path = whisper_model_name, # device = device,
            download_root = whisper_models_path)

        segments, _ = whisperModel.transcribe(media_file_path, language = media_file_spoken_language) # `_` is info.

        # Save segments as SRT.
        srt_file_path = segments_to_srt(segments = segments, srt_file_path = default_srt_file_path)
    except Exception as ex:
        logger.error(f'{_TAG}: generate_srt_file_from_media_file: Exception is: {ex}')

    logger.info(f'{_TAG}: generate_srt_file_from_media_file: out')
    return srt_file_path

def align_srt(srt_file_path: str) -> str:
    """
    Align the subtitles in the SRT file.
    Args:
        srt_file_path: Path to the SRT file.
    Returns:
        Path to the aligned SRT file.
    """
    logger.info(f'{_TAG}: align_srt: in');
    
    try:
        aligned_srt_file_path = f'aligned_{srt_file_path}'
        # Read the original SRT file
        with open(srt_file_path, 'r') as f:
            lines = f.readlines()
        
        aligned_segments = []
        current_segment = None
        
        i = 0
        while i < len(lines):
            # SRT format is: index\nstart --> end\ntext\n\n
            if lines[i].strip().isdigit():  # Segment number
                segment_id = int(lines[i].strip())
                i += 1
                
                # Parse timestamps
                time_line = lines[i].strip()
                start_time, end_time = time_line.split(' --> ')
                i += 1
                
                # Parse text
                text_lines = []
                while i < len(lines) and lines[i].strip() != '':
                    text_lines.append(lines[i].strip())
                    i += 1
                text = ' '.join(text_lines)
                i += 1  # Skip empty line
                
                # Check if current segment exists and doesn't end with punctuation
                if current_segment and not current_segment['text'].rstrip().endswith(('.', '?', '!')):
                    # Merge with current segment
                    current_segment['text'] += ' ' + text
                    current_segment['end'] = end_time
                else:
                    # Add previous segment if exists
                    if current_segment:
                        aligned_segments.append(current_segment)
                    # Start new segment
                    current_segment = {
                        'id': segment_id,
                        'start': start_time,
                        'end': end_time,
                        'text': text
                    }
        
        # Add the last segment
        if current_segment:
            aligned_segments.append(current_segment)
        
        # TODO: Can we reuse the `segments_to_srt` function?
        # Write aligned segments to new SRT file
        with open(aligned_srt_file_path, 'w') as f:
            for idx, segment in enumerate(aligned_segments, 1):
                f.write(f"{idx}\n")
                f.write(f"{segment['start']} --> {segment['end']}\n")
                f.write(f"{segment['text']}\n\n")
    except Exception as ex:
        logger.error(f'{_TAG}: align_srt: Exception is: {ex}')

    logger.info(f'{_TAG}: align_srt: out');
    return aligned_srt_file_path

async def translate_srt_using_gemini_api(srt_file_path: str, translated_language_code: str, translated_language_name: str, translated_srt_file_path: str, google_ai_api_url_with_key: str):
    """
    Translate SRT file using Gemini Api with FULL CONTEXT.
    Args:
        srt_file_path: srt_file_path that needs to translate.
        translated_language_code: The translated language code (e.g vi, jp, kr).
        translated_language_name: The translate language name (e.g Vietnamese, Japanese, Korean).
        translated_srt_file_path: The translated srt file path to write to.
        google_ai_api_url_with_key: The Url of Google AI API with key.
    Returns:
        Path to the translated SRT file.
    """
    logger.info(f'{_TAG}: translate_srt_using_gemini_api: in')

    try:
        # 1. Extract and combine text blocks
        text_blocks: List[str] = []
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            current_block = []
            for line in f:
                line = line.strip()
                if line and not line.isdigit() and '-->' not in line:
                    current_block.append(line)
                elif current_block:
                    text_blocks.append(' '.join(current_block))
                    current_block = []
            if current_block:
                text_blocks.append(' '.join(current_block))
        
        combined_text = '\n|||\n'.join(text_blocks)
        
        # 2. Simple prompt
        prompt = f"Translate the following text to {translated_language_name} exactly, preserving all special markers (|||) between segments:{combined_text}"
        # prompt = f"Translate this to {translated_language_name}:\n{combined_text}"
        
        # 3. API call with httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                google_ai_api_url_with_key,
                json={
                    "contents": [{
                        "parts": [{"text": prompt}]
                    }]
                },
                timeout=30.0  # Important for long translations
            )
            
            if response.status_code == 200:
                result = response.json()
                translated_combined = result['candidates'][0]['content']['parts'][0]['text']
                translated_blocks = translated_combined.split('|||')
                
                # 4. Reconstruct SRT
                with open(srt_file_path, 'r', encoding='utf-8') as f_in, \
                     open(translated_srt_file_path, 'w', encoding='utf-8') as f_out:
                    
                    block_idx = 0
                    for line in f_in:
                        line = line.strip()
                        if line and not line.isdigit() and '-->' not in line:
                            if block_idx < len(translated_blocks):
                                f_out.write(translated_blocks[block_idx].strip() + '\n')
                                block_idx += 1
                        else:
                            f_out.write(line + '\n')
            else:
                error = response.text
                logger.error(f"Gemini API error: {error}")

    except Exception as ex:
        logger.error(f'{_TAG}: Error: {ex}')
    
    logger.info(f'{_TAG}: translate_srt_using_gemini_api: out')
    return translated_srt_file_path

# Starting point.
async def main():
    # srt_file_path = generate_srt_file_from_media_file()
    align_srt_file_path = align_srt(srt_file_path = 'input.en.srt')
    # Translate into a specific language using Gemini.
    translated_align_srt_file_path_by_gemini = await translate_srt_using_gemini_api(
        srt_file_path = align_srt_file_path, translated_language_code = translated_language_code, translated_language_name = translated_language_name,
        translated_srt_file_path = f'aligned_{default_media_file_name}_gemini.{translated_language_code}.srt', google_ai_api_url_with_key = google_ai_api_url_with_key
    )

# Run the async function
asyncio.run(main())