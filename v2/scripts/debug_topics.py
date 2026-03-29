#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from topic_cluster import TopicCluster, load_atoms_from_jsonl

V2_ROOT = Path('/Users/yangliu/Documents/Claude Code/codebuddy/tech-daily-brief/v2')

# 加载atoms
date_dir = V2_ROOT / "archive" / "daily" / "2026-03-23"
atoms = []
for ch in ['weibo', 'x', 'rss']:
    atoms.extend(load_atoms_from_jsonl(date_dir / f"{ch}.jsonl"))

print(f"Total atoms: {len(atoms)}")

# 聚类
cluster = TopicCluster()
topics = cluster.cluster_atoms(atoms)

# 检查特定话题
print("\nDetails for 'AnthropicC Claude Code 新增 Channels功能':")
for topic in topics:
    if 'AnthropicC' in topic.name:
        print(f"Topic: {topic.name}")
        print(f"  ID: {topic.id}")
        print(f"  Main entity: {getattr(topic, 'main_entity', None)}")
        print(f"  Action: {getattr(topic, 'action', None)}")
        print(f"  Atoms: {len(topic.atoms)}")
        all_text = " ".join([(a.title or "") + " " + (a.summary or "") for a in topic.atoms])
        print(f"  Combined text (first 200 chars): {all_text[:200]}...")
        
        # 重新生成名称
        new_name = cluster.generate_topic_name(getattr(topic, 'main_entity', 'unknown'), getattr(topic, 'action', None), topic.atoms)
        print(f"  Regenerated name: {new_name}")
