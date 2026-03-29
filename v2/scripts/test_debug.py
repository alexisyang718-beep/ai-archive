#!/usr/bin/env python3
import importlib
import topic_cluster
importlib.reload(topic_cluster)

from topic_cluster import TopicCluster, load_atoms_from_jsonl
from pathlib import Path

atoms = load_atoms_from_jsonl(Path('../archive/daily/2026-03-23/x.jsonl'))
weibo_atoms = load_atoms_from_jsonl(Path('../archive/daily/2026-03-23/weibo.jsonl'))
rss_atoms = load_atoms_from_jsonl(Path('../archive/daily/2026-03-23/rss.jsonl'))
all_atoms = atoms + weibo_atoms + rss_atoms

cluster = TopicCluster()

for atom in all_atoms:
    text = atom.title + ' ' + atom.summary
    if 'zuckerberg' in text.lower():
        entities, main_entity, action, event_sig = cluster.extract_topic_signature(text)
        if main_entity == 'zuckerberg' and not event_sig:
            print(f'Atom: {atom.title[:50]}')
            print(f'  Category: {atom.category}')
            name = cluster.generate_topic_name(main_entity, action, [atom])
            print(f'  Name: {name}')
            print()
