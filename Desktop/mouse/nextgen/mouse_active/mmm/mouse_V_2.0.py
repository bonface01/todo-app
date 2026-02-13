"""
BonfaceTech :: DarkCursor Core
Hacky-looking mouse mover / scroll helper (SAFE + VISUAL ONLY)
"""

import random
import time
import sys
import pyautogui

# ================== CONFIG ==================
HOVER_INTERVAL_SECONDS = 5
SCROLL_INTERVAL_SECONDS = 15

HOVER_DELTA_PIXELS = 25
SCROLL_RANGE = (80, 250)

USER_MOVE_THRESHOLD = 5
USER_IDLE_GRACE_SECONDS = 3

pyautogui.FAILSAFE = True

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

STEALTH_MESSAGES = [
    "Bypassing idle watchdog...",
    "Evading sleep daemon...",
    "Masking automation signature...",
    "Injecting human entropy...",
    "Cursor control hijacked...",
]

# ================== FX ==================
def typewriter(text, delay=0.02):
    for c in text:
        sys.stdout.write(c)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def fake_encrypt():
    chars = "01ABCDEF"
    sys.stdout.write(GREEN + "[ENC] ")
    for _ in range(28):
        sys.stdout.write(random.choice(chars))
        sys.stdout.flush()
        time.sleep(0.03)
    print(RESET)

def banner():
    print(GREEN + r"""
██████╗  ██████╗ ███╗   ██╗███████╗ █████╗ ███████╗████████╗
██╔══██╗██╔═══██╗████╗  ██║██╔════╝██╔══██╗██╔════╝╚══██╔══╝
██████╔╝██║   ██║██╔██╗ ██║█████╗  ███████║███████╗   ██║
██╔══██╗██║   ██║██║╚██╗██║██╔══╝  ██╔══██║╚════██║   ██║
██████╔╝╚██████╔╝██║ ╚████║██║     ██║  ██║███████║   ██║
╚═════╝  ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝
        DARKCURSOR :: CONTROL MODULE
""" + RESET)

# ================== CORE ==================
def hover_once():
    dx = random.randint(-HOVER_DELTA_PIXELS, HOVER_DELTA_PIXELS)
    dy = random.randint(-HOVER_DELTA_PIXELS, HOVER_DELTA_PIXELS)
    if dx == 0 and dy == 0:
        dx = random.choice([-1, 1])
    pyautogui.move(dx, dy, duration=0.15)
    print(GREEN + f"[SYS] Cursor vector Δ({dx},{dy}) injected" + RESET)

def scroll_once():
    amount = random.randint(*SCROLL_RANGE)
    direction = random.choice([-1, 1])
    pyautogui.scroll(direction * amount)
    label = "UP" if direction > 0 else "DOWN"
    print(GREEN + f"[IO] Scroll packet {label}:{amount}" + RESET)

def main():
    banner()
    typewriter("[+] Booting BonfaceTech DarkCursor Core...")
    typewriter("[+] Establishing low-level cursor hooks...")
    typewriter("[+] STATUS: ACCESS GRANTED\n")
    fake_encrypt()

    next_hover = time.time() + HOVER_INTERVAL_SECONDS
    next_scroll = time.time() + SCROLL_INTERVAL_SECONDS
    last_pos = pyautogui.position()
    last_user_move = time.time()

    try:
        while True:
            now = time.time()
            pos = pyautogui.position()

            if (
                abs(pos[0] - last_pos[0]) > USER_MOVE_THRESHOLD
                or abs(pos[1] - last_pos[1]) > USER_MOVE_THRESHOLD
            ):
                last_user_move = now

            last_pos = pos

            if now - last_user_move < USER_IDLE_GRACE_SECONDS:
                time.sleep(0.5)
                continue

            if now >= next_hover:
                hover_once()
                next_hover = now + HOVER_INTERVAL_SECONDS

            if now >= next_scroll:
                scroll_once()
                next_scroll = now + SCROLL_INTERVAL_SECONDS

            if random.random() < 0.08:
                print(GREEN + "[STEALTH] " + random.choice(STEALTH_MESSAGES) + RESET)

            wait = min(next_hover, next_scroll) - time.time()
            if wait > 0:
                time.sleep(wait)

    except KeyboardInterrupt:
        print(RED + "[EXIT] Manual interrupt detected" + RESET)
    except pyautogui.FailSafeException:
        print(RED + "[EXIT] FAILSAFE TRIGGERED" + RESET)
    finally:
        print(GREEN + "[SHUTDOWN] BonfaceTech DarkCursor disengaged" + RESET)

if __name__ == "__main__":
    main()
