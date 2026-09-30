"""Simulated scanner: stands in for the ESP32-CAM until the board arrives.

It sends a JPEG photo to the same endpoint the ESP32-CAM will use (POST /api/v1/scans/jpeg),
so the backend can't tell the difference.

Usage (from backend/):
  .venv/bin/python tools/scanner_sim.py                 # webcam: SPACE = scan, Q = quit
  .venv/bin/python tools/scanner_sim.py photo1.jpg ...  # send image files instead
  options: --server http://127.0.0.1:8000  --camera 0
"""

import argparse
import sys

import cv2
import httpx


def send(server: str, jpeg: bytes) -> None:
    try:
        resp = httpx.post(f"{server}/api/v1/scans/jpeg", content=jpeg,
                          headers={"Content-Type": "image/jpeg"}, timeout=20)
    except httpx.HTTPError as exc:
        print(f"  Could not reach the backend: {exc}")
        return
    if resp.status_code == 201:
        data = resp.json()["data"]
        item = data["item"]
        print(f"  Added: {item['name']} [{item['category']}] expires {item['expiryDate']}"
              f" (source: {data['source']}, code: {data['code']})")
    else:
        print(f"  {resp.status_code}: {resp.json()['error']['message']}")


def scan_files(server: str, paths: list[str]) -> None:
    for p in paths:
        print(p)
        img = cv2.imread(p)
        if img is None:
            print("  Not an image")
            continue
        send(server, cv2.imencode(".jpg", img)[1].tobytes())


def scan_webcam(server: str, camera: int) -> None:
    cap = cv2.VideoCapture(camera)
    if not cap.isOpened():
        sys.exit(f"Cannot open camera {camera}")
    # Ask for a higher resolution so small barcodes stay readable.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print("Hold a barcode up to the camera. SPACE = scan, Q = quit.")
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        cv2.imshow("Simulated scanner (SPACE = scan, Q = quit)", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            print("Scanning...")
            send(server, cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes())
        elif key in (ord("q"), 27):
            break
    cap.release()
    cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("images", nargs="*", help="image files to send (default: use the webcam)")
    parser.add_argument("--server", default="http://127.0.0.1:8000")
    parser.add_argument("--camera", type=int, default=0)
    args = parser.parse_args()
    server = args.server.rstrip("/")
    if args.images:
        scan_files(server, args.images)
    else:
        scan_webcam(server, args.camera)


if __name__ == "__main__":
    main()
