# Subtitle Processing App - Informal Pseudocode

## High-Level App Flow

```
1. Start the subtitle processing app
2. Generate SRT file from media file using Whisper AI
   - Load Whisper model
   - Transcribe audio to text segments
   - Save segments as SRT file
3. Align the SRT subtitles
   - Read original SRT file
   - Merge segments that don't end with punctuation
   - Save aligned SRT file
4. Translate aligned SRT using Gemini AI
   - Extract text blocks from SRT
   - Send to Gemini API for translation
   - Reconstruct translated SRT file
5. End - output final translated subtitle file
```

## Detailed Function Pseudocode

### generate_srt_file_from_media_file()
```
1. Initialize Whisper model with specified size and download path
2. Transcribe the media file:
   - Pass media file path and language to Whisper
   - Get back segments and info
3. Convert segments to SRT format:
   - For each segment: write ID, timestamp, and text
4. Save to SRT file
5. Return SRT file path
```

### align_srt()
```
1. Read the original SRT file line by line
2. Parse each subtitle segment:
   - Extract segment ID, timestamps, and text
3. For each segment:
   - If current segment doesn't end with punctuation (. ? !):
     - Merge with next segment
     - Update end timestamp
   - Otherwise:
     - Save current segment to aligned list
     - Start new segment
4. Write all aligned segments to new SRT file
5. Return aligned SRT file path
```

### translate_srt_using_gemini_api()
```
1. Read SRT file and extract only text content
2. Combine all text blocks with separator (|||)
3. Create translation prompt for Gemini
4. Send HTTP POST request to Gemini API:
   - Include combined text in request body
   - Wait for response with timeout
5. If API call successful:
   - Extract translated text from response
   - Split translated text back into blocks
6. Reconstruct SRT file:
   - Keep original timestamps and IDs
   - Replace original text with translated text
7. Save translated SRT file
8. Return translated SRT file path
```

## Error Handling Pattern (Used Throughout)
```
1. Try to execute main function logic
2. If any exception occurs:
   - Log the error with function name
   - Continue execution (don't crash)
3. Always log function entry and exit
```

## Configuration Variables
```
- Default media file: "input.mp4"
- Whisper model: "large-v2"
- Source language: English
- Target language: Vietnamese
- Model storage path: "../faster-whisper-models"
- Gemini API URL with key
```