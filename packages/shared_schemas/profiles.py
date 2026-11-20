"""Profile definitions and templates for Personal, Developer, Business, and Creator personas."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class ProfileTemplate(BaseModel):
    title: str
    prompt: str
    category: str


class ProfileDefinition(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    default_temperature: float = 0.7
    permission_preset: str = "standard"  # standard, sandboxed, corporate, creative
    suggested_models: List[str] = Field(default_factory=list)
    templates: List[ProfileTemplate] = Field(default_factory=list)


PROFILES: Dict[str, ProfileDefinition] = {
    "personal": ProfileDefinition(
        id="personal",
        name="Personal Assistant",
        description="Daily personal companion for questions, reminders, notes, and local organization.",
        system_prompt=(
            "You are Zevon, a private, local-first personal AI assistant. "
            "You are helpful, concise, thoughtful, and run completely offline on the user's computer. "
            "Help the user organize tasks, answer questions, draft notes, and manage their daily activities."
        ),
        default_temperature=0.7,
        permission_preset="standard",
        suggested_models=["zevon-offline-compact", "qwen2.5:3b", "llama3.2:3b"],
        templates=[
            ProfileTemplate(
                title="Plan Today's Priorities",
                prompt="Help me organize my top 3 priorities for today and outline a focused schedule.",
                category="productivity",
            ),
            ProfileTemplate(
                title="Draft a Polite Reminder",
                prompt="Draft a friendly and polite follow-up message about an upcoming deadline.",
                category="writing",
            ),
            ProfileTemplate(
                title="Explain Simply",
                prompt="Explain how local open-source language models work in plain language.",
                category="learning",
            ),
        ],
    ),
    "developer": ProfileDefinition(
        id="developer",
        name="Developer & Engineering",
        description="Code-aware assistant for software development, debugging, CLI scripting, and architecture.",
        system_prompt=(
            "You are Zevon's Developer Assistant. You are an expert software engineer and systems architect. "
            "Provide clean, idiomatically typed code with explanations, edge-case analysis, and verification steps. "
            "Prefer standard, modern patterns, zero unnecessary dependencies, and safe sandbox execution."
        ),
        default_temperature=0.2,
        permission_preset="sandboxed",
        suggested_models=["zevon-reasoning-mock", "deepseek-r1:8b", "qwen2.5-coder:7b"],
        templates=[
            ProfileTemplate(
                title="Debug Error Stack Trace",
                prompt="Here is an error stack trace. Analyze the root cause and propose a minimal fix:\n\n```\n[paste error here]\n```",
                category="debugging",
            ),
            ProfileTemplate(
                title="Write Unit Tests",
                prompt="Write comprehensive unit tests with edge cases for the following function:\n\n```python\n# [paste code here]\n```",
                category="testing",
            ),
            ProfileTemplate(
                title="Architect an API Route",
                prompt="Design a clean, asynchronous FastAPI route with Pydantic request/response validation and error handling.",
                category="architecture",
            ),
        ],
    ),
    "business": ProfileDefinition(
        id="business",
        name="Business & Team",
        description="Professional mode for document drafting, meeting summaries, policy checks, and reports.",
        system_prompt=(
            "You are Zevon's Business Specialist. You provide structured, professional, executive-ready communication. "
            "Emphasize clarity, factual rigor, risk assessment, and well-organized action items. "
            "Maintain auditability and adhere to privacy and compliance principles."
        ),
        default_temperature=0.3,
        permission_preset="corporate",
        suggested_models=["zevon-reasoning-mock", "llama3.3:70b", "qwen2.5:14b"],
        templates=[
            ProfileTemplate(
                title="Executive Meeting Summary",
                prompt="Summarize the following meeting notes into: Decisions Made, Action Items (with owners), and Open Risks:\n\n[paste notes]",
                category="operations",
            ),
            ProfileTemplate(
                title="Draft Project Proposal",
                prompt="Outline a project proposal including problem statement, proposed solution, timeline, and measurable success criteria.",
                category="strategy",
            ),
            ProfileTemplate(
                title="Risk & Feasibility Assessment",
                prompt="Perform a risk and feasibility analysis on adopting a local-first software architecture for our team.",
                category="governance",
            ),
        ],
    ),
    "creator": ProfileDefinition(
        id="creator",
        name="Creator & Media",
        description="Creative collaborator for brainstorming, video scripts, article outlines, and content production.",
        system_prompt=(
            "You are Zevon's Creative Partner. You are imaginative, engaging, articulate, and skilled in storytelling. "
            "Help generate novel ideas, compelling hooks, structured scripts, and punchy editorial drafts "
            "while maintaining the creator's distinct voice and audience focus."
        ),
        default_temperature=0.85,
        permission_preset="creative",
        suggested_models=["zevon-offline-compact", "qwen2.5:7b", "llama3.2:3b"],
        templates=[
            ProfileTemplate(
                title="5-Minute Video Script",
                prompt="Write an engaging 5-minute video script with a strong hook, 3 key points, and a memorable call to action.",
                category="content",
            ),
            ProfileTemplate(
                title="Brainstorm 10 Content Angles",
                prompt="Brainstorm 10 unique, high-engagement angles for introducing an open-source AI assistant to developers.",
                category="ideation",
            ),
            ProfileTemplate(
                title="Refine Prose & Cadence",
                prompt="Review and polish the following paragraph to make it punchy, rhythmic, and captivating:\n\n[paste draft]",
                category="editing",
            ),
        ],
    ),
}


def get_profile(profile_id: str) -> ProfileDefinition:
    """Retrieve profile definition by ID, defaulting to 'personal'."""
    return PROFILES.get(profile_id.lower(), PROFILES["personal"])


def list_profiles() -> List[ProfileDefinition]:
    """Return all configured profile definitions."""
    return list(PROFILES.values())
