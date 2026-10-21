import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import unittest
from pathlib import Path


class MainTest(unittest.TestCase):
    def test_main_exits_successfully_without_output(self) -> None:
        game = Path(__file__).resolve().parents[1] / "main.py"
        result = subprocess.run(
            [sys.executable, str(game)], capture_output=True, text=True, check=False
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_paints_maze_and_restores_terminal_on_resize_or_ctrl_c(self) -> None:
        game = Path(__file__).resolve().parents[1] / "main.py"
        for exit_signal in (signal.SIGWINCH, signal.SIGINT):
            with self.subTest(exit_signal=exit_signal):
                master, slave = pty.openpty()
                fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 12, 40, 0, 0))
                original_settings = termios.tcgetattr(slave)
                process = subprocess.Popen(
                    [sys.executable, str(game)],
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                    env={**os.environ, "TERM": "xterm-256color"},
                )
                output = b""
                try:
                    deadline = time.monotonic() + 2
                    while b"\x1b[42m" not in output and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.05)[0]:
                            output += os.read(master, 65536)
                    self.assertIn(b"\x1b[42m", output)
                    self.assertIn(b"\x1b[41m", output)
                    for color in (
                        b"\x1b[40m",
                        b"\x1b[47m",
                        b"\x1b[42m",
                        b"\x1b[41m",
                    ):
                        self.assertIn(color, output)

                    if exit_signal == signal.SIGWINCH:
                        fcntl.ioctl(
                            slave, termios.TIOCSWINSZ, struct.pack("HHHH", 20, 60, 0, 0)
                        )
                    process.send_signal(exit_signal)
                    deadline = time.monotonic() + 2
                    while process.poll() is None and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.05)[0]:
                            output += os.read(master, 65536)
                    while select.select([master], [], [], 0)[0]:
                        try:
                            output += os.read(master, 65536)
                        except OSError:
                            break

                    self.assertEqual(process.poll(), 0)
                    if exit_signal == signal.SIGWINCH:
                        self.assertIn(b"Exiting because the terminal was resized.", output)
                    else:
                        self.assertNotIn(b"Exiting because the terminal was resized.", output)
                    self.assertIn(b"\x1b[?1049l", output)
                    self.assertNotIn(b"Traceback", output)
                    restored_settings = termios.tcgetattr(slave)
                    original_settings[3] &= ~termios.PENDIN
                    restored_settings[3] &= ~termios.PENDIN
                    self.assertEqual(restored_settings, original_settings)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait()
                    os.close(master)
                    os.close(slave)

    def test_too_small_terminal_exits_with_size_requirement(self) -> None:
        game = Path(__file__).resolve().parents[1] / "main.py"
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 4, 4, 0, 0))
        process = subprocess.Popen(
            [sys.executable, str(game)],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            env={**os.environ, "TERM": "xterm-256color"},
        )
        output = b""
        try:
            deadline = time.monotonic() + 2
            while process.poll() is None and time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    output += os.read(master, 65536)
            while select.select([master], [], [], 0)[0]:
                try:
                    output += os.read(master, 65536)
                except OSError:
                    break

            self.assertEqual(process.poll(), 1)
            self.assertIn(b"Terminal must be at least 9 rows and 10 columns.", output)
            self.assertIn(b"\x1b[?1049l", output)
            self.assertNotIn(b"Traceback", output)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)


if __name__ == "__main__":
    unittest.main()
