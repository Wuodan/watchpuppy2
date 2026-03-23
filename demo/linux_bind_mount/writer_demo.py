import sys
import time
from pathlib import Path

_PAUSE_SECONDS = 3


def main() -> int:
    share = Path(sys.argv[1])
    created_path = share / "created.txt"
    renamed_path = share / "renamed.txt"
    while True:
        print("writer creating created.txt")
        created_path.write_text("one\n", encoding="utf-8")
        time.sleep(_PAUSE_SECONDS)
        print("writer modifying created.txt")
        created_path.write_text("one\ntwo\n", encoding="utf-8")
        time.sleep(_PAUSE_SECONDS)
        print("writer renaming created.txt to renamed.txt")
        created_path.rename(renamed_path)
        time.sleep(_PAUSE_SECONDS)
        print("writer deleting renamed.txt")
        renamed_path.unlink(missing_ok=True)
        time.sleep(_PAUSE_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
