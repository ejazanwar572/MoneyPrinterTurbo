# Video Generation & Automation Lessons Learned

## 1. Frame-Perfect Sentence-Visual B-Roll Timing
- **Rule:** Never use rigid fixed-duration clips (e.g. 5-second slices) across sentence transitions.
- **Enforcement:** Always parse exact speech timestamps from TTS/SRT (`st` to `et`) for each sentence `i`, and slice B-roll clip `i` to match that exact duration so visual transitions occur on sentence boundaries.

## 2. Subtitle Block Count Mismatch & Font Safety
- **Rule:** Never allow TTS subtitle blocks to retain original Hindi/Devanagari text when using an English subtitle font (`STHeitiMedium.ttc`). Leftover non-Latin glyphs produce missing box artifacts `[ ][ ][ ]`.
- **Enforcement:** Proportionally map English translation sentences across all TTS subtitle blocks so 100% of blocks contain clean English text.

## 3. Subtitle Formatting & High-Retention Badging
- **Rule:** Never display long 20-word sentences in a single subtitle block. Long blocks obscure 30-40% of the video footage and hurt viewer retention.
- **Enforcement:** Automatically chunk long subtitle blocks into short, punchy 3-5 word phrases that update dynamically every 1.5 to 2 seconds on a single-line translucent rounded badge.

## 4. Culturally Accurate Stock B-Roll Queries
- **Rule:** Avoid generic queries like "red flag" or "priest" which pull irrelevant foreign stock footage (e.g., Turkish flags).
- **Enforcement:** Always use explicit, subject-accurate queries such as "indian temple flag saffron", "hindu priest temple tower", "ancient indian stone temple aerial".

## 5. Subtitle Font Size & Aesthetics
- **Rule:** Never use oversized font sizes (e.g. `60`) for subtitle badges on vertical 9:16 mobile screens. Large font sizes obscure video visuals and look unpolished.
- **Enforcement:** Default font size is set to `42` pt for sleek, elegant, highly readable subtitle badges that maintain 85%+ visual screen visibility.
