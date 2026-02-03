# PNG表单识别与JSON导出功能设计方案

## 1. 概述

本文档描述了在info_extract项目中实现基于视觉模型的图片表单识别功能的设计方案。该功能利用pydantic-ai框架调用多模态大模型（视觉模型）识别图片中的表单内容，并将其结构化导出为JSON格式。

## 2. 需求分析

### 功能需求
- 支持PNG、JPG、JPEG等多种图片格式的表单识别
- 自动识别图片中的表单字段、标签和值
- 将识别结果结构化为JSON格式输出
- 支持用户自定义字段映射和验证规则
- 支持批量处理多张图片
- 提供置信度评分和原始OCR文本保留

### 非功能需求
- 识别准确率高（结构化字段准确率>95%）
- 响应速度快（单张图片处理时间<10秒）
- 支持主流视觉模型（OpenAI GPT-4o/Vision、Anthropic Claude、Google Gemini等）
- 具有良好的可扩展性和可配置性
- 完善的错误处理和日志记录

## 3. 技术选型

### 3.1 核心框架：pydantic-ai
采用pydantic-ai作为Agent框架，原因如下：
- 原生支持Pydantic模型作为输出结构
- 内置多模态输入支持（图片、文档）
- 支持多种模型提供商的统一接口
- 类型安全的依赖注入系统
- 良好的测试支持和可观测性

### 3.2 视觉模型支持

| 模型提供商 | 推荐模型 | 特点 |
|-----------|---------|------|
| OpenAI | gpt-4o | 多模态能力强，表单识别准确 |
| Anthropic | claude-3-5-sonnet | 文档理解能力强，支持大图片 |
| Google | gemini-1.5-pro | 原生多模态，性价比高 |
| Qwen | qwen-vl-max | 中文表单识别优秀 |

### 3.3 依赖库
- `pydantic-ai`: Agent框架核心
- `pydantic`: 数据模型定义和验证
- `Pillow`: 图片预处理和格式转换
- `logfire`: 可选，用于Agent执行监控（pydantic-ai原生支持）

## 4. 架构设计

### 4.1 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    IMG2JSON Pipeline                        │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │ Image Loader │ → │ Vision Agent │ → │ JSON Exporter   │  │
│  └──────────────┘   └──────────────┘   └─────────────────┘  │
│         │                  │                    │           │
│         ↓                  ↓                    ↓           │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │ Preprocessor │   │ LLM Model    │   │ Pydantic Models │  │
│  │ (Pillow)     │   │ (pydantic-ai)│   │ (Validation)    │  │
│  └──────────────┘   └──────────────┘   └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 类设计

#### FormField (Pydantic Model)
定义单个表单字段的数据结构。

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

class FormField(BaseModel):
    """表单字段定义"""
    name: str = Field(description="字段名称/标签")
    value: str = Field(description="字段值")
    field_type: Literal["text", "number", "date", "checkbox", "select", "signature"] = Field(
        description="字段类型"
    )
    confidence: float = Field(ge=0.0, le=1.0, description="识别置信度")
    bbox: Optional[tuple[int, int, int, int]] = Field(
        default=None, description="边界框坐标 (x1, y1, x2, y2)"
    )
    raw_text: Optional[str] = Field(
        default=None, description="原始OCR文本"
    )
```

#### FormSchema (Pydantic Model)
定义表单的整体结构。

```python
class FormSchema(BaseModel):
    """表单数据结构"""
    form_type: str = Field(description="表单类型标识")
    fields: list[FormField] = Field(description="表单字段列表")
    metadata: dict = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "form_type": "invoice",
                "fields": [
                    {
                        "name": "发票号码",
                        "value": "12345678",
                        "field_type": "text",
                        "confidence": 0.98
                    }
                ]
            }
        }
```

#### VisionFormAgent
核心Agent类，封装pydantic-ai的Agent功能。

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

class VisionFormAgent:
    """视觉表单识别Agent"""
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        output_schema: type[BaseModel] = FormSchema
    ):
        self.model = OpenAIModel(model_name, api_key=api_key)
        self.agent = Agent(
            model=self.model,
            result_type=output_schema,
            system_prompt=self._get_system_prompt()
        )
    
    async def recognize(self, image_path: str) -> FormSchema:
        """识别图片中的表单内容"""
        # 加载并预处理图片
        image_data = await self._load_image(image_path)
        
        # 调用Agent进行识别
        result = await self.agent.run(
            user_prompt="请识别图片中的表单内容，提取所有字段及其值",
            deps=image_data
        )
        
        return result.data
```

## 5. 实现细节

### 5.1 图片预处理流程

```python
from PIL import Image
import io

async def preprocess_image(image_path: str, max_size: int = 4096) -> bytes:
    """
    预处理图片以适应模型输入要求
    
    步骤：
    1. 加载图片
    2. 调整大小（保持宽高比，最大边不超过max_size）
    3. 转换为RGB模式
    4. 压缩为JPEG格式（如果原始格式不支持）
    """
    with Image.open(image_path) as img:
        # 转换为RGB
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # 调整大小
        width, height = img.size
        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # 保存为bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        return buffer.getvalue()
```

### 5.2 Agent Prompt设计

```python
FORM_RECOGNITION_PROMPT = """你是一个专业的表单识别助手。请仔细分析提供的图片，识别其中的表单字段。

任务要求：
1. 识别所有可见的表单字段标签（label）和对应的值（value）
2. 判断字段类型：text（文本）、number（数字）、date（日期）、checkbox（复选框）、select（选择框）、signature（签名）
3. 为每个字段提供置信度评分（0.0-1.0）
4. 如果可能，提供字段在图片中的大致位置（边界框坐标）
5. 保留原始识别的文本内容

输出格式：
请严格按照提供的JSON Schema格式输出，确保所有字段都有值。

注意事项：
- 如果字段值为空，使用空字符串""
- 对于复选框，如果选中则value为"true"，未选中为"false"
- 日期字段尽量统一为YYYY-MM-DD格式
- 对于不明确的字段，confidence可以适当降低
"""
```

### 5.3 多模型支持配置

```python
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.google import GoogleModel

MODEL_REGISTRY = {
    "gpt-4o": lambda key: OpenAIModel("gpt-4o", api_key=key),
    "gpt-4o-mini": lambda key: OpenAIModel("gpt-4o-mini", api_key=key),
    "claude-3-5-sonnet": lambda key: AnthropicModel("claude-3-5-sonnet-20241022", api_key=key),
    "claude-3-opus": lambda key: AnthropicModel("claude-3-opus-20240229", api_key=key),
    "gemini-1.5-pro": lambda key: GoogleModel("gemini-1.5-pro", api_key=key),
}

def create_vision_agent(model_name: str, api_key: str) -> Agent:
    """根据配置创建对应的视觉Agent"""
    model_factory = MODEL_REGISTRY.get(model_name)
    if not model_factory:
        raise ValueError(f"不支持的模型: {model_name}")
    
    model = model_factory(api_key)
    return Agent(
        model=model,
        result_type=FormSchema,
        system_prompt=FORM_RECOGNITION_PROMPT
    )
```

## 6. 错误处理与重试策略

### 6.1 错误分类

| 错误类型 | 处理策略 |
|---------|---------|
| 图片加载失败 | 记录错误，跳过该文件 |
| 模型API错误 | 指数退避重试（最多3次） |
| JSON解析失败 | 尝试修复或返回原始文本 |
| 字段验证失败 | 使用默认值并标记问题字段 |

### 6.2 重试机制

```python
from pydantic_ai import Agent, RetryPrompt

agent = Agent(
    model=model,
    result_type=FormSchema,
    retries=3,  # pydantic-ai内置重试
)

# 自定义重试逻辑
@agent.result_validator
async def validate_result(result: FormSchema) -> FormSchema:
    """验证并可能触发重试"""
    low_confidence_fields = [
        f for f in result.fields if f.confidence < 0.5
    ]
    if len(low_confidence_fields) > len(result.fields) * 0.5:
        raise RetryPrompt(
            f"识别置信度较低，请重新仔细识别以下字段: "
            f"{[f.name for f in low_confidence_fields]}"
        )
    return result
```

## 8. 集成方案

### 8.1 文件位置

```
src/
└── info_extract/
    └── utils/
        ├── __init__.py
        └── image2json.py   # 图片预处理(包含图片加载、VisionFormAgent实现、FormSchema定义)
```

