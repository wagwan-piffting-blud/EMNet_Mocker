# EMnet Splicer
This script provides functionality to splice together multiple Comlabs Government Systems EMNet audio files into one single audio file based on a ZCZC EAS Header code. The splicing process ensures that the audio segments are concatenated in the correct order based on the header codes. As well, (basic) EAS tone generation is supported based on the ZCZC header information.

Basic Example Usage: `python splicer.py -o output.wav -z "ZCZC-WXR-RWT-031025-031021-031155-031153-019155-031177-031055-031131-019085-031053-019129+0100-2782118-KOAX/NWS-"`

## Requirements
- Python 3.x (3.13 and above needs `audioop-lts` for audioop backport since audioop is not included in the standard library for these versions)
- pydub library (for audio processing)
- ffmpeg (required by pydub for audio file handling)

## Installation
1. Clone the repository:

```bash
git clone https://github.com/wagwan-piffting-blud/EMNet_Mocker
cd EMNet_Mocker
```

2. Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

3. Ensure ffmpeg is installed and accessible in your system's PATH. You can download it from [ffmpeg.org](https://ffmpeg.org/download.html).

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

You may also specify a manual timezone offset override using -O or --tz-override (e.g., "EST", "PDT"; most US timezones and their DST counterparts [listed on this page](https://en.wikipedia.org/wiki/Time_in_the_United_States#United_States_and_regional_time_zones) are supported):

```bash
python splicer.py -o output.wav -z "ZCZC_CODE" -O "EST"
```

Note that `-O` and `-l` are _mutually exclusive_; you can only use one of them at a time.

For some message types, an alternate message audio file is available. You can specify this when generating the file, or always use it with the `-a` or `--use-alt-message` flag:

```bash
python splicer.py -o output.wav -z "ZCZC_CODE" -a
```

The alternate message audio files are located in `EVENTS/ALT/event.wav`, where `event` is the event code from the ZCZC header. A current list of these alternative messages is as follows:

```python
ALT_MESSAGES = {
    "ADR": "'A daily check message has been issued for' will be used instead of 'An administrative message has been issued for'",
    "EVI": "'An order to evacuate immediately has been issued for' will be used instead of 'An immediate evacuation warning has been issued for'",
    "SVR": "'This is a severe thunderstorm warning for' will be used instead of 'A severe thunderstorm warning has been issued for'",
}
```

## A note on missing files
If you have any more of the EMnet audio files that are not currently included in the repository, feel free to submit a pull request or open an issue to have them added. Make sure the file(s) is/are publicly accessible. **Specifically, the LOC/000000.wav (all of United States) file is currently missing from this repo.** Make sure these are the RAW, ORIGINAL .wav audio files from EMNet, as any modified/compressed versions may not sound correct when splicing.

## Acknowledgments
- [The EASyKit](https://theeasykit.weebly.com/) and [All EMNet Audio (Encoder2)](https://archive.org/details/emnet-audio) for the original audio files from EMNet
- [pydub](https://github.com/jiaaro/pydub) library for audio processing
- [Global Weather and EAS Society](https://globaleas.org/) for support and resources

## GenAI Disclosure Notice: Portions of this repository have been generated using Generative AI tools (ChatGPT Codex, GitHub Copilot).
