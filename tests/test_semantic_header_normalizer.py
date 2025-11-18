import json
import unittest
from info_extract.config.config_utils import output_info_items
from info_extract.extract.dataframe_mapping_extract import SemanticHeaderNormalizer, ColumnUtil

class TestSemanticHeaderNormalizer(unittest.TestCase):
    def setUp(self):
        info_items = output_info_items()
        standard_headers = [ item["name"] for item in info_items ]
        standard_describes = [ item["describe"] for item in info_items ]
        self.normalizer = SemanticHeaderNormalizer(standard_headers, standard_describes)

    # @unittest.skip("skip match.")
    def test_normalize_with_context(self):
        columns = [
            "序号",
            "公司名称",
            "姓名",
            "身份证号码",
            "联系电话(手机)",
            "工号",
            "部门",
            "电子邮件地址",
            "联系地址",
            "户籍信息\n（XX省XX市）",
            "劳动合同起始日期\n（xxxx-xx-xx)",
            "劳动合同终止日期\n（xxxx-xx-xx)",
            "缴纳起始月\n（xxxx.xx)",
            "参保地",
            "账户类型",
            "社保基数",
            "公积金基数",
            "公积金比例\n（x%+x%）",
            "员工本人银行帐号",
            "开户行详情\n（XX银行XX市XX支行）",
            "劳动合同是否电子签",
            "岗位类型",
            "个人身份",
            "行颜色"
        ]
        cleaned_columns = [ ColumnUtil.advanced_clean_text(col) for col in columns ]
        result = self.normalizer.normalize(cleaned_columns, 0.57)
        print("标准化结果:")
        for std, col, confidence_scores in result["normalized"]:
            print(f"  '{std}' -> '{col}' (置信度: {confidence_scores:.3f})")
