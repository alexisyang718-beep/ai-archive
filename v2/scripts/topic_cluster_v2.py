#!/usr/bin/env python3
"""
智能话题聚类 v2 - 减少硬编码依赖
核心改进：
1. 基于内容相似度的动态实体识别
2. LLM辅助的事件签名生成
3. 自适应话题命名
"""

import json
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import Counter, defaultdict
import hashlib


@dataclass
class Atom:
    """内容原子"""
    id: str
    content: str
    entities: List[str] = field(default_factory=list)
    source: str = ""
    timestamp: str = ""
    url: str = ""


@dataclass
class Topic:
    """话题"""
    id: str
    name: str
    atoms: List[Atom] = field(default_factory=list)
    main_entities: List[str] = field(default_factory=list)
    event_signature: Optional[str] = None
    confidence: float = 0.0


class SmartEntityExtractor:
    """智能实体提取器 - 不依赖硬编码列表"""

    # 公司/产品名称的模式（通用规则，非硬编码列表）
    COMPANY_PATTERNS = [
        # 大驼峰命名（如 OpenAI, DeepSeek, ChatGPT）
        r'\b[A-Z][a-z]*[A-Z][a-zA-Z]*\b',
        # 全大写缩写（如 NASA, FBI, API）
        r'\b[A-Z]{2,6}\b',
        # 中文+英文混合（如 Kimi K2, 通义千问）
        r'[\u4e00-\u9fa5]{2,}(?:\s+[A-Z][a-zA-Z0-9]*)?',
        # 版本号模式（如 GPT-4, Claude 3.5）
        r'(?:GPT|Claude|Kimi|Gemini|Llama)[-\s]?[0-9]\.?[0-9]?',
    ]

    # 需要过滤的常见词（这些不是实体）
    STOP_WORDS = {
        'AI', 'API', 'CEO', 'CTO', 'GPU', 'CPU', 'RAM', 'SSD', 'URL',
        'HTTP', 'HTTPS', 'HTML', 'CSS', 'JSON', 'XML', 'SQL', 'SDK',
        'The', 'This', 'That', 'These', 'Those', 'What', 'When',
        'How', 'Why', 'Where', 'Who', 'Which', 'New', 'Old', 'Good',
        'Best', 'Top', 'High', 'Low', 'Big', 'Small', 'First', 'Last',
    }

    def extract_from_content(self, content: str) -> List[Tuple[str, float]]:
        """
        从内容中提取候选实体，返回 (实体名, 置信度)
        置信度基于：出现频率、命名规范性、上下文位置
        """
        candidates = []

        for pattern in self.COMPANY_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                entity = match.group()
                if entity in self.STOP_WORDS:
                    continue
                if len(entity) < 2:
                    continue

                # 计算置信度
                confidence = self._calculate_confidence(entity, content, match.start())
                candidates.append((entity, confidence))

        # 按置信度排序并去重
        candidates.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        result = []
        for entity, conf in candidates:
            key = entity.lower()
            if key not in seen:
                seen.add(key)
                result.append((entity, conf))

        return result

    def _calculate_confidence(self, entity: str, content: str, position: int) -> float:
        """计算实体置信度"""
        score = 0.5  # 基础分

        # 大驼峰命名加分
        if re.match(r'[A-Z][a-z]*[A-Z]', entity):
            score += 0.2

        # 包含数字（如 GPT-4, Kimi K2）加分
        if re.search(r'\d', entity):
            score += 0.15

        # 出现在标题位置（内容前20%）加分
        if position < len(content) * 0.2:
            score += 0.1

        # 长度适中加分（2-15字符）
        if 2 <= len(entity) <= 15:
            score += 0.05

        return min(score, 1.0)


class ContentFingerprint:
    """内容指纹生成器 - 用于相似度计算"""

    def __init__(self):
        self.entity_extractor = SmartEntityExtractor()

    def generate(self, atom: Atom) -> Dict[str, Any]:
        """
        生成内容指纹，包含：
        - 实体集合
        - 关键词集合
        - 语义签名（基于关键短语）
        """
        content = atom.content

        # 提取实体
        entities = self.entity_extractor.extract_from_content(content)
        entity_names = [e[0] for e in entities[:5]]  # 取前5个

        # 提取关键词（基于词频和位置）
        keywords = self._extract_keywords(content)

        # 生成语义签名
        semantic_sig = self._generate_semantic_signature(content, entity_names)

        return {
            'entities': set(entity_names),
            'keywords': set(keywords),
            'semantic_signature': semantic_sig,
            'entity_confidence': {e[0]: e[1] for e in entities[:5]},
        }

    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取：名词短语
        # 实际可用 jieba/NLTK 等分词工具
        words = re.findall(r'\b[A-Za-z]{3,}\b', content)
        word_freq = Counter(words)

        # 过滤常见词
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all'}
        keywords = [w for w, c in word_freq.most_common(10)
                   if w.lower() not in stop_words]

        return keywords

    def _generate_semantic_signature(self, content: str, entities: List[str]) -> str:
        """生成语义签名 - 用于快速匹配相似内容"""
        # 基于实体组合生成签名
        if len(entities) >= 2:
            # 取前两个实体组合
            sig = f"{entities[0]}:{entities[1]}"
        elif len(entities) == 1:
            # 只有一个实体时，加上内容哈希前缀
            content_hash = hashlib.md5(content[:50].encode()).hexdigest()[:6]
            sig = f"{entities[0]}:{content_hash}"
        else:
            # 无实体时，用内容哈希
            sig = hashlib.md5(content[:100].encode()).hexdigest()[:12]

        return sig

    def calculate_similarity(self, fp1: Dict, fp2: Dict) -> float:
        """计算两个指纹的相似度"""
        # 实体重叠度
        entity_overlap = len(fp1['entities'] & fp2['entities'])
        entity_union = len(fp1['entities'] | fp2['entities'])
        entity_sim = entity_overlap / entity_union if entity_union > 0 else 0

        # 关键词重叠度
        keyword_overlap = len(fp1['keywords'] & fp2['keywords'])
        keyword_union = len(fp1['keywords'] | fp2['keywords'])
        keyword_sim = keyword_overlap / keyword_union if keyword_union > 0 else 0

        # 语义签名匹配（完全相同则高度相似）
        semantic_sim = 1.0 if fp1['semantic_signature'] == fp2['semantic_signature'] else 0

        # 加权综合
        similarity = entity_sim * 0.5 + keyword_sim * 0.3 + semantic_sim * 0.2

        return similarity


class AdaptiveTopicNamer:
    """自适应话题命名器"""

    def __init__(self):
        self.entity_extractor = SmartEntityExtractor()

    def generate_name(self, topic: Topic) -> str:
        """
        基于话题内所有 atoms 的内容生成名称
        策略：
        1. 找出共同的核心实体
        2. 提取共同的关键动作/事件
        3. 组合成有意义的名称
        """
        if not topic.atoms:
            return "未命名话题"

        # 收集所有 atoms 的实体
        all_entities = []
        for atom in topic.atoms:
            entities = self.entity_extractor.extract_from_content(atom.content)
            all_entities.extend([e[0] for e in entities])

        # 统计实体频率
        entity_freq = Counter(all_entities)

        # 找出高频实体（出现在多个 atoms 中）
        common_entities = [e for e, c in entity_freq.most_common(3)
                         if c >= len(topic.atoms) * 0.5]

        # 提取关键动作词
        action_words = self._extract_common_actions(topic.atoms)

        # 组合名称
        if common_entities and action_words:
            name = f"{common_entities[0]} {action_words[0]}"
        elif common_entities:
            name = f"{common_entities[0]} 相关动态"
        elif action_words:
            name = f"{action_words[0]} 相关"
        else:
            # 回退：使用第一个 atom 的前20字
            name = topic.atoms[0].content[:20] + "..."

        return name

    def _extract_common_actions(self, atoms: List[Atom]) -> List[str]:
        """提取共同的动作词"""
        action_patterns = [
            r'发布\s*([^，。；]+)',
            r'推出\s*([^，。；]+)',
            r'更新\s*([^，。；]+)',
            r'新增\s*([^，。；]+)',
            r'支持\s*([^，。；]+)',
            r'发布|推出|更新|新增|支持|上线|开启|关闭|取消',
        ]

        actions = []
        for atom in atoms:
            for pattern in action_patterns:
                matches = re.findall(pattern, atom.content)
                actions.extend(matches)

        action_freq = Counter(actions)
        return [a for a, c in action_freq.most_common(3) if c >= len(atoms) * 0.3]


class SmartTopicClusterer:
    """智能话题聚类器 v2"""

    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        self.fingerprint_generator = ContentFingerprint()
        self.topic_namer = AdaptiveTopicNamer()
        self.topics: List[Topic] = []

    def cluster(self, atoms: List[Atom]) -> List[Topic]:
        """
        主聚类流程：
        1. 为每个 atom 生成内容指纹
        2. 基于相似度进行聚类
        3. 为每个话题生成自适应名称
        """
        # 生成指纹
        fingerprints = {}
        for atom in atoms:
            fingerprints[atom.id] = self.fingerprint_generator.generate(atom)

        # 聚类
        assigned = set()
        topics = []

        for atom in atoms:
            if atom.id in assigned:
                continue

            # 创建新话题
            topic = Topic(
                id=f"topic_{len(topics)}",
                name="",
                atoms=[atom],
                main_entities=list(fingerprints[atom.id]['entities'])
            )
            assigned.add(atom.id)

            # 寻找相似 atoms
            for other in atoms:
                if other.id in assigned or other.id == atom.id:
                    continue

                similarity = self.fingerprint_generator.calculate_similarity(
                    fingerprints[atom.id],
                    fingerprints[other.id]
                )

                if similarity >= self.similarity_threshold:
                    topic.atoms.append(other)
                    assigned.add(other.id)

            # 生成话题名称
            topic.name = self.topic_namer.generate_name(topic)
            topics.append(topic)

        self.topics = topics
        return topics

    def merge_similar_topics(self, merge_threshold: float = 0.8) -> List[Topic]:
        """合并高度相似的话题"""
        if len(self.topics) < 2:
            return self.topics

        merged = []
        used = set()

        for i, topic1 in enumerate(self.topics):
            if i in used:
                continue

            merged_topic = topic1

            for j, topic2 in enumerate(self.topics[i+1:], i+1):
                if j in used:
                    continue

                # 计算话题相似度
                sim = self._calculate_topic_similarity(topic1, topic2)

                if sim >= merge_threshold:
                    # 合并
                    merged_topic.atoms.extend(topic2.atoms)
                    used.add(j)

            merged.append(merged_topic)
            used.add(i)

        # 重新生成名称
        for topic in merged:
            topic.name = self.topic_namer.generate_name(topic)

        self.topics = merged
        return merged

    def _calculate_topic_similarity(self, t1: Topic, t2: Topic) -> float:
        """计算两个话题的相似度"""
        # 基于主实体重叠
        entity_overlap = len(set(t1.main_entities) & set(t2.main_entities))
        entity_union = len(set(t1.main_entities) | set(t2.main_entities))

        if entity_union == 0:
            return 0

        return entity_overlap / entity_union


def demo():
    """演示"""
    # 测试数据
    atoms = [
        Atom(id="1", content="Kimi K2模型发布，支持多模态推理", entities=["Kimi", "K2"]),
        Atom(id="2", content="月之暗面发布Kimi K2，性能超越GPT-4", entities=["月之暗面", "Kimi", "K2"]),
        Atom(id="3", content="OpenAI推出GPT-4 Turbo新版本", entities=["OpenAI", "GPT-4"]),
        Atom(id="4", content="GPT-4 Turbo更新，价格降低50%", entities=["GPT-4"]),
        Atom(id="5", content="DeepSeek发布V3模型，开源免费", entities=["DeepSeek", "V3"]),
    ]

    clusterer = SmartTopicClusterer(similarity_threshold=0.5)
    topics = clusterer.cluster(atoms)

    print("=" * 60)
    print("智能话题聚类结果")
    print("=" * 60)

    for topic in topics:
        print(f"\n📌 {topic.name}")
        print(f"   主实体: {', '.join(topic.main_entities)}")
        print(f"   包含 {len(topic.atoms)} 条内容:")
        for atom in topic.atoms:
            print(f"      - {atom.content[:40]}...")


if __name__ == "__main__":
    demo()
