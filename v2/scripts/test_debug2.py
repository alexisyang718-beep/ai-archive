#!/usr/bin/env python3
from topic_cluster import TopicCluster, load_atoms_from_jsonl
from pathlib import Path

atoms = load_atoms_from_jsonl(Path('../archive/daily/2026-03-23/x.jsonl'))
weibo_atoms = load_atoms_from_jsonl(Path('../archive/daily/2026-03-23/weibo.jsonl'))
rss_atoms = load_atoms_from_jsonl(Path('../archive/daily/2026-03-23/rss.jsonl'))
all_atoms = atoms + weibo_atoms + rss_atoms

cluster = TopicCluster()

for atom in all_atoms:
    text = atom.title + ' ' + atom.summary
    if 'zuckerberg' in text.lower() and atom.category == 'ai_models':
        entities, main_entity, action, event_sig = cluster.extract_topic_signature(text)
        print(f'Processing: {atom.id}')
        print(f'  Title: {atom.title[:50]}')
        print(f'  Main: {main_entity}, Action: {action}, Event: {event_sig}')
        
        # 尝试找匹配的话题
        matched = False
        for tid, topic in cluster.topics.items():
            if topic.category == atom.category:
                overlap = len(entities & topic.keywords)
                if action and hasattr(topic, 'action') and topic.action == action:
                    overlap += 10
                if event_sig and hasattr(topic, 'event_signature') and topic.event_signature == event_sig:
                    overlap = 100
                    matched = True
                    print(f'  -> Matched to existing topic: {topic.name}')
                    break
        
        if not matched:
            name = cluster.generate_topic_name(main_entity, action, [atom])
            print(f'  -> Creating new topic: {name}')
        print()
        
        # 实际执行聚类
        cluster.find_or_create_topic(atom)
