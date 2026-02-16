import argparse
import os
import sys
import threading


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", default=os.path.expanduser("~/.dont-rust-bro"))
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    from drb.daemon import DaemonServer

    server = DaemonServer(args.state_dir, headless=args.headless)

    if args.headless:
        server.serve_forever()
    else:
        # Start socket server in background thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # Run GUI in main thread (required by pywebview)
        from drb.gui import PracticeWindow

        packs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "packs")
        if not os.path.isdir(packs_dir):
            packs_dir = os.path.join(args.state_dir, "packs")

        gui = PracticeWindow(state_dir=args.state_dir, packs_dir=packs_dir)
        server.set_gui(gui)
        gui.run()

        # GUI exited, stop server
        server.shutdown()


if __name__ == "__main__":
    main()
