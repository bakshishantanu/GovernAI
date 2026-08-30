from app.skills.base import BaseSkill, BaseTool, TrustLevel


class _EchoTool(BaseTool):
    name = "echo"
    description = "Echoes input"
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    async def execute(self, **kwargs):
        return kwargs["text"]


class _EchoSkill(BaseSkill):
    name = "echo_skill"
    display_name = "Echo Skill"
    description = "A trivial skill for testing"
    version = "1.0.0"
    required_permissions = ["echo:use"]
    trust_level = TrustLevel.VERIFIED

    def get_tools(self):
        return [_EchoTool()]


async def test_tool_execute_runs():
    tool = _EchoTool()
    result = await tool.execute(text="hi")
    assert result == "hi"


def test_tool_to_openai_tool_format():
    tool = _EchoTool()
    spec = tool.to_openai_tool()
    assert spec["type"] == "function"
    assert spec["function"]["name"] == "echo"
    assert spec["function"]["parameters"]["required"] == ["text"]


def test_skill_exposes_tools_and_metadata():
    skill = _EchoSkill()
    tools = skill.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "echo"
    assert skill.trust_level == TrustLevel.VERIFIED
    assert skill.required_permissions == ["echo:use"]
