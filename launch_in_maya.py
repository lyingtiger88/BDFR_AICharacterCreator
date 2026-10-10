"""Launch this project from Maya Script Editor after setting REPO_PATH."""
import sys

REPO_PATH = r"D:\Projects\BDFR_AICharacterCreator"
if REPO_PATH not in sys.path:
    sys.path.insert(0, REPO_PATH)

from bdfr_character_creator import show

show()
