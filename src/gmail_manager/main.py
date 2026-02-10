if __name__ == "__main__":
    import sys
    import os

    # Add project root to sys.path so absolute imports work
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    )
    from src.gmail_manager.gui import run

    run()
else:
    from .gui import run
