import os
import textwrap
from typing import Optional, Literal
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from .playbook import PlaybookManager

from .model import qwen

class PlaybookEvaluation(BaseModel):
    bullet_id: str = Field(description="文件序号")
    impact: Literal["helpful", "harmful", "neutral"] = Field(description="对策略条目的影响")

class Reflection(BaseModel):
    reasoning: str = Field(description="反思的推理链条")
    error_identification: Optional[str] = Field(description="反思中识别到的错误", default=None)
    root_cause_analysis: Optional[str] = Field(description="反思中识别到的根因分析", default=None)
    correct_approach: Optional[str] = Field(description="反思中识别到的正确方法", default=None)
    key_insight: Optional[str] = Field(description="反思中识别到的关键洞察", default=None)
    playbook_evaluation: list[PlaybookEvaluation]

agent = Agent(
            model=qwen(),
            output_type=Reflection,
            instructions=
                textwrap.dedent("""
                你是资深的SQL智能体，负责分析取出脚本的执行轨迹，诊断其成功或失败的原因，并提炼出可复用的策略和教训。
                考虑更新 信息项和df字段的映射关系（同义词）。
                **分析要求：**
                1.  **逐步复盘**：仔细检查执行轨迹中的每一步，思考其意图和实际效果。
                2.  **定位关键点**：识别出直接导致成功或失败的关键决策、工具调用或逻辑判断。
                3.  **归因分析**：判断问题是源于对API的误解、策略选择不当、逻辑错误，还是忽略了Playbook中的某条重要建议。
                4.  **提炼新知**：从本次经历中总结出新的、有价值的策略、常见陷阱或优化技巧。
                5.  **策略条目评估**: 影响评估仅列出与本轮执行相关的策略条目，评估其对智能体成功或失败的影响，分类为"helpful"、"harmful"或"neutral"。  
            """)
        )

async def reflect(playbookManager:PlaybookManager, messages: list[ModelMessage], exp: Exception| None = None)->Reflection:
    prompt = f"策略条目Playbooks：{playbookManager.overview_playbooks()}"
    if exp:
        prompt += f"异常信息：{exp}"
    response = await agent.run(prompt, message_history=messages)
    return response.output