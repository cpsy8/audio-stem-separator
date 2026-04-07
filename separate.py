"""
Music separator using Demucs.
Usage:
    python separate.py <audio_file> [options]
"""
import sys
import os
import argparse
import demucs.separate


def main():
    parser = argparse.ArgumentParser(description="Separate music into stems using Demucs.")
    parser.add_argument("file", help="Path to the audio file (mp3, wav, flac, etc.)")
    parser.add_argument(
        "--vocals-only",
        action="store_true",
        help="Two-stem mode: separate vocals vs. instrumental only",
    )
    parser.add_argument(
        "--model",
        default="htdemucs",
        choices=["htdemucs", "htdemucs_ft", "htdemucs_6s", "mdx", "mdx_extra", "mdx_q", "mdx_extra_q"],
        help="Model to use (default: htdemucs)",
    )
    parser.add_argument("--wav", action="store_true", help="Output as WAV instead of MP3")
    parser.add_argument("--bitrate", type=int, default=320, help="MP3 bitrate in kbps (default: 320)")
    parser.add_argument("--out", default="separated", help="Output directory (default: separated)")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    demucs_args = ["-n", args.model, "-o", args.out, "-d", "cpu"]
    if not args.wav:
        demucs_args += ["--mp3", "--mp3-bitrate", str(args.bitrate)]
    if args.vocals_only:
        demucs_args += ["--two-stems", "vocals"]
    demucs_args.append(args.file)

    print(f"Separating: {args.file}")
    print(f"Model:      {args.model}")
    print(f"Output:     {args.out}/")
    print(f"Format:     {'WAV' if args.wav else f'MP3 ({args.bitrate} kbps)'}")
    if args.vocals_only:
        print("Mode:       vocals + instrumental (no_vocals)")
    else:
        print("Mode:       drums / bass / vocals / other")
    print()

    demucs.separate.main(demucs_args)
    print(f"\nDone! Output saved to: {os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
