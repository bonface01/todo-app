
"""
Simple launcher for Mouse Mover
"""

import os
import sys

def main():
    print("BonfaceTech Mouse Mover Launcher")
    print("=" * 40)
    print("\nChoose an option:")
    print("1. Start Interactive Mode")
    print("2. Start Auto Mode")
    print("3. Start Silent Mode")
    print("4. Test Installation")
    print("5. Exit")
    
    choice = input("\nEnter your choice (1-5): ")
    
    if choice == "1":
        os.system("python mousemover.py")
    elif choice == "2":
        os.system("python mousemover.py --auto")
    elif choice == "3":
        os.system("python mousemover.py --silent")
    elif choice == "4":
        os.system("python test_install.py")
    elif choice == "5":
        print("Goodbye! But do not go with guilt of not testing BonfaceTech Tools")
    else:
        print("Invalid choice!")

if __name__ == "__main__":
    main()