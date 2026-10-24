"""python -m easyboard [--port N] [--results DIR] [--no-browser]"""
import argparse
from pathlib import Path
from .server import serve

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int); parser.add_argument('--results', type=Path); parser.add_argument('--no-browser', action='store_true')
args = parser.parse_args()
serve(args.port, args.results, not args.no_browser)
