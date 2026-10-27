"""RAVEN version information."""

MAJOR = 0
MINOR = 1
MICRO = 0

VERSION = f"{MAJOR}.{MINOR}.{MICRO}"

__version__ = VERSION

def get_versions():
    return {"version": VERSION}