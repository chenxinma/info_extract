from pathlib import Path
from typing import Tuple

import langextract as lx
import yaml

def load_examples(examples_file: Path) -> Tuple[str, list[lx.data.ExampleData]]:
    """
    加载示例
    Args:
        examples_file: 示例文件路径
    Returns:
        提示词和示例列表
    """
    # 读取示例文件
    with open(examples_file, "r", encoding="utf-8") as f:
        example_list = yaml.safe_load(f)
        prompt = example_list["prompt"]
        examples = []
        for example in example_list["examples"]:
            extractions = []
            for extr in example["extractions"]:
                extract = lx.data.Extraction(
                    extraction_class = extr["extraction_class"].strip(),
                    extraction_text = str(extr["extraction_text"]).strip()
                )
                if "attributes" in extr:
                    extract.attributes = extr["attributes"]
                extractions.append(extract)
            examples.append(lx.data.ExampleData(
                text = example["fragment"].strip(),
                extractions = extractions
            ))
    return prompt, examples