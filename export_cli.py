import argparse
from epub_export import export_epub
from markdown_export import save_markdown

p=argparse.ArgumentParser();p.add_argument('kind',choices=['md','epub']);p.add_argument('source');p.add_argument('destination');p.add_argument('--title',default='');p.add_argument('--author',default='');a=p.parse_args()
if a.kind=='md':save_markdown(a.source,a.destination)
else:export_epub(a.source,a.destination,a.title,a.author)
