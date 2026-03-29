#!/usr/bin/env python3
"""atom_store 基本功能测试"""

import sys, json, tempfile, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from atom_store import AtomStore, create_atom

def test_all():
    tmp = Path(tempfile.mkdtemp())
    try:
        store = AtomStore(base_dir=tmp)

        # 测试 1：创建 Atom
        atom = create_atom(
            title="OpenAI releases GPT-5.4",
            summary_zh="OpenAI 发布 GPT-5.4 轻量级模型",
            platform="x", author="@OpenAI", author_type="official",
            url="https://x.com/OpenAI/status/123", content_type="official",
            category="ai_models", tags=["openai", "gpt", "llm"],
            entities=["OpenAI", "GPT-5.4"], date="2026-03-18"
        )
        assert atom["trust_default"] == "L1", f"Expected L1, got {atom['trust_default']}"
        assert atom["id"] is None
        print("✅ 测试 1: create_atom")

        # 测试 2：保存
        atom_id = store.save_atom(atom)
        assert atom_id == "atom_20260318_001", f"Expected atom_20260318_001, got {atom_id}"
        print("✅ 测试 2: save_atom")

        # 测试 3：按日期查询
        atoms = store.query_by_date("2026-03-18")
        assert len(atoms) == 1
        assert atoms[0]["title"] == "OpenAI releases GPT-5.4"
        print("✅ 测试 3: query_by_date")

        # 测试 4：entity 索引
        results = store.query_by_entity("OpenAI")
        assert len(results) == 1
        print("✅ 测试 4: query_by_entity")

        # 测试 5：tag 索引
        results = store.query_by_tag("gpt")
        assert len(results) == 1
        print("✅ 测试 5: query_by_tag")

        # 测试 6：ID 精确查询
        result = store.query_by_id("atom_20260318_001")
        assert result is not None
        assert result["source"]["author"] == "@OpenAI"
        print("✅ 测试 6: query_by_id")

        # 测试 7：更新
        ok = store.update_atom("atom_20260318_001", {
            "trust_final": "L1", "trust_reason": "官方公告", "in_daily_brief": True
        })
        assert ok
        updated = store.query_by_id("atom_20260318_001")
        assert updated["trust_final"] == "L1"
        assert updated["in_daily_brief"] == True
        print("✅ 测试 7: update_atom")

        # 测试 8：批量保存
        batch = [
            create_atom(
                title=f"Test news {i}", summary_zh=f"测试 {i}",
                platform="rss", author="TechCrunch", author_type="media",
                url=f"https://tc.com/{i}", content_type="report",
                category="ai_models", tags=["test"], entities=["TestCo"],
                date="2026-03-18"
            ) for i in range(5)
        ]
        ids = store.save_atoms_batch(batch)
        assert len(ids) == 5
        all_a = store.query_by_date("2026-03-18")
        assert len(all_a) == 6  # 1 + 5
        print("✅ 测试 8: save_atoms_batch")

        # 测试 9：统计
        stats = store.get_daily_stats("2026-03-18")
        assert stats["total"] == 6
        assert stats["selected_for_brief"] == 1
        print("✅ 测试 9: get_daily_stats")

        # 测试 10：日期范围
        atom2 = create_atom(
            title="Day 2", summary_zh="第二天", platform="x", author="@t",
            author_type="kol", url="https://x.com/t/1", content_type="commentary",
            category="mobile", tags=["test"], entities=["TestCo"], date="2026-03-19"
        )
        store.save_atom(atom2)
        rng = store.query_by_date_range("2026-03-18", "2026-03-19")
        assert len(rng) == 7
        print("✅ 测试 10: query_by_date_range")

        # 测试 11：entity 频率
        freq = store.get_entity_frequency("2026-03-18", "2026-03-19")
        tc = dict(freq).get("TestCo", 0)
        assert tc == 6  # 5 batch + 1 day2
        print("✅ 测试 11: get_entity_frequency")

        # 测试 12：关联发现
        # 先添加一条与 atom_001 共享 entity 的记录
        shared_atom = create_atom(
            title="GPT-5.4 benchmark results", summary_zh="GPT-5.4 基准测试",
            platform="rss", author="TechCrunch", author_type="media",
            url="https://tc.com/gpt54", content_type="report",
            category="ai_models", tags=["openai", "benchmark"], entities=["OpenAI", "GPT-5.4"],
            date="2026-03-18"
        )
        store.save_atom(shared_atom)
        related = store.find_related_atoms("atom_20260318_001")
        assert len(related) > 0, "Should find atoms sharing OpenAI/GPT-5.4 entities"
        print("✅ 测试 12: find_related_atoms")

        # 测试 13：trust_default 判定
        a1 = create_atom(title="t", summary_zh="s", platform="x", author="@x",
                         author_type="official", url="u", content_type="official",
                         category="other", tags=[], entities=[])
        assert a1["trust_default"] == "L1"
        a2 = create_atom(title="t", summary_zh="s", platform="x", author="@x",
                         author_type="media", url="u", content_type="report",
                         category="other", tags=[], entities=[])
        assert a2["trust_default"] == "L2"
        a3 = create_atom(title="t", summary_zh="s", platform="x", author="@x",
                         author_type="blogger", url="u", content_type="repost",
                         category="other", tags=[], entities=[])
        assert a3["trust_default"] == "L3"
        print("✅ 测试 13: trust_default 判定")

        print("\n🎉 全部 13 项测试通过！")

    finally:
        shutil.rmtree(tmp)

if __name__ == "__main__":
    test_all()
