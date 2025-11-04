# 实现任务：添加 PDF 源支持

## 任务

### 任务：环境设置
- [ ] 添加 PDF 解析库依赖（PyPDF2 或 pdfminer.six）
- [ ] 更新 pyproject.toml 文件中的新依赖

### 任务：PDF 读取器实现
- [ ] 创建 src/info_extract/source/pdf.py
- [ ] 实现继承自 Step 的 PDFReader 类
- [ ] 添加 PDF 文本提取功能
- [ ] 将提取的文本保存为处理目录中的 txt 文件

### 任务：集成
- [ ] 更新 main.py 管道以包含 PDFReader
- [ ] 确保 PDF 文件按正确顺序处理

### 任务：测试
- [ ] 创建各种格式的测试 PDF 文件
- [ ] 验证文本提取准确性
- [ ] 测试与现有 PlainExtractor 的集成

### 任务：文档
- [ ] 更新 README.md 中的 PDF 支持信息
- [ ] 将 PDF 规范添加到 docs/specs/source/spec.md
- [ ] 更新使用说明