"""Windows launcher for the PDF to DXF local app."""

from __future__ import annotations

import argparse
import socket
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer

from pdf_to_dxf.server import PdfToDxfHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PDF to DXF as a local Windows app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    port = choose_port(args.host, args.port)
    server = ThreadingHTTPServer((args.host, port), PdfToDxfHandler)
    url = f"http://{args.host}:{port}/"
    print("PDF to DXF is running.")
    print(f"Open: {url}")
    print("Close this window or press Ctrl+C to stop.")

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping PDF to DXF...")
    finally:
        server.server_close()


def choose_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 25):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if probe.connect_ex((host, port)) != 0:
                return port
    raise RuntimeError(f"No free port found from {preferred_port} to {preferred_port + 24}.")


def open_browser(url: str) -> None:
    time.sleep(0.8)
    webbrowser.open(url)


if __name__ == "__main__":
    main()
