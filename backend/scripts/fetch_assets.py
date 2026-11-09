"""Download the face models and test videos that are not stored in git.

Usage (from the backend folder, venv active):  python scripts/fetch_assets.py
Already-downloaded files are skipped. Uses only the standard library.
"""
from __future__ import annotations

import os
import sys
import urllib.request

BACKEND = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))

ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"
MIXKIT = "https://assets.mixkit.co/videos/{id}/{id}-720.mp4"

ASSETS = [
    ("models/face_detection_yunet_2023mar.onnx", f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx"),
    ("models/face_recognition_sface_2021dec.onnx", f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx"),
    ("samples/speaker_on_stage.mp4", MIXKIT.format(id=13194)),
    ("samples/conference_room_group.mp4", MIXKIT.format(id=23116)),
    ("samples/team_meeting.mp4", MIXKIT.format(id=15798)),
    ("samples/conference_audience.mp4", MIXKIT.format(id=23035)),
    ("samples/talk_with_audience.mp4", MIXKIT.format(id=23292)),
    ("samples/pedestrians_opencv.avi", "https://github.com/opencv/opencv/raw/4.x/samples/data/vtest.avi"),
]


def main() -> int:
    failed = 0
    for rel, url in ASSETS:
        dest = os.path.join(BACKEND, rel)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"ok      {rel} (already there)")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"get     {rel} ...", end="", flush=True)
        try:
            urllib.request.urlretrieve(url, dest + ".part")
            os.replace(dest + ".part", dest)
            print(f" {os.path.getsize(dest) / 1e6:.1f} MB")
        except Exception as exc:
            failed += 1
            print(f" FAILED: {exc}")
    if failed:
        print(f"\n{failed} download(s) failed. Check your connection and run the script again.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
