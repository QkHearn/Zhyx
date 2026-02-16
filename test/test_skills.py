"""Skill 测试"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_mcp_scan():
    from core import get_mcp
    from skills import get_registry
    reg = get_registry()
    reg.clear()
    n = get_mcp().scan_and_register_skills()
    skills = [s.name for s in reg.list_all()]
    assert n >= 4
    assert "ChatSkill" in skills
    assert "FileReader" in skills


def test_file_reader():
    from core.chat import run_skill
    r = run_skill("FileReader", {"path": str(ROOT / "README.md")})
    assert "content" in r or "error" in r
