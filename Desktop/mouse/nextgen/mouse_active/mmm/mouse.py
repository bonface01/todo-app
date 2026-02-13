"""
Mouse mover/scroll helper to keep the machine awake.
Scrolls every 15 seconds and hovers every 5 seconds.
Pauses while you are actively moving the mouse (recent movement within a short window).
"""

import random
import time

import pyautogui

# Fixed intervals
HOVER_INTERVAL_SECONDS = 5
SCROLL_INTERVAL_SECONDS = 15

# Motion tuning
HOVER_DELTA_PIXELS = 25            # max distance to nudge in any direction
SCROLL_RANGE = (80, 250)           # min/max scroll amount (positive int)

# User activity detection
USER_MOVE_THRESHOLD = 5            # pixels of movement counted as user activity
USER_IDLE_GRACE_SECONDS = 3        # wait this long after user movement before acting

pyautogui.FAILSAFE = True  # flinging to a corner aborts for safety


def hover_once():
    """Move within a small box around the current cursor position."""
    dx = random.randint(-HOVER_DELTA_PIXELS, HOVER_DELTA_PIXELS)
    dy = random.randint(-HOVER_DELTA_PIXELS, HOVER_DELTA_PIXELS)
    # Avoid a no-op move
    if dx == 0 and dy == 0:
        dx = random.choice([-1, 1])
    pyautogui.move(dx, dy, duration=0.15)
    print(f"Hovered by ({dx},{dy}).")


def scroll_once():
    """Scroll up or down by a random amount."""
    amount = random.randint(*SCROLL_RANGE)
    direction = random.choice([-1, 1])
    pyautogui.scroll(direction * amount)
    direction_label = "up" if direction > 0 else "down"
    print(f"Scrolled {direction_label} by {amount} units.")


def main():
    print(
        "[1]Starting mouse mover: hover every "
        f"{HOVER_INTERVAL_SECONDS}s, scroll every {SCROLL_INTERVAL_SECONDS}s. Ctrl+C to stop #THIS IS A BonfaceTech property."
    )
    print("[2]Failsafe also triggers by slamming the mouse to a corner.")

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

            # If user recently moved, pause actions
            if now - last_user_move < USER_IDLE_GRACE_SECONDS:
                time.sleep(0.5)
                continue

            if now >= next_hover:
                hover_once()
                next_hover = now + HOVER_INTERVAL_SECONDS

            if now >= next_scroll:
                scroll_once()
                next_scroll = now + SCROLL_INTERVAL_SECONDS

            # Sleep until the next scheduled action
            wait = min(next_hover, next_scroll) - time.time()
            if wait > 0:
                time.sleep(wait)

    except KeyboardInterrupt:
        print("[Exit_code 1]You Stopped this program by [ctrl + c].")
    except pyautogui.FailSafeException:
        print("[Exit_code 2]You Stopped this program by failsafe [mouse moved to a corner].")
    finally:
        print("[Exit_code 0]Thanks for trusting BonfaceTechTools.")


if __name__ == "__main__":
    main()
