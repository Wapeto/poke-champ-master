#!/usr/bin/env python3
"""Start the Pokemon Champions Advisor web app."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))

from app.main import app

if __name__ == "__main__":
    print("Starting Pokemon Champions Advisor at http://localhost:5000")
    app.run(debug=True, port=5000)
