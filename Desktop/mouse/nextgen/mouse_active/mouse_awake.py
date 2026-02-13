# Save as: mousemover.py
"""
BonfaceTech Mouse Mover Pro - Complete Python Solution
Advanced screen activity simulator with multiple modes and features.
"""

import random
import time
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import threading
from typing import Optional, Dict, Any

try:
    import pyautogui
except ImportError:
    print("Installing required package: pyautogui...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
    import pyautogui

# ============================================================================
# CONFIGURATION CLASS
# ============================================================================

class Config:
    """Configuration manager for Mouse Mover"""
    
    DEFAULT_CONFIG = {
        "hover_interval": 5,
        "scroll_interval": 15,
        "click_interval": 120,
        "hover_delta": 25,
        "scroll_range": [80, 250],
        "user_move_threshold": 5,
        "user_idle_grace": 3,
        "mode": "human",  # simple, human, random, pattern
        "log_to_file": True,
        "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
        "enable_sounds": False,
        "auto_start": False,
        "patterns": {
            "figure8": [(0, 0), (20, 20), (0, 40), (-20, 20), (0, 0)],
            "square": [(0, 0), (30, 0), (30, 30), (0, 30), (0, 0)],
            "triangle": [(0, 0), (25, 15), (-25, 15), (0, 0)]
        }
    }
    
    def __init__(self, config_file: str = "mousemover_config.json"):
        self.config_file = Path(config_file)
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(user_config)
                    return config
            except Exception as e:
                print(f"Error loading config: {e}, using defaults")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()

# ============================================================================
# LOGGER CLASS
# ============================================================================

class Logger:
    """Simple logging system"""
    
    COLORS = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, log_to_file=True, log_level="INFO"):
        self.log_to_file = log_to_file
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        self.current_level = log_level.upper()
        
        if log_to_file:
            self.log_dir = Path("logs")
            self.log_dir.mkdir(exist_ok=True)
            self.log_file = self.log_dir / f"mousemover_{datetime.now().strftime('%Y%m%d')}.log"
        else:
            self.log_file = None
    
    def should_log(self, level: str) -> bool:
        """Check if message should be logged based on level"""
        return self.log_levels.index(level) >= self.log_levels.index(self.current_level)
    
    def log(self, level: str, message: str):
        """Log a message"""
        level = level.upper()
        
        if not self.should_log(level):
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        # Console output with colors
        color = self.COLORS.get(level, self.COLORS['RESET'])
        print(f"{color}{log_msg}{self.COLORS['RESET']}")
        
        # File output
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_msg + '\n')
    
    def debug(self, message: str):
        self.log("DEBUG", message)
    
    def info(self, message: str):
        self.log("INFO", message)
    
    def warning(self, message: str):
        self.log("WARNING", message)
    
    def error(self, message: str):
        self.log("ERROR", message)

# ============================================================================
# MOVEMENT ENGINE
# ============================================================================

class MovementEngine:
    """Handles all mouse movement logic"""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.screen_width, self.screen_height = pyautogui.size()
        self.current_pos = pyautogui.position()
        
        # Safety settings
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1
        
    def move_simple(self):
        """Simple hover movement (original algorithm)"""
        dx = random.randint(-self.config.get("hover_delta"), self.config.get("hover_delta"))
        dy = random.randint(-self.config.get("hover_delta"), self.config.get("hover_delta"))
        
        if dx == 0 and dy == 0:
            dx = random.choice([-1, 1])
            
        pyautogui.move(dx, dy, duration=0.15)
        self.current_pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
        self.logger.debug(f"Simple hover: ({dx}, {dy})")
        return dx, dy
    
    def move_human(self):
        """Human-like natural movement"""
        # Choose movement type
        move_type = random.choices(
            ['smooth', 'click_drag', 'micro_adjust'],
            weights=[0.6, 0.2, 0.2]
        )[0]
        
        if move_type == 'smooth':
            self._smooth_move()
        elif move_type == 'click_drag':
            self._click_and_drag()
        else:
            self._micro_adjust()
    
    def _smooth_move(self):
        """Smooth, natural mouse movement"""
        steps = random.randint(5, 12)
        dx_total = random.randint(-self.config.get("hover_delta"), self.config.get("hover_delta"))
        dy_total = random.randint(-self.config.get("hover_delta"), self.config.get("hover_delta"))
        
        for i in range(steps):
            progress = i / steps
            # Cubic easing for natural motion
            ease = 1 - (1 - progress) ** 3
            
            dx = int(dx_total * ease)
            dy = int(dy_total * ease)
            
            target_x = max(10, min(self.current_pos[0] + dx, self.screen_width - 10))
            target_y = max(10, min(self.current_pos[1] + dy, self.screen_height - 10))
            
            pyautogui.moveTo(target_x, target_y, duration=0.2/steps)
            time.sleep(0.02)
        
        self.current_pos = pyautogui.position()
        self.logger.debug(f"Smooth move completed")
    
    def _click_and_drag(self):
        """Simulate click and drag action"""
        if random.random() < 0.3:  # 30% chance of drag
            start_x, start_y = self.current_pos
            dx = random.randint(-30, 30)
            dy = random.randint(-30, 30)
            
            pyautogui.mouseDown()
            pyautogui.moveTo(start_x + dx, start_y + dy, duration=0.3)
            time.sleep(0.1)
            pyautogui.mouseUp()
            
            self.current_pos = pyautogui.position()
            self.logger.debug(f"Click and drag: ({dx}, {dy})")
    
    def _micro_adjust(self):
        """Small, subtle adjustments"""
        dx = random.randint(-5, 5)
        dy = random.randint(-5, 5)
        pyautogui.move(dx, dy, duration=0.1)
        self.current_pos = (self.current_pos[0] + dx, self.current_pos[1] + dy)
    
    def smart_scroll(self):
        """Intelligent scrolling simulation"""
        # Simulate different scrolling behaviors
        scroll_type = random.choices(
            ['read', 'browse', 'quick'],
            weights=[0.5, 0.3, 0.2]
        )[0]
        
        if scroll_type == 'read':
            # Slow, steady scrolling (like reading)
            amount = random.randint(80, 150)
            pulses = random.randint(2, 4)
            for _ in range(pulses):
                pyautogui.scroll(amount // pulses)
                time.sleep(0.2)
            self.logger.debug(f"Reading scroll: {amount} units")
            
        elif scroll_type == 'browse':
            # Quick browsing scrolls
            amount = random.randint(150, 250)
            direction = random.choice([-1, 1])
            pyautogui.scroll(direction * amount)
            self.logger.debug(f"Browsing scroll: {amount} units")
            
        else:  # quick
            # Very quick scroll
            amount = random.randint(50, 100)
            pyautogui.scroll(amount)
            time.sleep(0.05)
            pyautogui.scroll(-amount // 2)  # Small bounce back
            self.logger.debug(f"Quick scroll: {amount} units")
    
    def occasional_click(self):
        """Realistic occasional clicking"""
        # Determine click type
        click_type = random.choices(
            ['left', 'right', 'middle', 'double'],
            weights=[0.65, 0.25, 0.05, 0.05]
        )[0]
        
        if click_type == 'double':
            pyautogui.doubleClick()
        else:
            pyautogui.click(button=click_type)
        
        self.logger.debug(f"{click_type.capitalize()} click performed")

# ============================================================================
# MAIN MOUSE MOVER CLASS
# ============================================================================

class MouseMoverPro:
    """Main Mouse Mover Application"""
    
    def __init__(self, config_file="mousemover_config.json"):
        self.config = Config(config_file)
        self.logger = Logger(
            log_to_file=self.config.get("log_to_file"),
            log_level=self.config.get("log_level")
        )
        self.engine = MovementEngine(self.config, self.logger)
        
        # State
        self.running = False
        self.last_user_pos = pyautogui.position()
        self.next_hover = 0
        self.next_scroll = 0
        self.next_click = 0
        
        self.logger.info("=" * 60)
        self.logger.info("BonfaceTech Mouse Mover Pro - Initialized")
        self.logger.info(f"Screen: {self.engine.screen_width}x{self.engine.screen_height}")
        self.logger.info(f"Mode: {self.config.get('mode').upper()}")
        self.logger.info("=" * 60)
    
    def check_user_activity(self) -> bool:
        """Check if user has moved mouse recently"""
        current_pos = pyautogui.position()
        threshold = self.config.get("user_move_threshold")
        
        if (abs(current_pos[0] - self.last_user_pos[0]) > threshold or
            abs(current_pos[1] - self.last_user_pos[1]) > threshold):
            self.last_user_pos = current_pos
            self.engine.current_pos = current_pos
            return True
        return False
    
    def display_status(self):
        """Display current status information"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n" + "=" * 60)
        print(" " * 20 + "BONFACETECH MOUSE MOVER PRO")
        print("=" * 60)
        print(f"\nStatus: {'RUNNING' if self.running else 'STOPPED'}")
        print(f"Mode: {self.config.get('mode').upper()}")
        print(f"Position: {pyautogui.position()}")
        print(f"Screen: {self.engine.screen_width}x{self.engine.screen_height}")
        print("\nControls:")
        print("  [P] Pause/Resume")
        print("  [M] Change Mode")
        print("  [S] Change Speed")
        print("  [C] Show Config")
        print("  [Q] Quit")
        print("\n" + "=" * 60)
    
    def show_menu(self):
        """Display interactive menu"""
        while True:
            self.display_status()
            
            if not self.running:
                choice = input("\nPress [S] to start or [Q] to quit: ").upper()
                if choice == 'S':
                    self.start()
                elif choice == 'Q':
                    break
                continue
            
            choice = input("\nEnter command (P/M/S/C/Q): ").upper()
            
            if choice == 'P':
                self.running = not self.running
                self.logger.info(f"{'Paused' if not self.running else 'Resumed'}")
            elif choice == 'M':
                self.change_mode()
            elif choice == 'S':
                self.change_speed()
            elif choice == 'C':
                self.show_config()
            elif choice == 'Q':
                self.stop()
                break
    
    def change_mode(self):
        """Change movement mode interactively"""
        print("\nSelect Movement Mode:")
        print("  1. Simple (Original)")
        print("  2. Human (Natural)")
        print("  3. Random")
        print("  4. Pattern")
        
        choice = input("Enter choice (1-4): ")
        modes = {1: "simple", 2: "human", 3: "random", 4: "pattern"}
        
        if choice.isdigit() and int(choice) in modes:
            self.config.set("mode", modes[int(choice)])
            self.logger.info(f"Mode changed to: {modes[int(choice)].upper()}")
    
    def change_speed(self):
        """Change movement intervals"""
        print("\nCurrent intervals:")
        print(f"  Hover: {self.config.get('hover_interval')}s")
        print(f"  Scroll: {self.config.get('scroll_interval')}s")
        print(f"  Click: {self.config.get('click_interval')}s")
        
        try:
            hover = input("New hover interval (seconds): ")
            scroll = input("New scroll interval (seconds): ")
            
            if hover:
                self.config.set("hover_interval", int(hover))
            if scroll:
                self.config.set("scroll_interval", int(scroll))
                
            self.logger.info(f"Intervals updated")
        except ValueError:
            self.logger.error("Invalid input")
    
    def show_config(self):
        """Display current configuration"""
        print("\nCurrent Configuration:")
        for key, value in self.config.config.items():
            if key != "patterns":
                print(f"  {key}: {value}")
    
    def start(self):
        """Start the mouse mover"""
        self.running = True
        now = time.time()
        self.next_hover = now + self.config.get("hover_interval")
        self.next_scroll = now + self.config.get("scroll_interval")
        self.next_click = now + self.config.get("click_interval")
        
        self.logger.info("Mouse Mover STARTED")
        self.logger.info("Move mouse to any corner to trigger failsafe")
        
        self.main_loop()
    
    def stop(self):
        """Stop the mouse mover"""
        self.running = False
        self.logger.info("Mouse Mover STOPPED")
    
    def main_loop(self):
        """Main execution loop"""
        last_activity_check = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Check user activity every second
                if current_time - last_activity_check >= 1:
                    if self.check_user_activity():
                        # User is active, delay next actions
                        grace = self.config.get("user_idle_grace")
                        self.next_hover = current_time + grace + self.config.get("hover_interval")
                        self.next_scroll = current_time + grace + self.config.get("scroll_interval")
                        self.next_click = current_time + grace + self.config.get("click_interval")
                        self.logger.debug("User activity detected - delaying automation")
                    last_activity_check = current_time
                
                # Execute scheduled actions
                if current_time >= self.next_hover:
                    mode = self.config.get("mode")
                    
                    if mode == "simple":
                        self.engine.move_simple()
                    elif mode == "human":
                        self.engine.move_human()
                    elif mode == "random":
                        self.engine.move_simple()  # For now, same as simple
                    elif mode == "pattern":
                        self.engine.move_simple()  # Placeholder for pattern
                    
                    self.next_hover = current_time + self.config.get("hover_interval")
                
                if current_time >= self.next_scroll:
                    if random.random() < 0.7:  # 70% chance to scroll
                        self.engine.smart_scroll()
                    self.next_scroll = current_time + self.config.get("scroll_interval")
                
                if current_time >= self.next_click:
                    if random.random() < 0.3:  # 30% chance to click
                        self.engine.occasional_click()
                    self.next_click = current_time + random.randint(
                        self.config.get("click_interval") // 2,
                        self.config.get("click_interval") * 2
                    )
                
                # Sleep to prevent CPU overuse
                next_action = min(self.next_hover, self.next_scroll, self.next_click)
                sleep_time = max(0.1, min(next_action - current_time, 1))
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            self.logger.info("Stopped by user (Ctrl+C)")
        except pyautogui.FailSafeException:
            self.logger.info("Failsafe triggered! Mouse moved to corner")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
        finally:
            self.stop()

# ============================================================================
# COMMAND LINE INTERFACE
# ============================================================================

def parse_arguments():
    """Parse command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="BonfaceTech Mouse Mover Pro - Prevent screen lock",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python mousemover.py            # Interactive menu mode
  python mousemover.py --auto     # Auto-start with current config
  python mousemover.py --mode human --hover 10 --scroll 30
  python mousemover.py --silent   # Run without interactive menu
        """
    )
    
    parser.add_argument("--auto", action="store_true", help="Auto-start the mover")
    parser.add_argument("--silent", action="store_true", help="Run without menu")
    parser.add_argument("--mode", choices=["simple", "human", "random", "pattern"],
                       default="human", help="Movement mode")
    parser.add_argument("--hover", type=int, help="Hover interval in seconds")
    parser.add_argument("--scroll", type=int, help="Scroll interval in seconds")
    parser.add_argument("--config", default="mousemover_config.json",
                       help="Configuration file path")
    
    return parser.parse_args()

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Create or update config with CLI args
    config = Config(args.config)
    
    if args.mode:
        config.set("mode", args.mode)
    if args.hover:
        config.set("hover_interval", args.hover)
    if args.scroll:
        config.set("scroll_interval", args.scroll)
    
    # Create the mouse mover
    mover = MouseMoverPro(args.config)
    
    # Run based on arguments
    if args.auto:
        mover.start()
    elif args.silent:
        mover.start()
        try:
            while mover.running:
                time.sleep(1)
        except KeyboardInterrupt:
            mover.stop()
    else:
        mover.show_menu()
    
    mover.logger.info("=" * 60)
    mover.logger.info("Thanks for trusting BonfaceTech Tools!")
    mover.logger.info("=" * 60)

if __name__ == "__main__":
    main()