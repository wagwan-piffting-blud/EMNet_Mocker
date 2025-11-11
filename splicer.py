"""
EMnet Splicer
=======================
This script provides functionality to splice together multiple Comlabs Government Systems EMNet audio files into one single audio file based on a ZCZC EAS Header code. The splicing process ensures that the audio segments are concatenated in the correct order based on the header codes. As well, (basic) EAS tone generation is supported based on the ZCZC header information.

Example Usage: python splicer.py -o output_file.wav -z ZCZC_CODE
"""

import os
import re
import time
import argparse
from datetime import datetime, timedelta, timezone
from pydub import AudioSegment
from pydub.generators import Sine

def generate_tones(zczc_string):
    """
    Generate EAS tones based on the ZCZC string.

    This function will add the appropriate EAS tones to the beginning of the spliced audio based on the ZCZC header information. Quoting Wikipedia:

    "The digital sections of a SAME message are AFSK data bursts, with individual bits lasting 1920 μs (1.92 ms) each, giving a bit rate of 520.83 bits per second. A mark bit is four complete cycles of a sine wave, translating to a mark frequency of 2083.33 Hz, and a space bit is three complete sine wave cycles, making the space frequency 1562.5 Hz.

    The data is sent isochronously and encoded in 8-bit bytes with the most-significant bit of each ASCII byte set to zero. The least-significant bit of each byte is transmitted first, including the preamble. The data stream is bit and byte synchronized on the preamble. Since there is no error correction, the digital part of a SAME message is transmitted three times, so that decoders can pick 'best two out of three' for each byte, thereby eliminating most errors which can cause an activation to fail."

    (Source: https://en.wikipedia.org/wiki/Specific_Area_Message_Encoding#Format_of_digital_parts)
    """
    if not zczc_string:
        raise ValueError("ZCZC string cannot be empty.")

    header_text = zczc_string.strip()
    if not header_text:
        raise ValueError("ZCZC string cannot be empty or whitespace.")

    try:
        header_bytes = header_text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("ZCZC string must contain ASCII characters only.") from exc

    bit_rate = 520.8333333333334
    bit_duration_ms = 1000.0 / bit_rate
    mark_freq = 2083.3333
    space_freq = 1562.5
    sample_rate = 44100

    cache = getattr(generate_tones, "_segment_cache", None)
    if cache is None:
        mark_segment = Sine(mark_freq, sample_rate=sample_rate).to_audio_segment(duration=bit_duration_ms)
        mark_segment = mark_segment.set_channels(1).set_sample_width(2)
        space_segment = Sine(space_freq, sample_rate=sample_rate).to_audio_segment(duration=bit_duration_ms)
        space_segment = space_segment.set_channels(1).set_sample_width(2)
        gap_segment = AudioSegment.silent(duration=1000, frame_rate=sample_rate).set_channels(1).set_sample_width(2)

        mark_raw = mark_segment.raw_data
        space_raw = space_segment.raw_data
        byte_lookup = []
        for value in range(256):
            raw_bits = bytearray()
            for bit_index in range(8):
                raw_bits.extend(mark_raw if (value >> bit_index) & 1 else space_raw)
            byte_lookup.append(bytes(raw_bits))

        cache = {
            "sample_width": mark_segment.sample_width,
            "frame_rate": mark_segment.frame_rate,
            "channels": mark_segment.channels,
            "byte_lookup": tuple(byte_lookup),
            "gap_raw": gap_segment.raw_data,
        }
        generate_tones._segment_cache = cache

    sample_width = cache["sample_width"]
    frame_rate = cache["frame_rate"]
    channels = cache["channels"]
    byte_lookup = cache["byte_lookup"]
    gap_raw = cache["gap_raw"]

    preamble = bytes([0xAB] * 16)
    burst_bytes = preamble + header_bytes + b"\r"

    raw_audio = bytearray()
    for burst_index in range(3):
        for value in burst_bytes:
            raw_audio.extend(byte_lookup[value])
        if burst_index < 2:
            raw_audio.extend(gap_raw)

    return AudioSegment(
        data=bytes(raw_audio),
        sample_width=sample_width,
        frame_rate=frame_rate,
        channels=channels,
    )

def split_zczc(zczc_string):
    """
    Split the ZCZC string into its components.

    Example: ZCZC-ORG-EEE-PSSCCC+TTTT-JJJHHMM-LLLLLLLL-
    where:
    ORG = Originator Code (3 letters)
    EEE = Event Code (3 letters)
    PSSCCC = Location Code (6 digits per FIPS, can include multiple county FIPS codes, up to 31 codes total)
    TTTT: Duration (4 digits)
    JJJHHMM: Date-Time Group (7 digits)
    LLLLLLLL: Station Identifier (up to 8 characters)

    We need to use a Regex to split this string into its components. This is because the SAME standard allows for multiple county FIPS codes to be specified in the PSSCCC field, which means that we cannot simply split on the hyphens. The regex will be designed to capture each component of the ZCZC string.
    """

    pattern = r"^ZCZC-([A-Z]{3})-([A-Z]{3})-((?:\d{6}(?:-?)){1,31})\+(\d{4})-(\d{7})-([A-Za-z0-9\/ ]{0,8})-?$"
    match = re.match(pattern, zczc_string)

    if match:
        return match.groups()
    else:
        raise ValueError("Invalid ZCZC string format.")

def splice(output_file, zczc_code, use_local_time=False, include_tones=False, tz_override=None):
    """
    Splice audio segments based on the provided ZCZC code.

    The EMNet audio files are located in the same directory as this script. The audio files are named using the following conventions:

    Events:
    EVENTS/event_code.wav
    where event_code is the 3-letter event code from the ZCZC header.

    Locations:
    LOC/location_code.wav
    where location_code is the 6-digit FIPS code from the ZCZC header.

    Other segments:
    OTHER/until.wav
    OTHER/and.wav
    where 'until' and 'and' are just those words as audio segments used in the splicing process.

    TIMES:
    TIMES/am.wav
    TIMES/pm.wav
    TIMES/hour(01-12).wav
    TIMES/minute(00-59).wav
    where these files represent the time components in the ZCZC header. For example, if the duration time is "0130", and the alert was issued at "0011200", we would calculate the end time and use these audio segments accordingly. This would mean in this example that the alert ends at 1:30 PM, so take the hour1.wav, minute30.wav, and pm.wav files.
    """
    audio_segments = []

    if include_tones:
        audio_segments.append(AudioSegment.silent(duration=1000).set_channels(1).set_sample_width(2))
        tones = generate_tones(zczc_code)
        audio_segments.append(tones)
        audio_segments.append(AudioSegment.silent(duration=1000).set_channels(1).set_sample_width(2))
        # Append combined attention signal (853+960 Hz) for 8 seconds
        attention_signal = AudioSegment.silent(duration=0).set_channels(1).set_sample_width(2)
        freq1 = 853
        freq2 = 960
        sample_rate = 44100
        duration_ms = 8000
        sine1 = Sine(freq1, sample_rate=sample_rate).to_audio_segment(duration=duration_ms)
        sine2 = Sine(freq2, sample_rate=sample_rate).to_audio_segment(duration=duration_ms)
        combined_signal = sine1.overlay(sine2)
        attention_signal += combined_signal
        audio_segments.append(attention_signal)
        audio_segments.append(AudioSegment.silent(duration=1000).set_channels(1).set_sample_width(2))

    zczc_split = split_zczc(zczc_code)
    originator, event, location_codes, duration, datetime_group, station_id = zczc_split
    location_code_list = location_codes.split('-')

    event_file = os.path.join("EVENTS", f"{event}.wav")

    if os.path.exists(event_file):
        audio_segments.append(AudioSegment.from_wav(event_file))
    else:
        raise FileNotFoundError(f"Warning: Event audio file {event_file} not found.")

    for index, location_code in enumerate(location_code_list):
        if (index == len(location_code_list) - 1) and index != 0:
            and_file = os.path.join("OTHER", "and.wav")
            if os.path.exists(and_file):
                audio_segments.append(AudioSegment.from_wav(and_file))
            else:
                raise FileNotFoundError(f"Warning: And audio file {and_file} not found.")
        location_file = os.path.join("LOC", f"{location_code}.wav")
        if os.path.exists(location_file):
            audio_segments.append(AudioSegment.from_wav(location_file))
        else:
            raise FileNotFoundError(f"Warning: Location audio file {location_file} not found.")

    until_file = os.path.join("OTHER", "until.wav")

    if os.path.exists(until_file):
        audio_segments.append(AudioSegment.from_wav(until_file))
    else:
        raise FileNotFoundError(f"Warning: Until audio file {until_file} not found.")

    issue_time = datetime_group[3:]
    issue_hour = int(issue_time[0:2])
    issue_minute = int(issue_time[2:4])
    duration_hours = int(duration[0:2])
    duration_minutes = int(duration[2:4])

    end_hour = (issue_hour + duration_hours + (issue_minute + duration_minutes) // 60) % 24
    end_minute = (issue_minute + duration_minutes) % 60

    if use_local_time:
        """
        Adjust end time calculation to local timezone. This is done by getting the current timezone from the OS and calculating the offset from UTC. Then, we apply this offset to the issue time and duration to get the correct local end time.
        """
        tzinfo_sub = datetime.now().astimezone().tzinfo
        issue_datetime_utc = datetime.now(timezone.utc).replace(hour=issue_hour, minute=issue_minute, second=0, microsecond=0)
        issue_datetime_local = issue_datetime_utc.astimezone(tzinfo_sub)
        end_datetime_local = issue_datetime_local + timedelta(hours=duration_hours, minutes=duration_minutes)
        end_hour = end_datetime_local.hour
        end_minute = end_datetime_local.minute

    elif tz_override is not None:
        """
        Adjust end time calculation to the specified timezone offset. Timezone offsets are specified as the name of the timezone (e.g., "EST", "PST", etc.). We create a timezone object with the specified offset and apply it to the issue time and duration to get the correct end time.
        """
        tz_offsets = {
            "UTC": 0,
            "EST": -5,
            "EDT": -4,
            "CST": -6,
            "CDT": -5,
            "MST": -7,
            "MDT": -6,
            "PST": -8,
            "PDT": -7,
        }
        if tz_override not in tz_offsets:
            raise ValueError(f"Invalid timezone override: {tz_override}")
        offset_hours = tz_offsets[tz_override]
        tzinfo_sub = timezone(timedelta(hours=offset_hours))
        issue_datetime_utc = datetime.now(timezone.utc).replace(hour=issue_hour, minute=issue_minute, second=0, microsecond=0)
        issue_datetime_tz = issue_datetime_utc.astimezone(tzinfo_sub)
        end_datetime_tz = issue_datetime_tz + timedelta(hours=duration_hours, minutes=duration_minutes)
        end_hour = end_datetime_tz.hour
        end_minute = end_datetime_tz.minute

    if end_hour == 0:
        hour_file = os.path.join("TIMES", "hour12.wav")
        ampm_file = os.path.join("TIMES", "am.wav")
    elif end_hour < 12:
        hour_file = os.path.join("TIMES", f"hour{end_hour:02d}.wav")
        ampm_file = os.path.join("TIMES", "am.wav")
    elif end_hour == 12:
        hour_file = os.path.join("TIMES", "hour12.wav")
        ampm_file = os.path.join("TIMES", "pm.wav")
    else:
        hour_file = os.path.join("TIMES", f"hour{end_hour - 12:02d}.wav")
        ampm_file = os.path.join("TIMES", "pm.wav")

    minute_file = os.path.join("TIMES", f"minute{end_minute:02d}.wav")
    if os.path.exists(hour_file):
        audio_segments.append(AudioSegment.from_wav(hour_file))
    else:
        raise FileNotFoundError(f"Warning: Hour audio file {hour_file} not found.")
    if os.path.exists(minute_file):
        audio_segments.append(AudioSegment.from_wav(minute_file))
    else:
        raise FileNotFoundError(f"Warning: Minute audio file {minute_file} not found.")
    if os.path.exists(ampm_file):
        audio_segments.append(AudioSegment.from_wav(ampm_file))
    else:
        raise FileNotFoundError(f"Warning: AM/PM audio file {ampm_file} not found.")

    if include_tones:
        audio_segments.append(AudioSegment.silent(duration=1000).set_channels(1).set_sample_width(2))
        tones = generate_tones("NNNN")
        audio_segments.append(tones)
        audio_segments.append(AudioSegment.silent(duration=1000).set_channels(1).set_sample_width(2))

    if not audio_segments:
        print("No audio segments found to splice.")
        return

    combined_audio = AudioSegment.silent(duration=0)
    for segment in audio_segments:
        combined_audio += segment
    combined_audio.export(output_file, format="wav")
    print(f"Spliced audio saved to {output_file} successfully.")

def main():
    parser = argparse.ArgumentParser(description="Splice EMNet audio files based on ZCZC EAS Header code.")
    parser.add_argument("-o", "--output_file", required=True, help="Output file path for the spliced audio.")
    parser.add_argument("-z", "--zczc_code", required=True, help="ZCZC EAS Header code to splice by.")
    parser.add_argument("-l", "--local-time", action="store_true", help="Use local time for calculations instead of UTC.")
    parser.add_argument("-O", "--tz-override", help="Override timezone offset by name (e.g., 'EST', 'PST'). Cannot be used with --local-time.")
    parser.add_argument("-t", "--include-tones", action="store_true", help="Include EAS tones in the spliced audio.")
    parser.add_argument("-v", "--version", action="version", version="EMnet Splicer 1.0.0 by Wags")

    args = parser.parse_args()

    if args.local_time and args.tz_override is not None:
        parser.error("Cannot use --local-time and --tz-override together.")

    try:
        splice(args.output_file, args.zczc_code, args.local_time, args.include_tones, args.tz_override)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
