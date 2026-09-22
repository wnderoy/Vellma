import logging
import sys

def setup_logger(level=logging.INFO, minimal: bool = True):
    """Configures global console logging."""
    if minimal:
        # Format: "name · message" (e.g., "parser · Reading input.dfy")
        fmt = "%(name)-7s · %(message)s"
    else:
        # Structured format for headless batch runs or simulations
        fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)