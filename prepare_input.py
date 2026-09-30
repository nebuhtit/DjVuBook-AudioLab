import argparse
from input_source import resolve_source
p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');a=p.parse_args()
path,kind=resolve_source(a.source,a.output)
print(path)
