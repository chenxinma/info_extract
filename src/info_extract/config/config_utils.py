"""
Utility functions for converting configuration data between database and file formats.
"""
import textwrap
from typing import Optional, TypedDict
from .profile_manager import ProfileManager
from langextract.data import ExampleData

class ColumnDefine(TypedDict):
    name: str
    dtype: str
    describe: Optional[str]


def initialize_profile_manager(db_path: str = "./config/standard.db", profile_id: int = 1):
    """
    Initialize the global profile manager instance.
    
    Args:
        db_path: Path to the database file
        profile_id: ID of the profile to use initially
    """
    return ProfileManager(db_path, profile_id)

profile_manager: ProfileManager = initialize_profile_manager()


def output_info_items() -> list[ColumnDefine]:
    """
    提供excel输出的标准表头定义
    """    
    config_db = profile_manager.get_config_db()
    return [ ColumnDefine(name=info.label, dtype=info.data_type, describe=info.describe) for info in config_db.get_info_items()]

def generate_info_item_define_prompt() -> str:
    """
    提供取数映射提示词
    """    
    config_db = profile_manager.get_config_db()
    info_items = config_db.get_info_items()
    prompt = ["# 以下是需要抽取的 ** 信息项 ** ："]

    for item in info_items:
        describe = "# " + item.describe if item.describe else ""
        prompt.append(f"- {item.label} : {item.data_type} {describe}")

    return "\n".join(prompt)

def _sample_col(sample: str|None):
    if sample:
        return sample
    else:
        return  "null"

def generate_sample_sql() -> str:    
    config_db = profile_manager.get_config_db()
    columns = [ f"{_sample_col(item.sample_col_name)} as {item.label}" for item in config_db.get_info_items() ]
    sql = textwrap.dedent(
            f"""
            输出样例：
            ```sql
            SELECT
                {",".join(columns)}
            FROM df
            ```
            只生产单一SELECT语句。
            """)
    return sql

def get_examples() -> list[ExampleData]:
    """
    从standard.db读取数据并生成一组 langextract.data.ExampleData
    """    
    config_db = profile_manager.get_config_db()

    # Get all examples
    examples = config_db.get_examples()
    result = []

    for example in examples:
        # Get extractions for this example
        extraction_sets = config_db.get_extractions_by_example_id(example.id)

        # Process each extraction to create langextract.data.Extraction objects
        extraction_objects = []

        for e_id, extraction_obj in extraction_sets:
            extraction_objects.append(extraction_obj)

            attributes = config_db.get_attributes_by_extraction_id(e_id)

            # Set attributes if any exist
            if attributes:
                extraction_obj.attributes = attributes # type: ignore



        # Create the langextract.data.ExampleData object
        example_data = ExampleData(
            text=example.fragment or "",
            extractions=extraction_objects
        )

        result.append(example_data)

    return result


def get_cached_mapping_sql(hash_key: str) -> str|None:
    """
    从standard.db读取hash_key(表头完全一致)的sql
    """
    config_db = profile_manager.get_config_db()
    return config_db.get_mapping_sql_by_hash_key(hash_key)


def save_mapping_sql(hash_key:str, sql_code: str):
    """
    保存生成的sql到standard.db
    """
    config_db = profile_manager.get_config_db()
    config_db.save_mapping_sql(hash_key=hash_key, sql_code=sql_code)
