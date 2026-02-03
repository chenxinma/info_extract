import textwrap

from pydantic_ai import Agent, FunctionToolset

from ..utils.model import qwen
from .playbook import PlaybookManager
from .reflector_agent import Reflection

agent = Agent(
            model=qwen(),
            instructions=
                textwrap.dedent("""
                你是一名严谨的知识库整编专家（Curator）。你的任务是根据反思器的分析，对策略剧本进行精准的增量更新以优化df映射取数的执行效果。
                1.  **分析反思器输出**：仔细阅读反思器的分析结果，识别出需要更新的策略条目、新增的策略或修正的策略。
                2.  **新增或更新策略剧本**：根据分析结果，对策略剧本进行增量更新。确保更新后的剧本与反思器的分析一致，且符合策略剧本的格式规范。
                    可以使用`overview_playbooks`读取策略剧本，使用`create_playbook`创建新策略条目，使用`modify_playbook`和`delete_playbook`修改或删除策略条目。
                """)
            )

async def curate(playbookManager:PlaybookManager, reflection: Reflection):
    """
    根据反思结果更新策略剧本
    """
    prompt = f"""
    反思结果：{reflection.model_dump_json(ensure_ascii=False)}
    """
    return await agent.run(prompt, toolsets=[
        FunctionToolset(tools=[
            playbookManager.create_playbook,
            playbookManager.overview_playbooks,
            playbookManager.modify_playbook,
            playbookManager.delete_playbook
        ])
    ])