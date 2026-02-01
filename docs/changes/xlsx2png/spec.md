# Excel转PNG功能规格说明

## 1. 功能概述

本功能实现将Excel文件(.xlsx/.xls)转换为PNG图片格式，主要面向Windows环境，提供高效、准确的表格转图片服务。

## 2. 功能需求

### 2.1 核心功能
1. **Excel文件读取**：支持读取.xlsx和.xls格式的Excel文件
2. **工作表选择**：支持转换指定工作表或全部工作表
3. **PNG图片生成**：将Excel内容转换为高质量PNG图片
4. **格式保留**：尽可能保留原始Excel的布局和基本样式

### 2.2 输入输出规范
#### 输入参数
- `excel_file_path` (string): Excel文件路径
- `output_png_path` (string): 输出PNG图片路径
- `sheet_name` (string, optional): 指定工作表名称，默认为第一个工作表
- `width` (int, optional): 输出图片宽度，默认自适应
- `height` (int, optional): 输出图片高度，默认自适应

#### 输出结果
- 成功：生成指定路径的PNG图片文件
- 失败：抛出异常并记录错误日志

### 2.3 性能指标
- 转换速度：单个工作表(100行×20列)转换时间不超过3秒
- 内存使用：转换过程内存占用不超过500MB
- 图片质量：输出PNG图片分辨率达到300 DPI

## 3. 非功能性需求

### 3.1 兼容性
- 运行环境：Windows 10/11, Python 3.13+
- Excel版本：支持Office 2016及以上版本
- 依赖库：openpyxl, pywin32, Pillow

### 3.2 错误处理
- 当Excel文件损坏时，抛出解析错误异常
- 当系统未安装Office时，给出明确提示信息
- 当文件路径不存在时，抛出文件不存在异常

### 3.3 安全性
- 验证输入文件类型，防止恶意文件注入
- 转换过程中对敏感信息进行适当处理

## 4. 技术实现

### 4.1 实现方案
采用COM组件方案，通过Windows COM接口与Excel应用程序交互：
- 使用`win32com.client`调用Excel应用程序
- 利用Excel内置的CopyPicture功能获取表格图像
- 通过Pillow处理和保存最终PNG图片

### 4.2 架构集成
- 在`src/info_extract/utils/excel.py`中实现核心转换功能
- 在`src/info_extract/source/excel.py`中集成到现有Excel处理流程
- 通过配置文件控制转换参数和启用选项

### 4.3 依赖管理
- `pywin32`: 用于COM组件交互
- `Pillow`: 用于图片处理
- `openpyxl`: 项目已有依赖，用于备用方案