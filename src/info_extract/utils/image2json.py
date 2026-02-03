"""
PNG表单识别与JSON导出功能

基于pydantic-ai框架的视觉表单识别系统，能够将图片（PNG/JPG等格式）中的表单内容
自动识别并结构化为JSON格式输出。

Usage:
    from info_extract.utils.image2json import recognize_image, batch_recognize

    # 单张图片识别
    result = await recognize_image("path/to/form.png")

    # 批量识别
    results = await batch_recognize(["form1.png", "form2.png"])
"""

from __future__ import annotations

import asyncio
import io
import os
import time
from pathlib import Path
from typing import Literal, Optional

from PIL import Image
from pydantic import BaseModel, Field
import pandas as pd

# pydantic-ai imports
from pydantic_ai import Agent, BinaryContent
from .model import qwen



# =============================================================================
# 异常类定义
# =============================================================================


class VisionAgentError(Exception):
    """视觉Agent错误基类"""

    def __init__(self, message: str, error_code: str = "E000"):
        self.error_code = error_code
        super().__init__(f"[{error_code}] {message}")


class ImageLoadError(VisionAgentError):
    """图片加载错误"""
    pass


class FileNotFoundImageError(ImageLoadError):
    """文件不存在错误 (E001)"""

    def __init__(self, path: str):
        super().__init__(f"图片文件不存在: {path}", "E001")


class UnsupportedFormatError(ImageLoadError):
    """格式不支持错误 (E002)"""

    def __init__(self, format: str):
        super().__init__(f"不支持的图片格式: {format}", "E002")


class CorruptedImageError(ImageLoadError):
    """图片损坏错误 (E003)"""

    def __init__(self, path: str):
        super().__init__(f"无法读取图片文件: {path}", "E003")


class ModelAPIError(VisionAgentError):
    """模型API错误 (E004)"""

    def __init__(self, message: str):
        super().__init__(message, "E004")


# =============================================================================
# 数据模型定义
# =============================================================================

class FormField(BaseModel):
    """表单字段定义"""

    name: str = Field(description="字段名称/标签", min_length=1, max_length=200)
    value: str = Field(description="字段值", max_length=10000)
    confidence: float = Field(description="识别置信度（0-1）")
    field_type: Literal[
        "text", "number", "date", "checkbox", "select", "signature", "unknown"
    ] = Field(default="text", description="字段类型")

class FormSchema(BaseModel):
    """表单数据结构"""
    title: Optional[str] = Field(default=None, description="表单标题")
    fields: list[FormField] = Field(default_factory=list, description="表单字段列表")



class RecognitionResponse(BaseModel):
    """识别响应结果"""

    success: bool = Field(description="识别是否成功")
    form_data: Optional[FormSchema] = Field(default=None, description="识别的表单数据")
    processing_time: float = Field(description="处理耗时（秒）")
    error_message: Optional[str] = Field(
        default=None, description="错误信息（如果失败）"
    )
    metadata: dict = Field(default_factory=dict, description="额外元数据")

    def to_pandas(self) -> pd.DataFrame | None:
        """将识别响应转换为Pandas DataFrame"""
        if self.form_data is None:
            return None
        data = {}
        for field in self.form_data.fields:
            data[field.name] = field.value
        return pd.DataFrame([data])

class ImageData:
    """图片数据内部类"""

    def __init__(self, data: bytes, original_size: tuple[int, int], format: str):
        self.data = data
        self.original_size = original_size
        self.format = format


# =============================================================================
# 配置模型
# =============================================================================
class ImageProcessingConfig(BaseModel):
    """图片处理配置"""

    max_file_size: int = Field(
        default=10 * 1200 * 1200, description="最大文件大小（字节）"
    )
    max_image_size: int = Field(default=4096, description="最大边长（像素）")
    jpeg_quality: int = Field(default=85, ge=1, le=100, description="JPEG压缩质量")
    supported_formats: list[str] = Field(
        default_factory=lambda: [".png", ".jpg", ".jpeg", ".bmp", ".webp"],
        description="支持的格式列表",
    )


class VisionAgentConfig(BaseModel):
    """主配置模型"""

    default_model: str = Field(default="qwen3-vl-plus", description="默认模型")
    model: str = Field(default="qwen3-vl-plus", description="模型名称")
    image_processing: ImageProcessingConfig = Field(
        default_factory=ImageProcessingConfig, description="图片处理配置"
    )


# =============================================================================
# Prompt模板
# =============================================================================


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


# =============================================================================
# 图片加载器
# =============================================================================
class ImageLoader:
    """负责图片的加载、验证和预处理"""

    SUPPORTED_FORMATS: set[str] = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    MAX_IMAGE_SIZE: int = 4096  # 最大边长

    def __init__(self, config: Optional[ImageProcessingConfig] = None):
        self.config = config or ImageProcessingConfig()

    def load(self, path: str) -> ImageData:
        """加载并预处理图片

        Args:
            path: 图片文件路径

        Returns:
            ImageData: 处理后的图片数据

        Raises:
            FileNotFoundImageError: 文件不存在
            UnsupportedFormatError: 格式不支持
            CorruptedImageError: 图片损坏
        """
        # 验证文件
        self._validate_file(path)

        try:
            # 加载图片
            with Image.open(path) as img:
                original_size = img.size
                original_format = img.format or "unknown"

                # 预处理
                processed = self._preprocess(img)

                return ImageData(
                    data=processed, original_size=original_size, format=original_format
                )
        except (IOError, OSError) as e:
            raise CorruptedImageError(path) from e

    def _validate_file(self, path: str) -> None:
        """验证文件

        Args:
            path: 文件路径

        Raises:
            FileNotFoundImageError: 文件不存在
            UnsupportedFormatError: 格式不支持
        """
        # 检查文件存在性
        if not os.path.exists(path):
            raise FileNotFoundImageError(path)

        # 检查文件大小
        file_size = os.path.getsize(path)
        if file_size > self.config.max_file_size:
            raise UnsupportedFormatError(
                f"文件大小 {file_size} 超过最大限制 {self.config.max_file_size}"
            )

        # 检查格式后缀
        ext = Path(path).suffix.lower()
        if ext not in self.config.supported_formats:
            raise UnsupportedFormatError(ext)

    def _preprocess(self, image: Image.Image) -> bytes:
        """预处理图片

        Args:
            image: PIL Image对象

        Returns:
            bytes: 处理后的图片字节数据
        """
        # RGBA/P模式转换为RGB
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # 尺寸调整（保持比例，最大边不超过限制）
        width, height = image.size
        max_size = self.config.max_image_size

        if max(width, height) > max_size:
            ratio = max_size / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # 保存为JPEG字节
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=self.config.jpeg_quality)
        return buffer.getvalue()


# =============================================================================
# 视觉Agent
# =============================================================================
class VisionFormAgent:
    """基于pydantic-ai的视觉识别Agent"""

    def __init__(
        self,
        custom_prompt: Optional[str] = None,
        config: Optional[VisionAgentConfig] = None,
    ):
        """初始化VisionFormAgent

        Args:
            custom_prompt: 自定义Prompt
            config: Agent配置
        """
        if Agent is None:
            raise ImportError("pydantic-ai未安装，无法使用VisionFormAgent")

        self.config = config or VisionAgentConfig()
        self.custom_prompt = custom_prompt

        # 创建Agent实例
        self.agent = Agent(
            model=qwen(self.config.model),
            output_type=FormSchema,
            instructions=self._get_system_prompt(),
        )

    def _get_system_prompt(self) -> str:
        """获取系统Prompt"""
        if self.custom_prompt:
            return self.custom_prompt
        return SYSTEM_PROMPT

    def _load_image(self, image_path: str) -> tuple[ImageData, str]:
        """加载图片"""
        loader = ImageLoader(self.config.image_processing)
        image_data = loader.load(image_path)
        return image_data, f"image/{image_data.format}"

    async def recognize(self, image_path: str) -> tuple[FormSchema, float]:
        """执行识别

        Args:
            image_path: 图片文件路径

        Returns:
            识别结果（FormSchema）

        Raises:
            ImageLoadError: 图片加载失败
            ModelAPIError: 模型API调用失败
        """
        start_time = time.time()

        try:
            # 加载图片
            image_data, media_type = self._load_image(image_path)

            # 调用Agent进行识别
            result = await self.agent.run(
                [
                    "请识别图片中的表单内容，提取所有字段及其值",
                    BinaryContent(data=image_data.data, media_type=media_type)
                ],
            )

            processing_time = time.time() - start_time


            return result.output, processing_time 

        except ImageLoadError:
            raise
        except Exception as e:
            raise ModelAPIError(f"模型调用失败: {str(e)}") from e


# =============================================================================
# 结果处理器
# =============================================================================


class ResultProcessor:
    """处理和验证识别结果"""

    def process(
        self, raw_result: FormSchema, confidence_threshold: float = 0.5
    ) -> FormSchema:
        """后处理识别结果

        Args:
            raw_result: 原始识别结果
            confidence_threshold: 置信度阈值

        Returns:
            处理后的FormSchema
        """
        # 过滤低置信度字段
        filtered_fields = self._filter_low_confidence(
            raw_result.fields, confidence_threshold
        )

        # 数据清洗
        cleaned = self._clean_data(filtered_fields)

        return FormSchema(
            title=raw_result.title,
            fields=cleaned,
        )

    def _filter_low_confidence(
        self, fields: list[FormField], threshold: float
    ) -> list[FormField]:
        """过滤低置信度字段"""
        return [f for f in fields if f.confidence >= threshold]

    def _clean_data(self, fields: list[FormField]) -> list[FormField]:
        """清洗数据"""
        cleaned_fields = []

        for field in fields:
            # 去除空白字符
            cleaned_value = field.value.strip()

            # 数字格式标准化（去除千分位）
            if field.field_type == "number":
                cleaned_value = cleaned_value.replace(",", "").replace(" ", "")

            # 创建清洗后的字段
            cleaned_field = FormField(
                name=field.name.strip(),
                value=cleaned_value,
                field_type=field.field_type,
                confidence=field.confidence,
            )

            cleaned_fields.append(cleaned_field)

        return cleaned_fields


# =============================================================================
# 高级API函数
# =============================================================================


async def recognize_image(
    image_path: str,
    confidence_threshold: float = 0.5,
    include_bbox: bool = False,
    include_raw_text: bool = False,
    custom_prompt: Optional[str] = None,
) -> RecognitionResponse:
    """识别单张图片

    Args:
        image_path: 图片文件路径
        confidence_threshold: 置信度阈值
        include_bbox: 是否包含边界框坐标
        include_raw_text: 是否包含原始OCR文本
        custom_prompt: 自定义Prompt

    Returns:
        RecognitionResponse: 识别响应结果
    """
    start_time = time.time()

    try:
        # 创建Agent
        agent = VisionFormAgent(
            custom_prompt=custom_prompt
        )

        # 执行识别
        form_data, processing_time = await agent.recognize(image_path)

        # 处理结果
        processor = ResultProcessor()
        processed_data = processor.process(form_data, confidence_threshold)

        return RecognitionResponse(
            success=True,
            form_data=processed_data,
            processing_time=processing_time,
            metadata={
                "confidence_threshold": confidence_threshold,
                "include_bbox": include_bbox,
                "include_raw_text": include_raw_text,
            },
        )

    except VisionAgentError as e:
        processing_time = time.time() - start_time
        return RecognitionResponse(
            success=False,
            form_data=None,
            processing_time=processing_time,
            error_message=str(e),
            metadata={"error_code": e.error_code},
        )
    except Exception as e:
        processing_time = time.time() - start_time
        return RecognitionResponse(
            success=False,
            form_data=None,
            processing_time=processing_time,
            error_message=f"未知错误: {str(e)}",
            metadata={"error_code": "E999"},
        )


async def batch_recognize(
    image_paths: list[str],
    max_concurrency: int = 5,
    confidence_threshold: float = 0.5,
    include_bbox: bool = False,
    include_raw_text: bool = False,
    custom_prompt: Optional[str] = None,
) -> list[RecognitionResponse]:
    """批量识别多张图片

    Args:
        image_paths: 图片路径列表
        max_concurrency: 最大并发数
        confidence_threshold: 置信度阈值
        include_bbox: 是否包含边界框坐标
        include_raw_text: 是否包含原始OCR文本
        custom_prompt: 自定义Prompt

    Returns:
        list[RecognitionResponse]: 识别结果列表
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def recognize_with_limit(path: str) -> RecognitionResponse:
        async with semaphore:
            return await recognize_image(
                image_path=path,
                confidence_threshold=confidence_threshold,
                include_bbox=include_bbox,
                include_raw_text=include_raw_text,
                custom_prompt=custom_prompt,
            )

    tasks = [recognize_with_limit(path) for path in image_paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常结果
    processed_results: list[RecognitionResponse] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(
                RecognitionResponse(
                    success=False,
                    form_data=None,
                    processing_time=0.0,
                    error_message=f"处理异常: {str(result)}",
                    metadata={"path": image_paths[i], "error_code": "E999"},
                )
            )
        elif isinstance(result, RecognitionResponse):
            processed_results.append(result)

    return processed_results


# =============================================================================
# 便捷函数
# =============================================================================
def validate_image(image_path: str) -> tuple[bool, Optional[str]]:
    """验证图片文件

    Args:
        image_path: 图片文件路径

    Returns:
        tuple: (是否有效, 错误信息)
    """
    try:
        loader = ImageLoader()
        loader._validate_file(image_path)
        return True, None
    except ImageLoadError as e:
        return False, str(e)
