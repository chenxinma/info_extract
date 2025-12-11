# 与AI协作开发一个结构化信息提取工具

> 用「Spec Coding」六步法，把需求变代码，把代码变资产。

## 问题与选择

| 痛点                         | 结果          |
| -------------------------- | ----------- |
| 客户文档格式多变（邮件 / Excel / PDF） | 人工提取效率低、易出错 |

**解法** &#x20;

- 不选「Vibe Coding」想到哪写到哪
- 选「Spec Coding」先立规范、再落地

  → 需求明确、流程可标准化，更适合 HR 场景

## Spec Coding 六步协作流程

| 步骤     | 目标            | 关键产出                                                                                 | 一句话提醒           |
| ------ | ------------- | ------------------------------------------------------------------------------------ | --------------- |
| ① 订立规范 | 给 AI 植入项目 DNA | 文档模板 + 规范说明                                                                          | 规范越细，AI 越稳      |
| ② 需求传达 | 把口语需求变结构化     | \[proposal.md]\(<http://proposal.md> "proposal.md")                                  | 场景 + 预期结果，缺一不可  |
| ③ 方案审查 | 敲定技术细节        | \[spec.md]\(<http://spec.md> "spec.md") + \[tasks.md]\(<http://tasks.md> "tasks.md") | 任务必须可执行、可验收     |
| ④ 代码实现 | AI 按图索骥写代码    | 功能代码                                                                                 | 边界异常必须提前提       |
| ⑤ 验证测试 | 人机联合质保        | 测试报告                                                                                 | 100% 信任 AI = 埋雷 |
| ⑥ 规范归档 | 把成果变资产        | specs/ 目录                                                                            | 不归档 = 白干        |

### 示范对话（第④步）

**用户**：
请实现`src/info_extract/source/excel.py`，创建`ExcelReader` 类。

**AI**：

```python title="excel.py"
class ExcelReader(Step):
    """处理Excel文件，提取sheet内容"""
    def __init__(self, source_dir: str = "source", processing_dir: str = "processing"):
        """
        初始化Excel处理器
        
        Args:
            source_dir: 源文件目录路径
            processing_dir: 处理后文件保存目录路径
        """
        self.source_dir = Path(source_dir)
        self.processing_dir = Path(processing_dir)
    
    async def run(self) -> AsyncGenerator[StepResult, None]:
        """
        处理Excel文件xls或xlsx，提取sheet内容
        
        Yields:
            按sheet返回parquest文件路径
        """
        _files = self.source_files(self.source_dir, "*.xls*")
        logger.info(f"找到 {len(_files)} 个excel文件")

        for excel_file in _files:
            book = load_workbook(str(excel_file))
            for sheet_name in book.sheetnames:
                sheet = book[sheet_name]

```


**用户**：
补充错误处理：跳过excel打开时产生的临时文件，对于workbook里隐藏的Sheet也不要处理直接跳过。

**AI**：

```python 
    async def run(self) -> AsyncGenerator[StepResult, None]:
        """
        处理Excel文件xls或xlsx，提取sheet内容
        
        Yields:
            按sheet返回parquest文件路径
        """
        _files = self.source_files(self.source_dir, "*.xls*")
        logger.info(f"找到 {len(_files)} 个excel文件")

        for excel_file in _files:
            if excel_file.stem.endswith("~"):
                continue
            book = load_workbook(str(excel_file))
            for sheet_name in book.sheetnames:
                sheet = book[sheet_name]
                # 检查sheet是否为隐藏状态，如果是则跳过
                if sheet.sheet_state == 'hidden' or sheet.sheet_state == 'veryHidden':
                    logger.debug(f"sheet {sheet_name} 是隐藏状态，已跳过处理")
                    continue
                
```


## 四大实践心法

1. **文档即契约** &#x20;

   模板 ≈ 法律，越清晰 AI 越不敢「胡来」。
2. **小步快跑** &#x20;

   把「Excel支持」拆成环境 → 读取 → 集成 → 测试，一口气吃不成胖子。
3. **对话式调试** &#x20;

   把 AI 当编译器：报错不重来，逐步引导修正。
4. **人不离场** &#x20;

   需求 / 架构 / 验收，三道关必须人类签字。

## 总结与定位

- **Spec Coding**≠ AI 自动驾驶 &#x20;

  \=「人决策 + AI 加速」的规范化协作
- 适用场景 &#x20;

  需求明确、流程可标准化的**中等复杂度**项目
- 未来展望 &#x20;

  随着 AI 能力增强，「规范 + 人机协同」将成为软件开发新常态。
