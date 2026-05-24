"""
Agent evaluation scenarios with directory-based extension.
Drop JSON files into tests/fixtures/scenarios/ to add scenarios without code changes.

Scenario JSON format:
{
  "name": "my-scenario",
  "message": "user message here",
  "expected_intent": "explicit_edit",
  "expected_scope": "summary",
  "assertions": ["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
  "tags": ["explicit_edit", "zh"],
  "difficulty": "medium",
  "regression": true,
  "multi_turn": []
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

INTENT_CLASSES = {"explicit_edit", "broad_edit", "fact_edit", "analysis_only", "general_chat"}
SCOPES = {"summary", "workExperience", "education", "personalProjects", "additional", "personalInfo", "global"}

FIXTURES_SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "scenarios"


@dataclass
class Scenario:
    name: str
    message: str
    expected_intent: str
    expected_scope: str = ""
    assertions: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    multi_turn: List[str] = field(default_factory=list)
    difficulty: str = "medium"
    regression: bool = True
    expected_output_schema: Optional[Dict[str, Any]] = None


# ── Hardcoded scenario bank (35 scenarios) ────────────────────────────

SCENARIOS: List[Scenario] = [
    # explicit_edit
    Scenario(name="explicit-summary", message="优化一下个人 summary，控制在 90 字以内，突出管理能力。",
             expected_intent="explicit_edit", expected_scope="summary",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "summary", "zh"], difficulty="easy"),
    Scenario(name="explicit-work-star", message="把最近一段工作经历改成 STAR 风格要点，每条要有量化结果。",
             expected_intent="explicit_edit", expected_scope="workExperience",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "workExperience", "zh", "star"], difficulty="medium"),
    Scenario(name="explicit-edu-enhance", message="丰富教育经历部分，突出课程项目与学术成果，避免空话。",
             expected_intent="explicit_edit", expected_scope="education",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "education", "zh"], difficulty="medium"),
    Scenario(name="explicit-project-polish", message="优化项目经历，每个项目加一句技术栈和一句业务成果。",
             expected_intent="explicit_edit", expected_scope="personalProjects",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "personalProjects", "zh"], difficulty="medium"),
    Scenario(name="explicit-skills-dedup", message="技术技能里如果有重复的帮我合并去重。",
             expected_intent="explicit_edit", expected_scope="additional",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "additional", "zh"], difficulty="easy"),
    Scenario(name="explicit-single-bullet", message="把工作经历第一条描述改得更量化一些。",
             expected_intent="explicit_edit", expected_scope="workExperience",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "workExperience", "zh", "granular"], difficulty="medium", regression=False),
    Scenario(name="explicit-skills-add", message="在技能里加上 Kubernetes 和 Terraform。",
             expected_intent="explicit_edit", expected_scope="additional",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "additional", "zh", "additive"], difficulty="easy", regression=False),
    Scenario(name="explicit-title-update", message="把职位名称从 Developer 改成 Senior Software Engineer。",
             expected_intent="explicit_edit", expected_scope="workExperience",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["explicit_edit", "workExperience", "zh", "title"], difficulty="easy", regression=False),
    # broad_edit
    Scenario(name="broad-polish-tone", message="整体润色一下简历，语气更专业克制，去掉夸张表达。",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["broad_edit", "global", "zh", "tone"], difficulty="hard"),
    Scenario(name="broad-ats-keywords", message="强化 ATS 关键词覆盖，目标岗位是高级产品经理。",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["broad_edit", "global", "zh", "ats"], difficulty="hard"),
    Scenario(name="broad-metric-boost", message="每段经历至少补一条可量化的结果指标。",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["broad_edit", "global", "zh", "metrics"], difficulty="hard"),
    Scenario(name="broad-en-polish", message="Polish the entire resume to sound more professional and concise.",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["broad_edit", "global", "en", "tone"], difficulty="medium", regression=False),
    Scenario(name="broad-consistency", message="统一整份简历的时间格式和标点风格，确保一致。",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["broad_edit", "global", "zh", "consistency"], difficulty="medium", regression=False),
    Scenario(name="broad-concise", message="简历太长了，帮我精简到一页纸的内容量。",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["broad_edit", "global", "zh", "conciseness"], difficulty="hard", regression=False),
    # fact_edit
    Scenario(name="fact-phone-change", message="把我的手机号改成 13800138000。",
             expected_intent="fact_edit",
             assertions=["chain_has_suggest", "has_confirm_required", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["fact_edit", "personalInfo", "zh", "phone"], difficulty="easy"),
    Scenario(name="fact-email-update", message="更新邮箱为 new.email@example.com。",
             expected_intent="fact_edit",
             assertions=["chain_has_suggest", "has_confirm_required", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["fact_edit", "personalInfo", "zh", "email"], difficulty="easy"),
    Scenario(name="fact-date-fix", message="第一段工作经历的起止时间不对，改成 2020-06 到 2023-08。",
             expected_intent="fact_edit",
             assertions=["chain_has_suggest", "has_confirm_required", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["fact_edit", "workExperience", "zh", "date"], difficulty="medium"),
    Scenario(name="fact-gpa-update", message="GPA 改成 3.9。",
             expected_intent="fact_edit", expected_scope="education",
             assertions=["chain_has_suggest", "has_confirm_required", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["fact_edit", "education", "zh", "numeric"], difficulty="easy", regression=False),
    Scenario(name="fact-name-spelling", message="我的名字拼写不对，应该是 Zhang San 不是 Zhan San。",
             expected_intent="fact_edit", expected_scope="personalInfo",
             assertions=["chain_has_suggest", "has_confirm_required", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["fact_edit", "personalInfo", "zh", "name"], difficulty="easy", regression=False),
    # analysis_only
    Scenario(name="analysis-risk-review", message="只分析这份简历的风险点和短板，不要修改任何内容。",
             expected_intent="analysis_only",
             assertions=["no_mutation", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["analysis_only", "global", "zh"], difficulty="medium"),
    Scenario(name="analysis-ats-gap", message="分析简历的 ATS 关键词覆盖情况，告诉我缺了什么，不要改内容。",
             expected_intent="analysis_only",
             assertions=["no_mutation", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["analysis_only", "global", "zh", "ats"], difficulty="medium"),
    Scenario(name="analysis-en-gap", message="Review my resume for gaps and weaknesses. Do not make any edits.",
             expected_intent="analysis_only",
             assertions=["no_mutation", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["analysis_only", "global", "en"], difficulty="medium", regression=False),
    Scenario(name="analysis-section-review", message="只评估工作经历部分的质量，给出改进建议但不要改。",
             expected_intent="analysis_only", expected_scope="workExperience",
             assertions=["no_mutation", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["analysis_only", "workExperience", "zh"], difficulty="medium", regression=False),
    # general_chat
    Scenario(name="chat-hello", message="你好，你能帮我做什么？", expected_intent="general_chat",
             assertions=["no_mutation", "assistant_not_empty"], tags=["general_chat", "zh"], difficulty="easy"),
    Scenario(name="chat-capability-en", message="What resume formats do you support? Can you handle PDF files?",
             expected_intent="general_chat",
             assertions=["no_mutation", "assistant_not_empty"], tags=["general_chat", "en"], difficulty="easy"),
    Scenario(name="chat-thanks", message="谢谢你的帮助！", expected_intent="general_chat",
             assertions=["no_mutation", "assistant_not_empty"], tags=["general_chat", "zh"], difficulty="easy", regression=False),
    Scenario(name="chat-workflow", message="这个工具怎么用？我需要先上传简历吗？", expected_intent="general_chat",
             assertions=["no_mutation", "assistant_not_empty"], tags=["general_chat", "zh", "onboarding"], difficulty="easy", regression=False),
    # edge_cases
    Scenario(name="edge-ambiguous-vague", message="帮我把简历改好一点。", expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["edge", "broad_edit", "zh", "ambiguous"], difficulty="hard"),
    Scenario(name="edge-multi-scope", message="优化工作经历和项目经历，统一用 STAR 格式。", expected_intent="explicit_edit",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["edge", "explicit_edit", "multi-scope", "zh"], difficulty="hard"),
    Scenario(name="edge-mixed-lang", message="Please polish the summary section, 用中文写。",
             expected_intent="explicit_edit", expected_scope="summary",
             assertions=["chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["edge", "explicit_edit", "summary", "mixed-lang"], difficulty="hard"),
    Scenario(name="edge-empty-message", message=" ", expected_intent="general_chat",
             assertions=["assistant_not_empty"], tags=["edge", "general_chat", "empty"], difficulty="hard", regression=False),
    Scenario(name="edge-very-long", message="请帮我全面优化这份简历。首先总结要突出技术领导力和业务影响力，控制在100字以内。工作经历全部改成STAR格式，每条要有量化结果和具体技术栈。教育经历补充GPA和核心课程。项目经历加技术栈和成果数据。技能部分按熟练度分级，去掉重复的。语言能力补充等级证明。证书和奖项按时间倒序排列。最后整体润色，确保语气专业、无拼写错误、格式统一。",
             expected_intent="broad_edit",
             assertions=["chain_has_suggest", "chain_has_refine", "chain_ends_with_compose", "assistant_not_empty"],
             tags=["edge", "broad_edit", "zh", "long-message"], difficulty="hard", regression=False),
    # multi_turn
    Scenario(name="multi-turn-refine-apply", message="把 summary 改得更简洁有力一些。",
             expected_intent="explicit_edit", expected_scope="summary",
             assertions=["chain_has_refine", "has_apply_ready", "assistant_not_empty"],
             tags=["multi-turn", "explicit_edit", "summary", "zh"], difficulty="medium", multi_turn=["apply"]),
    Scenario(name="multi-turn-phone-apply", message="更新手机号为 13900139000。",
             expected_intent="fact_edit", expected_scope="personalInfo",
             assertions=["chain_has_suggest", "has_confirm_required", "assistant_not_empty"],
             tags=["multi-turn", "fact_edit", "personalInfo", "zh"], difficulty="medium", regression=False, multi_turn=["apply"]),
    Scenario(name="multi-turn-reject", message="把工作经历改成 STAR 格式。",
             expected_intent="explicit_edit", expected_scope="workExperience",
             assertions=["chain_has_refine", "has_apply_ready", "assistant_not_empty"],
             tags=["multi-turn", "explicit_edit", "workExperience", "zh"], difficulty="medium", regression=False, multi_turn=["reject"]),
]


def load_scenarios_from_dir(path: Path | None = None) -> List[Scenario]:
    """Scan a directory for JSON scenario files. Each file defines one Scenario.
    Merges with the built-in SCENARIOS list (deduplicated by name)."""
    if path is None:
        path = FIXTURES_SCENARIOS_DIR
    if not path.exists():
        return list(SCENARIOS)

    names = {s.name for s in SCENARIOS}
    extra: List[Scenario] = []
    for f in sorted(path.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(d, dict) and "name" in d:
                s = Scenario(
                    name=d["name"], message=d.get("message", ""),
                    expected_intent=d.get("expected_intent", "general_chat"),
                    expected_scope=d.get("expected_scope", ""),
                    assertions=d.get("assertions", []),
                    tags=d.get("tags", []),
                    multi_turn=d.get("multi_turn", []),
                    difficulty=d.get("difficulty", "medium"),
                    regression=d.get("regression", False),
                )
                if s.name not in names:
                    names.add(s.name)
                    extra.append(s)
        except Exception:
            pass
    return SCENARIOS + extra


def filter_by_tag(tag: str) -> List[Scenario]:
    return [s for s in SCENARIOS if tag in s.tags]

def filter_by_intent(intent_class: str) -> List[Scenario]:
    return [s for s in SCENARIOS if s.expected_intent == intent_class]

def filter_regression() -> List[Scenario]:
    return [s for s in SCENARIOS if s.regression]

def get_by_name(name: str) -> Scenario | None:
    for s in SCENARIOS:
        if s.name == name:
            return s
    return None

def summary() -> Dict[str, Any]:
    intents: Dict[str, int] = {}
    difficulties: Dict[str, int] = {}
    tags: Dict[str, int] = {}
    reg = 0
    mt = 0
    for s in SCENARIOS:
        intents[s.expected_intent] = intents.get(s.expected_intent, 0) + 1
        difficulties[s.difficulty] = difficulties.get(s.difficulty, 0) + 1
        for t in s.tags:
            tags[t] = tags.get(t, 0) + 1
        if s.regression:
            reg += 1
        if s.multi_turn:
            mt += 1
    return {
        "total_scenarios": len(SCENARIOS),
        "by_intent": intents,
        "by_difficulty": difficulties,
        "regression_count": reg,
        "multi_turn_count": mt,
        "top_tags": dict(sorted(tags.items(), key=lambda x: x[1], reverse=True)[:10]),
    }
