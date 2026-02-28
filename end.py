from pathlib import Path
import sys


def main() -> None:
    args = sys.argv[1:]
    output_path = Path(__file__).resolve().with_name("script_args.txt")

    with output_path.open("w", encoding="utf-8") as output_file:
        output_file.write("\n".join(args))


if __name__ == "__main__":
    main()
