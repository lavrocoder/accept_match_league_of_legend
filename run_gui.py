#!/usr/bin/env python
"""
Entry point for the GUI application.
Run this file to start the graphical interface.
"""

from app.services.auto_match_gui import run_gui

if __name__ == '__main__':
    try:
        run_gui()
    except KeyboardInterrupt:
        print("Exit")
