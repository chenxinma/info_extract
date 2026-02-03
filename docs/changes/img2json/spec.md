# PNG表单识别与JSON导出功能规格说明

## 1. 功能概述

本功能实现基于pydantic-ai框架的视觉表单识别系统，能够将图片（PNG/JPG等格式）中的表单内容自动识别并结构化为JSON格式输出。支持多种主流视觉模型，具有高度的可配置性和扩展性。

## 2. 功能需求

### 2.1 核心功能

#### 2.1.1 图片输入处理
- **支持格式**: PNG、JPG、JPEG、BMP、WebP
- **图片预处理**: 自动调整大小、格式转换、质量优化
- **批量输入**: 支持单张图片或批量图片列表输入
- **图片验证**: 验证文件完整性、格式正确性

#### 2.1.2 表单识别
- **字段识别**: 自动识别表单字段名称（label）和值（value）
- **类型推断**: 自动判断字段类型（text、number、date、checkbox、select、signature）
- **结构提取**: 识别表单的层次结构和分组关系
- **置信度评分**: 为每个识别结果提供置信度分数（0.0-1.0）
- **位置信息**: 可选输出字段在图片中的边界框坐标

#### 2.1.3 JSON输出
- **结构化输出**: 使用Pydantic模型定义严格的输出结构
- **格式转换**: 支持多种JSON输出格式（compact、pretty、custom）
- **字段映射**: 支持自定义字段名称映射规则
- **数据验证**: 自动验证输出数据的完整性和有效性

### 2.2 输入输出规范

#### 输入参数

```python
class RecognitionRequest(BaseModel):
    """识别请求参数"""
    image_path: str = Field(description="图片文件路径")
    model_name: str = Field(default="gpt-4o", description="使用的模型名称")
    output_schema: Optional[type[BaseModel]] = Field(
        default=None, description="自定义输出结构"
    )
    confidence_threshold: float = Field(
        default=0.5, ge=0.0, le=1.0, description="置信度阈值"
    )
    include_bbox: bool = Field(
        default=False, description="是否包含边界框坐标"
    )
    include_raw_text: bool = Field(
        default=False, description="是否包含原始OCR文本"
    )
    custom_prompt: Optional[str] = Field(
        default=None, description="自定义识别Prompt"
    )
```

#### 输出结果

```python
class RecognitionResponse(BaseModel):
    """识别响应结果"""
    success: bool = Field(description="识别是否成功")
    form_data: Optional[FormSchema] = Field(
        default=None, description="识别的表单数据"
    )
    processing_time: float = Field(description="处理耗时（秒）")
    model_used: str = Field(description="实际使用的模型")
    error_message: Optional[str] = Field(
        default=None, description="错误信息（如果失败）"
    )
    metadata: dict = Field(
        default_factory=dict, description="额外元数据"
    )
```

### 2.3 性能指标

| 指标 | 目标值 | 说明 |
|-----|-------|------|
| 单张处理时间 | < 10秒 | 标准分辨率图片（< 2MB） |
| 批量处理吞吐量 | > 6张/分钟 | 并发数=5 |
| 字段识别准确率 | > 95% | 清晰打印表单 |
| 置信度>0.8的字段比例 | > 80% | 有效识别率 |
| 内存占用 | < 500MB | 单张图片处理峰值 |

## 3. 非功能性需求

### 3.1 兼容性

#### 运行环境
- **操作系统**: Windows 10/11, Linux, macOS
- **Python版本**: Python 3.10+
- **依赖库**: pydantic-ai >= 0.1.0, pydantic >= 2.0, Pillow >= 10.0

#### 模型支持
- **Alibaba**: qwen3-vl-plus
- **扩展性**: 支持通过配置添加新模型
```python
from .model import qwen
agent = Agent(
    model=qwen("qwen3-vl-plus"),
    instructions=
    ...
```

### 3.2 错误处理

#### 错误分类与响应

| 错误代码 | 错误类型 | 处理方式 | 用户提示 |
|---------|---------|---------|---------|
| E001 | 文件不存在 | 抛出FileNotFoundError | "图片文件不存在: {path}" |
| E002 | 格式不支持 | 抛出ValueError | "不支持的图片格式: {format}" |
| E003 | 图片损坏 | 抛出IOError | "无法读取图片文件" |
| E004 | 模型API错误 | 重试3次后抛出APIError | "模型服务暂时不可用" |
| E005 | 识别结果无效 | 尝试修复或返回partial | "部分字段识别失败" |
| E006 | 配置错误 | 抛出ConfigError | "无效的配置参数: {param}" |

#### 重试策略
- **最大重试次数**: 3次
- **退避策略**: 指数退避（1s, 2s, 4s）
- **可重试错误**: API限流、网络超时、服务不可用
- **不可重试错误**: 认证失败、无效参数、格式错误

### 3.3 安全性

- **输入验证**: 验证文件类型，防止恶意文件上传
- **路径安全**: 使用绝对路径，防止目录遍历攻击
- **API密钥**: 通过环境变量或安全密钥管理服务获取
- **日志脱敏**: 日志中不包含敏感信息（API密钥、文件内容）
- **资源限制**: 限制单张图片大小（最大10MB），防止内存溢出

## 4. 技术实现

### 4.1 架构组件

#### 4.1.1 ImageLoader（图片加载器）
```python
class ImageLoader:
    """负责图片的加载、验证和预处理"""
    
    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_IMAGE_SIZE = 4096  # 最大边长
    
    async def load(self, path: str) -> ImageData:
        """加载并预处理图片"""
        # 验证文件
        self._validate_file(path)
        # 加载图片
        image = Image.open(path)
        # 预处理
        processed = self._preprocess(image)
        return ImageData(data=processed, original_size=image.size)
```

#### 4.1.2 VisionAgent（视觉识别Agent）
```python
class VisionAgent:
    """基于pydantic-ai的视觉识别Agent"""
    
    def __init__(
        self,
        model_config: ModelConfig,
        output_schema: type[BaseModel] = FormSchema
    ):
        self.model = self._create_model(model_config)
        self.agent = Agent(
            model=self.model,
            result_type=output_schema,
            system_prompt=self._build_prompt()
        )
    
    async def recognize(self, image_data: ImageData) -> FormSchema:
        """执行识别"""
        result = await self.agent.run(
            user_prompt="识别图片中的表单内容",
            deps=image_data
        )
        return result.data
```

#### 4.1.3 ResultProcessor（结果处理器）
```python
class ResultProcessor:
    """处理和验证识别结果"""
    
    def process(
        self,
        raw_result: FormSchema,
        confidence_threshold: float = 0.5
    ) -> FormSchema:
        """后处理识别结果"""
        # 过滤低置信度字段
        filtered_fields = [
            f for f in raw_result.fields 
            if f.confidence >= confidence_threshold
        ]
        # 数据清洗
        cleaned = self._clean_data(filtered_fields)
        return FormSchema(
            form_type=raw_result.form_type,
            fields=cleaned,
            metadata=raw_result.metadata
        )
```

### 4.2 数据模型

#### FormField（表单字段）
```python
class FormField(BaseModel):
    """表单字段定义"""
    name: str = Field(
        description="字段名称/标签",
        min_length=1,
        max_length=200
    )
    value: str = Field(
        description="字段值",
        max_length=10000
    )
    field_type: Literal[
        "text", "number", "date", "checkbox", "select", "signature", "unknown"
    ] = Field(
        default="text",
        description="字段类型"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="识别置信度"
    )
    bbox: Optional[BoundingBox] = Field(
        default=None,
        description="边界框坐标"
    )
    raw_text: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="原始OCR文本"
    )
    
    class BoundingBox(BaseModel):
        x1: int = Field(ge=0, description="左上角X坐标")
        y1: int = Field(ge=0, description="左上角Y坐标")
        x2: int = Field(ge=0, description="右下角X坐标")
        y2: int = Field(ge=0, description="右下角Y坐标")
```

#### FormSchema（表单结构）
```python
class FormSchema(BaseModel):
    """表单数据结构"""
    form_type: str = Field(
        default="unknown",
        description="表单类型标识"
    )
    title: Optional[str] = Field(
        default=None,
        description="表单标题"
    )
    fields: list[FormField] = Field(
        default_factory=list,
        description="表单字段列表",
        min_length=0
    )
    page_info: Optional[PageInfo] = Field(
        default=None,
        description="页面信息"
    )
    metadata: dict = Field(
        default_factory=dict,
        description="元数据"
    )
    recognized_at: datetime = Field(
        default_factory=datetime.now,
        description="识别时间"
    )
    
    def to_json(self, indent: int = 2) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(indent=indent)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return self.model_dump()
```

### 4.3 Prompt设计

#### 系统Prompt
```python
SYSTEM_PROMPT = """你是一个专业的表单识别专家。你的任务是分析图片中的表单，提取所有字段信息。

提取规则：
1. 字段名称：识别字段的标签或标题，如"姓名"、"电话"等
2. 字段值：提取对应的数据内容
3. 字段类型判断：
   - text: 普通文本输入
   - number: 纯数字内容
   - date: 日期格式内容（YYYY-MM-DD）
   - checkbox: 复选框或单选框
   - select: 下拉选择框
   - signature: 签名区域
   - unknown: 无法确定类型

4. 置信度评分：
   - 0.9-1.0: 非常清晰，确定无疑
   - 0.7-0.9: 比较清晰，基本确定
   - 0.5-0.7: 一般清晰，可能有误
   - 0.0-0.5: 不清晰，识别困难

5. 边界框坐标（可选）：如果可能，提供字段在图片中的位置

注意事项：
- 不要遗漏任何可见的字段
- 对于空字段，value使用空字符串""
- 保持字段的原始顺序（从上到下、从左到右）
- 日期统一转换为YYYY-MM-DD格式
- 数字去除千分位符号，保留小数点
"""
```

## 5. 配置规范

### 5.1 配置文件

```yaml
# config/vision_agent.yaml
vision_agent:
  # 默认模型配置
  default_model: "gpt-4o"
  
  # 模型配置
  models:
    gpt-4o:
      provider: "openai"
      model_name: "gpt-4o"
      max_tokens: 4096
      temperature: 0.1
    
    claude-3-5-sonnet:
      provider: "anthropic"
      model_name: "claude-3-5-sonnet-20241022"
      max_tokens: 4096
      temperature: 0.1
    
    gemini-1.5-pro:
      provider: "google"
      model_name: "gemini-1.5-pro"
      max_tokens: 4096
      temperature: 0.1
  
  # 图片处理配置
  image_processing:
    max_file_size: 10485760  # 10MB
    max_image_size: 4096
    jpeg_quality: 85
    supported_formats: [".png", ".jpg", ".jpeg", ".bmp", ".webp"]
  
  # 识别参数
  recognition:
    default_confidence_threshold: 0.5
    include_bbox: false
    include_raw_text: false
    max_fields: 100
  
  # 重试配置
  retry:
    max_attempts: 3
    base_delay: 1.0
    max_delay: 10.0
    exponential_base: 2.0
  
  # 批处理配置
  batch:
    max_concurrency: 5
    queue_size: 100
```

### 5.2 环境变量

| 变量名 | 说明 | 必需 |
|-------|------|-----|
| OPENAI_API_KEY | OpenAI API密钥 | 使用OpenAI模型时 |
| ANTHROPIC_API_KEY | Anthropic API密钥 | 使用Anthropic模型时 |
| GOOGLE_API_KEY | Google API密钥 | 使用Gemini模型时 |
| VISION_AGENT_LOG_LEVEL | 日志级别 | 否，默认INFO |
| VISION_AGENT_CACHE_DIR | 缓存目录 | 否 |

## 6. API接口

### 6.1 Python API

```python
# 单张图片识别
async def recognize_image(
    image_path: str,
    model_name: str = "gpt-4o",
    **options
) -> RecognitionResponse:
    """识别单张图片"""

# 批量识别
async def batch_recognize(
    image_paths: list[str],
    model_name: str = "gpt-4o",
    max_concurrency: int = 5,
    **options
) -> list[RecognitionResponse]:
    """批量识别多张图片"""

# 自定义Schema识别
async def recognize_with_schema(
    image_path: str,
    output_schema: type[BaseModel],
    model_name: str = "gpt-4o"
) -> BaseModel:
    """使用自定义输出结构识别"""
```
