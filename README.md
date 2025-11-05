# EMnet Splicer
This script provides functionality to splice together multiple Comlabs Government Systems EMNet audio files into one single audio file based on a ZCZC EAS Header code. The splicing process ensures that the audio segments are concatenated in the correct order based on the header codes. As well, (basic) EAS tone generation is supported based on the ZCZC header information.

Example Usage: `python splicer.py -o output.wav -z "ZCZC-WXR-RWT-031025-031021-031155-031153-019155-031177-031055-031131-019085-031053-019129+0100-2782118-KOAX/NWS"`

## Requirements
- Python 3.x
- pydub library (for audio processing, you can install this with `pip install pydub`)

## Usage
Basic usage:

```bash
python splicer.py -o output.wav -z "ZCZC_CODE"
```

If you want to use local time for the end time calculation, add the `-l` or `--local-time` flag:

```bash
python splicer.py -o output.wav -z "ZCZC_CODE" -l
```

If you want to include the full EAS tones, add the `-t` or `--include-tones` flag:

```bash
python splicer.py -o output.wav -z "ZCZC_CODE" -t
```

You can also combine the above two flags as needed:

```bash
python splicer.py -o output.wav -z "ZCZC_CODE" -l -t
```

You may also specify a timezone offset override using -O or --tz-override (e.g., "EST", "PDT"; most common US timezones are supported):

```bash
python splicer.py -o output.wav -z "ZCZC_CODE" -O "EST"
```

Note that -O and -l are mutually exclusive; you can only use one of them at a time.

## GenAI Disclosure Notice: Portions of this repository have been generated using Generative AI tools (ChatGPT, ChatGPT Codex, GitHub Copilot).
