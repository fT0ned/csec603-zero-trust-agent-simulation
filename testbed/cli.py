import argparse
import json
import sys
from .runner import run_batch, manifest
from .common import write_json
from .power import keep_awake

def main():
    parser=argparse.ArgumentParser(description='Real enterprise testbed runner')
    parser.add_argument('command',choices=['run','manifest'])
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();config=json.load(open(args.config,encoding='utf-8-sig'))
    try:
        if args.command=='manifest': write_json(args.output,{'cells':manifest(config),'count':len(manifest(config))});return 0
        with keep_awake(): result=run_batch(config,args.output)
        return 0 if not result['failures'] else 2
    except Exception as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr);return 1

if __name__=='__main__': sys.exit(main())
