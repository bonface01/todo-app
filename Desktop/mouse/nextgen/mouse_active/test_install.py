
"""
Test PyAutoGUI installation and basic functionality
"""

import sys
import time

print("Testing PyAutoGUI Installation...")
print("=" * 50)

try:
    import pyautogui
    
    print("✓ PyAutoGUI imported successfully")
    
    # Test basic functions
    width, height = pyautogui.size()
    print(f"✓ Screen detected: {width}x{height}")
    
    x, y = pyautogui.position()
    print(f"✓ Mouse position: ({x}, {y})")
    
    print("\nTesting mouse movement (will move slightly)...")
    
    # Small test movement
    pyautogui.moveRel(10, 10, duration=0.3)
    time.sleep(0.5)
    pyautogui.moveRel(-10, -10, duration=0.3)
    
    print("✓ Mouse movement test passed")
    
    print("\nAll tests passed successfully!")
    print("\nYou can now run:")
    print("  python mousemover.py     - For interactive mode")
    print("  python launcher.py       - For menu launcher")
    
except ImportError:
    print("✗ PyAutoGUI not installed!")
    print("\nInstalling PyAutoGUI...")
    
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        print("\n✓ PyAutoGUI installed successfully!")
        print("Please run this test again.")
    except:
        print("\n✗ Installation failed. Please install manually:")
        print("  pip install pyautogui")
        
except Exception as e:
    print(f"\n✗ Test failed with error: {e}")
    print("\nPlease ensure:")
    print("1. You're not running as Administrator")
    print("2. Your display is not locked")
    print("3. You have mouse permissions")

input("\nPress Enter to exit...")