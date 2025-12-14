"""
Profile manager for the info_extract project.
Provides centralized management of configuration profiles.
"""
import textwrap
from typing import List, TypedDict, Optional

from langextract.core.data import ExampleData
from .config_db import ConfigDB


class ProfileInfo(TypedDict):
    id: int          # Profile's unique identifier
    name: str        # Profile's display name
    description: str # Profile's description
    is_default: bool # Whether this is the default profile
    isActive: bool   # Whether this is the currently active profile

class ColumnDefine(TypedDict):
    name: str
    dtype: str
    describe: Optional[str]


class ProfileManager:
    """
    Manages configuration profiles for the info_extract project.
    Provides methods for profile switching and management.
    """
    
    def __init__(self, db_path: Optional[str] = None, default_profile_id: int = 1):
        """
        Initialize the ProfileManager instance.
        
        Args:
            db_path: Path to the SQLite database. If None, uses default path.
            default_profile_id: ID of the default profile. Default is 1.
        """
        self.config_db = ConfigDB(db_path, default_profile_id)
        self.default_profile_id = default_profile_id
        self._current_profile_id = default_profile_id

    def get_available_profiles(self) -> List[ProfileInfo]:
        """
        Get all available profiles from the database.
        
        Returns:
            List of ProfileInfo objects
        """
        profiles = self.config_db.get_available_profiles()
        return [
            {
                'id': profile['id'],
                'name': profile['name'],
                'description': profile['description'] or '',
                'is_default': bool(profile['is_default']),
                'isActive': profile['id'] == self._current_profile_id
            }
            for profile in profiles
        ]

    def get_current_profile(self) -> ProfileInfo | None:
        """
        Get the currently active profile.
        
        Returns:
            ProfileInfo object for the current profile
        """
        current_profile_data = self.config_db.get_profile_by_id(self._current_profile_id)
        if current_profile_data:
            return {
                'id': current_profile_data['id'],
                'name': current_profile_data['name'],
                'description': current_profile_data['description'] or '',
                'is_default': bool(current_profile_data['is_default']),
                'isActive': True
            }
        return None

    def switch_profile(self, profile_id: int) -> bool:
        """
        Switch to the specified profile.
        
        Args:
            profile_id: ID of the profile to switch to
            
        Returns:
            True if the switch was successful, False otherwise
        """
        profile = self.config_db.get_profile_by_id(profile_id)
        if profile is None:
            return False
        
        # Update the active profile in the ConfigDB instance
        self.config_db.set_active_profile(profile_id)
        self._current_profile_id = profile_id
        return True

    def create_profile(self, name: str, description: str | None = None) -> int:
        """
        Create a new profile.
        
        Args:
            name: Name of the new profile
            description: Optional description of the new profile
            
        Returns:
            ID of the newly created profile
        """
        # Validate that the profile name doesn't already exist
        existing_profiles = self.config_db.get_available_profiles()
        for profile in existing_profiles:
            if profile['name'] == name:  # pyright: ignore[reportArgumentType]
                raise ValueError(f"Profile with name '{name}' already exists")
        
        return self.config_db.create_profile(name, description)

    def get_config_db(self) -> ConfigDB:
        """
        Get the ConfigDB instance for the current profile.
        
        Returns:
            Current ConfigDB instance
        """
        return self.config_db

    def get_current_profile_id(self) -> int:
        """
        Get the ID of the currently active profile.
        
        Returns:
            Current profile ID
        """
        return self._current_profile_id

    def output_info_items(self) -> list[ColumnDefine]:
        """
        提供excel输出的标准表头定义
        """    
        config_db = self.get_config_db()
        return [ ColumnDefine(name=info.label, dtype=info.data_type, describe=info.describe) for info in config_db.get_info_items()]

    def generate_info_item_define_prompt(self) -> str:
        """
        提供取数映射提示词
        """    
        config_db = self.get_config_db()
        info_items = config_db.get_info_items()
        prompt = ["# 以下是需要抽取的 ** 信息项 ** ："]

        for item in info_items:
            describe = "# " + item.describe if item.describe else ""
            prompt.append(f"- {item.label} : {item.data_type} {describe}")

        return "\n".join(prompt)

    def _sample_col(self, sample: str|None):
        if sample:
            return sample
        else:
            return  "null"

    def generate_sample_sql(self) -> str:    
        config_db = self.get_config_db()
        columns = [ f"{self._sample_col(item.sample_col_name)} as {item.label}" for item in config_db.get_info_items() ]
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

    def get_examples(self) -> list[ExampleData]:
        """
        从standard.db读取数据并生成一组 langextract.data.ExampleData
        """    
        config_db = self.get_config_db()

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

profile_manager = ProfileManager("./config/standard.db")
