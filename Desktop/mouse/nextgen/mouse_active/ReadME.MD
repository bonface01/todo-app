# 1. Install dependencies
pip install pyautogui

# 2. Test installation
python test_install.py

# 3. Run in different modes:

# Interactive menu mode (recommended)
python mousemover.py

# Or use launcher
python launcher.py

# Auto-start mode
python mousemover.py --auto

# Silent mode (no menu)
python mousemover.py --silent

# With custom settings
python mousemover.py --mode human --hover 10 --scroll 30