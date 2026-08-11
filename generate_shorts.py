import os
import sys
import json
import argparse
import re
import shutil
from loguru import logger

# Add project root to sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from app.config import config
from app.models.schema import VideoParams
from app.services import task as tm
from app.services import voice
from app.utils import utils

def parse_srt(srt_content):
    """
    Parse SRT content into a list of dicts: [{'index': str, 'times': str, 'text': str}]
    """
    blocks = []
    lines = srt_content.strip().split('\n')
    i = 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        index = lines[i].strip()
        if i + 1 < len(lines):
            times = lines[i+1].strip()
            text_lines = []
            i += 2
            while i < len(lines) and lines[i].strip():
                # If the line looks like an index followed by a timestamp in the next line, stop reading text
                if lines[i].strip().isdigit() and i + 1 < len(lines) and '-->' in lines[i+1]:
                    break
                text_lines.append(lines[i])
                i += 1
            blocks.append({
                'index': index,
                'times': times,
                'text': '\n'.join(text_lines)
            })
        else:
            i += 1
    return blocks

def write_srt(blocks):
    """
    Reconstruct SRT content from parsed blocks ensuring trailing double newline
    """
    out = []
    for b in blocks:
        out.append(str(b['index']))
        out.append(str(b['times']))
        out.append(str(b['text']))
        out.append('')
    return '\n'.join(out).strip() + '\n\n'

def split_sentences(text):
    """
    Split script/translation into clean sentences
    """
    sentences = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Split by sentence enders but keep them
        parts = re.split(r'(?<=[.!?।?])\s*', line)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences

def main():
    parser = argparse.ArgumentParser(description="Generate Hindi voiceover short video with English subtitles.")
    parser.add_argument("--subject", required=True, help="Video subject (e.g. 'mysteries of Bhangarh Fort')")
    parser.add_argument("--script", required=True, help="Hindi script content or path to text file containing it")
    parser.add_argument("--translation", required=True, help="English translation script content or path to text file containing it")
    parser.add_argument("--terms", required=True, help="Comma-separated Pexels search terms (one per sentence)")
    parser.add_argument("--output-name", default=None, help="Name for the final output video file (e.g. 'bhangarh.mp4')")
    parser.add_argument("--bgm-type", default="random", choices=["random", "custom", "none"], help="Background music type: random, custom, or none")
    parser.add_argument("--bgm-file", default="", help="Path to custom background music audio file (if --bgm-type is custom)")
    parser.add_argument("--bgm-volume", type=float, default=0.15, help="Background music volume (0.0 to 1.0, default 0.15)")
    args = parser.parse_args()

    # Pre-Flight Configuration Checks
    logger.info("Running pre-flight configuration checks...")
    
    # 1. Pexels API Key Check
    pexels_keys = config.app.get("pexels_api_keys", [])
    pexels_keys = [k for k in pexels_keys if k.strip() and k.strip() != "your_pexels_api_key"]
    if not pexels_keys:
        logger.error("Pre-flight failed: No valid Pexels API Key found in config.toml! Please add your key to config.toml before running.")
        sys.exit(1)
    
    # 2. client_secret.json Check
    client_secret_file = os.path.join(project_root, 'client_secret.json')
    if not os.path.exists(client_secret_file):
        logger.error(f"Pre-flight failed: client_secret.json not found in the project root ({project_root})!")
        logger.error("Please download your OAuth client credential JSON file from Google Console and save it there.")
        sys.exit(1)

    logger.info("Pre-flight checks passed successfully.")

    # Load script and translation contents
    script_content = args.script
    if os.path.exists(script_content):
        with open(script_content, "r", encoding="utf-8") as f:
            script_content = f.read()

    translation_content = args.translation
    if os.path.exists(translation_content):
        with open(translation_content, "r", encoding="utf-8") as f:
            translation_content = f.read()

    terms_list = [term.strip() for term in args.terms.split(",") if term.strip()]

    # Split scripts into sentences/lines for validation
    hindi_sentences = split_sentences(script_content)
    english_sentences = split_sentences(translation_content)

    logger.info(f"Hindi script sentences: {len(hindi_sentences)}")
    logger.info(f"English translation sentences: {len(english_sentences)}")
    logger.info(f"Search terms count: {len(terms_list)}")

    if len(english_sentences) != len(hindi_sentences):
        logger.warning(f"Mismatch: Hindi has {len(hindi_sentences)} sentences, English has {len(english_sentences)}.")

    if len(terms_list) < len(hindi_sentences):
        logger.warning(f"Warning: Only {len(terms_list)} search terms provided for {len(hindi_sentences)} sentences. Repeating the last term to align.")
        while len(terms_list) < len(hindi_sentences):
            terms_list.append(terms_list[-1])

    # Generate a unique task ID
    task_id = utils.get_uuid()
    logger.info(f"Generated task ID: {task_id}")

    bgm_type_val = None if args.bgm_type == "none" else args.bgm_type

    # Build video parameters matching the finalized audio/video specifications
    params = VideoParams(
        video_subject=args.subject,
        video_script=script_content,
        video_terms=terms_list,
        video_source="pexels",
        video_aspect="9:16",
        voice_name="hi-IN-SwaraNeural",
        subtitle_enabled=True,
        font_name="STHeitiMedium.ttc",
        rounded_subtitle_background=True,
        text_background_color=True,
        video_concat_mode="sequential",
        match_materials_to_script=True,
        bgm_type=bgm_type_val,
        bgm_file=args.bgm_file,
        bgm_volume=args.bgm_volume,
        n_threads=2,
    )

    # Step 1: Run the pipeline up to 'subtitle' stage
    logger.info("Starting MoneyPrinterTurbo task up to subtitle stage...")
    res = tm.start(task_id=task_id, params=params, stop_at="subtitle")
    if not res:
        logger.error("Task failed before subtitle stage.")
        sys.exit(1)

    task_dir = utils.task_dir(task_id)
    subtitle_path = os.path.join(task_dir, "subtitle.srt")
    audio_path = os.path.join(task_dir, "audio.mp3")

    if not os.path.exists(subtitle_path):
        logger.error(f"Subtitle file not found at {subtitle_path}")
        sys.exit(1)

    # Step 2: Read and replace subtitle content with English translation
    with open(subtitle_path, "r", encoding="utf-8") as f:
        srt_content = f.read()

    blocks = parse_srt(srt_content)
    logger.info(f"Found {len(blocks)} subtitle blocks in SRT.")

    # Align English sentences to SRT blocks
    if len(blocks) == len(english_sentences):
        for idx, block in enumerate(blocks):
            block['text'] = english_sentences[idx]
    else:
        logger.warning(
            f"SRT block count ({len(blocks)}) does not match English sentence count ({len(english_sentences)}). "
            "Falling back to sequential mapping."
        )
        for idx in range(min(len(blocks), len(english_sentences))):
            blocks[idx]['text'] = english_sentences[idx]

    updated_srt_content = write_srt(blocks)
    with open(subtitle_path, "w", encoding="utf-8") as f:
        f.write(updated_srt_content)
    logger.info("Successfully updated subtitles with English translation.")

    # Step 3: Download materials
    logger.info("Downloading b-roll materials...")
    audio_duration = voice.get_audio_duration(audio_path)
    downloaded_videos = tm.get_video_materials(task_id, params, terms_list, audio_duration)
    if not downloaded_videos:
        logger.error("Failed to download video materials.")
        sys.exit(1)

    # Step 4: Render final video
    logger.info("Rendering final video using MoviePy...")
    final_video_paths, combined_video_paths, *warnings = tm.generate_final_videos(
        task_id, params, downloaded_videos, audio_path, subtitle_path, audio_duration
    )

    if not final_video_paths:
        logger.error("Video rendering failed.")
        sys.exit(1)

    final_video = final_video_paths[0]
    logger.info(f"Video rendered successfully at: {final_video}")

    # Copy output to project root with a clean name
    output_name = args.output_name
    if not output_name:
        sanitized_subject = re.sub(r'[^a-zA-Z0-9_]', '_', args.subject.lower())
        output_name = f"{sanitized_subject}.mp4"
    
    dest_path = os.path.join(project_root, output_name)
    shutil.copy(final_video, dest_path)
    logger.info(f"SUCCESS: Copied final video to: {dest_path}")

if __name__ == "__main__":
    main()
