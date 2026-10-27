"""Validate two real annotation submissions without opening any forecast outcomes."""
import argparse
import json
from pathlib import Path
from eventx.v6.link_audit import validate_reviews

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet",type=Path)
    parser.add_argument("reviewer_a",type=Path)
    parser.add_argument("reviewer_b",type=Path)
    args=parser.parse_args()
    read=lambda p:[json.loads(line) for line in p.open()]
    print(json.dumps(validate_reviews(read(args.packet),read(args.reviewer_a),read(args.reviewer_b)),indent=2))

if __name__ == "__main__": main()
