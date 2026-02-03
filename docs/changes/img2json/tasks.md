# PNG表单识别与JSON导出功能任务分解

## 说明

本任务基于以下设计文档：
- proposal.md: 定义了单文件架构（`src/info_extract/utils/image2json.py`），包含图片预处理、VisionFormAgent实现、FormSchema定义
- spec.md: 定义了详细的功能规格、数据模型、Prompt设计、配置规范

## 1. 项目准备任务

- [x] 创建项目目录结构 (docs/changes/img2json/)
- [x] 审核设计方案可行性

## 2. 核心文件实现任务

### 2.1 创建主文件结构
- [x] 创建 `src/info_extract/utils/image2json.py`
  - [x] 添加文件头注释和模块文档字符串
  - [x] 规划代码结构区域（Imports/Models/Loader/Agent/Processor/API）

### 2.2 Pydantic数据模型实现
- [x] 实现 `BoundingBox` 嵌套模型
  - [x] x1, y1, x2, y2: int 字段（ge=0）
- [x] 实现 `FormField` 模型
  - [x] name: str 字段（min_length=1, max_length=200）
  - [x] value: str 字段（max_length=10000）
  - [x] field_type: Literal["text", "number", "date", "checkbox", "select", "signature", "unknown"]
  - [x] confidence: float 字段（ge=0.0, le=1.0）
  - [x] bbox: Optional[BoundingBox]
  - [x] raw_text: Optional[str]（max_length=10000）
  - [x] 添加 Config 配置和示例
- [x] 实现 `FormSchema` 主模型
  - [x] form_type: str（default="unknown"）
  - [x] title: Optional[str]
  - [x] fields: list[FormField]（default_factory=list）
  - [x] page_info: Optional[PageInfo]
  - [x] metadata: dict（default_factory=dict）
  - [x] recognized_at: datetime（default_factory=datetime.now）
  - [x] 实现 to_json() 和 to_dict() 方法
- [x] 实现 `PageInfo` 模型（边界框、页面尺寸等）
- [x] 实现 `RecognitionRequest` 请求模型
  - [x] image_path: str
  - [x] model_name: str（default="gpt-4o"）
  - [x] output_schema: Optional[type[BaseModel]]
  - [x] confidence_threshold: float（ge=0.0, le=1.0, default=0.5）
  - [x] include_bbox: bool（default=False）
  - [x] include_raw_text: bool（default=False）
  - [x] custom_prompt: Optional[str]
- [x] 实现 `RecognitionResponse` 响应模型
  - [x] success: bool
  - [x] form_data: Optional[FormSchema]
  - [x] processing_time: float
  - [x] model_used: str
  - [x] error_message: Optional[str]
  - [x] metadata: dict
- [x] 实现 `ImageData` 内部数据类
  - [x] data: bytes（处理后图片数据）
  - [x] original_size: tuple[int, int]
  - [x] format: str

### 2.3 图片加载与预处理
- [x] 实现 `ImageLoader` 类
  - [x] 类常量定义
    - [x] SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    - [x] MAX_FILE_SIZE = 10 * 1024 * 1024（10MB）
    - [x] MAX_IMAGE_SIZE = 4096
  - [x] `load(path: str) -> ImageData` 方法
    - [x] 调用 _validate_file 验证
    - [x] 使用 PIL.Image.open 加载
    - [x] 调用 _preprocess 预处理
    - [x] 返回 ImageData
  - [x] `_validate_file(path: str)` 私有方法
    - [x] 检查文件存在性（FileNotFoundError）
    - [x] 检查文件大小（ValueError）
    - [x] 检查格式后缀（ValueError）
  - [x] `_preprocess(image: Image) -> bytes` 私有方法
    - [x] RGBA/P 模式转换为 RGB
    - [x] 尺寸调整（保持比例，最大边 <= 4096）
    - [x] JPEG 压缩（quality=85）
    - [x] 返回 bytes
- [x] 添加异常处理
  - [x] FileNotFoundError（E001）
  - [x] ValueError 格式不支持（E002）
  - [x] IOError 图片损坏（E003）

### 2.4 Prompt模板定义
- [x] 定义 `SYSTEM_PROMPT` 常量
  - [x] 角色定义：专业表单识别专家
  - [x] 字段提取规则说明
  - [x] 字段类型判断说明（text/number/date/checkbox/select/signature/unknown）
  - [x] 置信度评分标准（0.9-1.0/0.7-0.9/0.5-0.7/0.0-0.5）
  - [x] 边界框坐标说明
  - [x] 注意事项（空字段处理、日期格式、数字格式等）
- [x] 支持自定义Prompt注入逻辑

### 2.5 视觉Agent实现
- [x] 实现模型注册表 `MODEL_REGISTRY`
  - [x] 支持 "gpt-4o"（OpenAI）
  - [x] 支持 "gpt-4o-mini"（OpenAI）
  - [x] 支持 "claude-3-5-sonnet"（Anthropic）
  - [x] 支持 "claude-3-opus"（Anthropic）
  - [x] 工厂函数实现
- [x] 实现 `VisionFormAgent` 类
  - [x] `__init__()` 构造函数
    - [x] model_name: str 参数
    - [x] api_key: Optional[str] 参数
    - [x] output_schema: type[BaseModel] 参数（default=FormSchema）
    - [x] 从 MODEL_REGISTRY 创建模型实例
    - [x] 创建 pydantic_ai.Agent 实例
    - [x] 配置 system_prompt
    - [x] 配置 result_type
    - [x] 配置 retries=3
  - [x] `_get_system_prompt()` 方法
    - [x] 返回 SYSTEM_PROMPT
  - [x] `_load_image(image_path: str) -> ImageData` 方法
    - [x] 使用 ImageLoader 加载图片
  - [x] `recognize(image_path: str) -> FormSchema` 异步方法
    - [x] 加载图片数据
    - [x] 调用 agent.run()
    - [x] 处理结果并返回
- [x] 实现结果验证器（result_validator）
  - [x] 检查低置信度字段比例
  - [x] 触发 RetryPrompt 重试逻辑

### 3.6 结果处理器实现
- [x] 实现 `ResultProcessor` 类
  - [x] `process(raw_result: FormSchema, confidence_threshold: float = 0.5) -> FormSchema` 方法
    - [x] 调用 _filter_low_confidence 过滤
    - [x] 调用 _clean_data 清洗
    - [x] 返回处理后的 FormSchema
  - [x] `_filter_low_confidence(fields: list[FormField], threshold: float)` 私有方法
  - [x] `_clean_data(fields: list[FormField])` 私有方法
    - [x] 去除空白字符（strip）
    - [x] 日期格式统一（YYYY-MM-DD）
    - [x] 数字格式标准化（去除千分位）

### 3.7 配置模型实现
- [x] 实现 `ModelConfig` Pydantic模型
  - [x] provider: str
  - [x] model_name: str
  - [x] max_tokens: int（default=4096）
  - [x] temperature: float（default=0.1）
- [x] 实现 `ImageProcessingConfig` 模型
  - [x] max_file_size: int
  - [x] max_image_size: int
  - [x] jpeg_quality: int
  - [x] supported_formats: list[str]
- [x] 实现 `RetryConfig` 模型
  - [x] max_attempts: int（default=3）
  - [x] base_delay: float（default=1.0）
  - [x] max_delay: float（default=10.0）
  - [x] exponential_base: float（default=2.0）
- [x] 实现 `VisionAgentConfig` 主配置模型
  - [x] default_model: str
  - [x] models: dict[str, ModelConfig]
  - [x] image_processing: ImageProcessingConfig
  - [x] retry: RetryConfig

### 3.8 高级API函数实现
- [x] 实现 `recognize_image()` 异步函数
  - [x] 参数：image_path, model_name="gpt-4o", **options
  - [x] 返回：RecognitionResponse
  - [x] 处理流程：
    - [x] 创建 VisionFormAgent 实例
    - [x] 调用 recognize() 方法
    - [x] 使用 ResultProcessor 处理结果
    - [x] 构建 RecognitionResponse
    - [x] 异常处理包装
- [x] 实现 `batch_recognize()` 异步函数
  - [x] 参数：image_paths: list[str], model_name="gpt-4o", max_concurrency=5, **options
  - [x] 返回：list[RecognitionResponse]
  - [x] 使用 asyncio.Semaphore 控制并发
  - [x] 实现部分失败处理（gather with return_exceptions）
- [x] 实现 `recognize_with_schema()` 异步函数
  - [x] 参数：image_path, output_schema: type[BaseModel], model_name="gpt-4o"
  - [x] 返回：BaseModel（自定义Schema实例）

### 3.9 异常类定义
- [x] 实现 `VisionAgentError` 基类（继承 Exception）
- [x] 实现 `ImageLoadError`（继承 VisionAgentError）
  - [x] 错误代码 E001-E003
- [x] 实现 `ModelAPIError`（继承 VisionAgentError）
  - [x] 错误代码 E004
- [x] 实现 `RecognitionError`（继承 VisionAgentError）
  - [x] 错误代码 E005
- [x] 实现 `ConfigError`（继承 VisionAgentError）
  - [x] 错误代码 E006

### 3.10 辅助函数
- [x] 实现 `get_supported_models()` 获取支持的模型列表
- [x] 实现 `validate_image()` 验证图片文件
- [x] 实现 `register_model()` 注册自定义模型

## 4. 模块导出任务

- [x] 更新 `src/info_extract/utils/__init__.py` 导出 image2json 的所有公共API
  - [x] 异常类导出
  - [x] 数据模型导出
  - [x] 配置模型导出
  - [x] 核心类导出
  - [x] API函数导出
  - [x] 工具函数导出

## 5. 代码质量任务（待完成）

- [ ] 运行 ruff 代码检查：`ruff check src/info_extract/utils/image2json.py`
- [ ] 运行 ruff 格式化：`ruff format src/info_extract/utils/image2json.py`
- [ ] 运行 mypy 类型检查：`mypy src/info_extract/utils/image2json.py`
- [ ] 确保单元测试覆盖率 > 80%
- [ ] 检查 pydantic-ai 导入是否正确
- [ ] 验证所有类型注解


## 任务优先级

### P0 - 核心功能（必须完成）
- [x] 依赖管理任务
- [x] 2.1-2.5（主文件结构、数据模型、图片处理、Agent实现）
- [x] 3.6-3.10（结果处理、配置、高级API、异常类、辅助函数）
- [x] 4（模块导出）

### P1 - 重要功能（应该完成）
- [ ] 5（代码质量检查）

### P2 - 增强功能（可以完成）
- [ ] 创建 `config/vision_agent.yaml` 模板（可选）
- [ ] 创建 `tests/utils/test_image2json.py` 单元测试（可选）


## 实现总结

**已完成的核心功能：**

1. **数据模型层**：实现了 BoundingBox、PageInfo、FormField、FormSchema、RecognitionRequest、RecognitionResponse 等所有 Pydantic 模型，包含完整的验证规则和示例配置。

2. **图片处理层**：ImageLoader 类实现了完整的图片验证、加载和预处理流程，支持格式检查、大小限制、模式转换和JPEG压缩。

3. **视觉Agent层**：VisionFormAgent 基于 pydantic-ai 框架实现，支持多模型（OpenAI、Anthropic），内置重试机制和结果验证器。

4. **结果处理层**：ResultProcessor 实现置信度过滤和数据清洗功能。

5. **配置层**：完整的配置模型体系（ModelConfig、ImageProcessingConfig、RetryConfig、VisionAgentConfig）。

6. **API层**：提供 recognize_image、batch_recognize、recognize_with_schema 三个高级API函数，支持并发控制和异常处理。

7. **异常处理**：完整的异常类层次结构（E001-E006），每个错误都有对应的异常类型。

8. **模块导出**：utils 模块 __init__.py 已更新，所有公共API均可从 info_extract.utils 导入。

**文件位置：** `src/info_extract/utils/image2json.py`

