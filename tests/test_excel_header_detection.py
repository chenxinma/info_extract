"""
测试Excel表头检测算法的不同实现
"""

import unittest
from pathlib import Path
import tempfile
from openpyxl import Workbook
from src.info_extract.source.excel import ExcelReader
from tqdm import tqdm


def create_test_excel_with_headers():
    """创建带有不同类型表头的测试Excel文件"""
    wb = Workbook()
    ws = wb.active
    ws.title = "TestSheet" # type: ignore

    # 在不同行添加不同的标题组合
    ws['A1'] = '无关数据' # type: ignore
    ws['B1'] = '其他信息' # type: ignore
    
    ws['A2'] = '' # type: ignore
    ws['B2'] = '' # type: ignore
    
    ws['A3'] = '姓名' # type: ignore
    ws['B3'] = '身份证号' # type: ignore
    ws['C3'] = '年龄' # type: ignore
    
    ws['A4'] = '张三' # type: ignore
    ws['B4'] = '110101199003071234' # type: ignore
    ws['C4'] = '30' # type: ignore
    
    ws['A5'] = '李四' # type: ignore
    ws['B5'] = '110101198506125678' # type: ignore
    ws['C5'] = '35' # type: ignore

    # 创建临时文件
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    wb.save(temp_file.name)
    return temp_file.name


def improved_find_header_row(sheet,
                           header_candidates=None,
                           max_scan_rows=10,
                           blanks_ratio=0.5,
                           fuzzy_match_threshold=0.8):
    """
    改进的表头行查找算法
    """
    ncols = max(sheet.max_column, 1)
    
    for r_idx, row in enumerate(sheet.iter_rows(min_row=1,
                                     max_row=min(max_scan_rows, sheet.max_row)),
                            start=0):
        row_values = [cell.value for cell in row]
        
        # 1. 空值比例策略
        non_blanks = sum(1 for v in row_values if v is not None and str(v).strip() != '')
        if non_blanks / ncols < (1 - blanks_ratio):
            continue

        # 2. 关键字策略（如果调用者给了关键字列表）
        if header_candidates:
            # 使用模糊匹配检查header_candidates中的关键词
            matched_count = 0
            for candidate in header_candidates:
                if any(candidate.lower() in str(cv).lower().strip() if cv else '' 
                      for cv in row_values if cv is not None):
                    matched_count += 1
            
            # 检查匹配数量是否达到阈值
            if matched_count / len(header_candidates) >= fuzzy_match_threshold:
                return r_idx
        else:
            # 如果没有提供候选关键词，则仅基于空值比例和其他启发式规则
            # 检查该行是否看起来像表头（例如，没有连续的相同值）
            unique_values = set(str(v).strip() if v else '' for v in row_values if v is not None and str(v).strip() != '')
            
            # 表头行通常包含相对独特的值，而不是重复的数据
            if len(unique_values) / ncols > 0.7:  # 至少70%的列是唯一的
                return r_idx
    
    # 如果没有找到匹配的行，返回-1
    return -1


class TestExcelHeaderDetection(unittest.TestCase):

    def setUp(self):
        self.excel_reader = ExcelReader()
        self.test_file = create_test_excel_with_headers()

    def tearDown(self):
        # 删除临时文件
        Path(self.test_file).unlink()

    @unittest.skip("s1")
    def test_current_vs_improved_algorithm_with_candidates(self):
        """比较现有算法和改进算法在有候选关键词的情况下的表现"""
        from openpyxl import load_workbook
        wb = load_workbook(self.test_file)
        ws = wb.active

        # 测试现有算法
        current_result = self.excel_reader.find_header_row(ws, header_candidates=["姓名", "身份证"])
        
        # 测试改进算法
        improved_result = improved_find_header_row(ws, header_candidates=["姓名", "身份证"])

        print(f"Current algorithm result with candidates: {current_result}")
        print(f"Improved algorithm result with candidates: {improved_result}")

        # 两种算法都应该找到第2行（索引为2，因为从0开始）作为表头
        self.assertEqual(current_result, 2, "当前算法应找到第3行（索引为2）作为表头")
        self.assertEqual(improved_result, 2, "改进算法应找到第3行（索引为2）作为表头")

    @unittest.skip("s2")
    def test_current_vs_improved_algorithm_without_candidates(self):
        """比较现有算法和改进算法在没有候选关键词的情况下的表现"""
        from openpyxl import load_workbook
        wb = load_workbook(self.test_file)
        ws = wb.active

        # 测试现有算法（无候选关键词）
        current_result = self.excel_reader.find_header_row(ws, header_candidates=None)

        # 测试改进算法（无候选关键词）
        improved_result = improved_find_header_row(ws, header_candidates=None)

        print(f"Current algorithm result without candidates: {current_result}")
        print(f"Improved algorithm result without candidates: {improved_result}")

        # 注意：当前算法在没有候选关键词时可能会返回第一行（索引0），而改进算法能更智能地识别真正的表头
        # 改进算法应该能找到第2行，因为它更符合表头的特征
        self.assertEqual(improved_result, 2, "改进算法应找到第3行（索引为2）作为表头")
        # 对于当前算法，由于其行为与改进算法不同，我们只记录其行为而不强制相等
        print(f"Current algorithm found row {current_result}, improved algorithm found row {improved_result}")

    @unittest.skip("s3")
    def test_improved_algorithm_fuzzy_matching(self):
        """测试改进算法的模糊匹配能力"""
        from openpyxl import load_workbook
        wb = load_workbook(self.test_file)
        ws = wb.active
        
        # 使用部分匹配的关键词
        result = improved_find_header_row(ws, header_candidates=["姓", "身份"])
        print(f"Improved algorithm result with partial matches: {result}")
        
        # 应该找到第2行，因为它包含"姓名"和"身份证号"
        self.assertEqual(result, 2, "改进算法应能识别部分匹配的关键词")

    @unittest.skip("s4")
    def test_improved_algorithm_tolerance_to_missing_keys(self):
        """测试改进算法对缺少关键词的容忍度"""
        from openpyxl import load_workbook
        wb = load_workbook(self.test_file)
        ws = wb.active
        
        # 提供一个不存在的关键词，但保持阈值较低
        result = improved_find_header_row(ws, header_candidates=["姓名", "不存在的列"], 
                                        fuzzy_match_threshold=0.5)
        print(f"Improved algorithm result with one missing key: {result}")
        
        # 因为我们设置了较低的阈值，所以应该仍能找到表头
        self.assertEqual(result, 2, "改进算法应在低阈值下容忍部分缺失的关键词")

        # 当阈值较高时，找不到匹配项
        result2 = improved_find_header_row(ws, header_candidates=["姓名", "不存在的列"], 
                                        fuzzy_match_threshold=0.9)
        print(f"Improved algorithm result with high threshold and missing key: {result2}")
        
        # 应该返回-1，因为未达到高阈值
        self.assertEqual(result2, -1, "改进算法应在高阈值下不接受缺失的关键词")

    def test_act_compare(self):
        from openpyxl import load_workbook

        test_files = list(Path("/home/macx/work/tmp/source").glob("*.xls*"))
        for f in test_files:
            if f.stem.endswith("~"):
                continue
            wb = load_workbook(f)
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                # 检查sheet是否为隐藏状态，如果是则跳过
                if sheet.sheet_state == 'hidden' or sheet.sheet_state == 'veryHidden':
                    continue
                expect_header_row = self.excel_reader.find_header_row(sheet, header_candidates=["姓名","身份证"])
                actual_header_row = improved_find_header_row(sheet, header_candidates=None)
                # self.assertEqual(expect_header_row, actual_header_row, f"{f.name}/{sheet_name}")
                if actual_header_row != expect_header_row:
                    print(f"{f.name}/{sheet_name}", expect_header_row, actual_header_row)



if __name__ == '__main__':
    unittest.main()