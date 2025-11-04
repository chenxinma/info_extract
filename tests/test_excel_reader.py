from typing import override
import unittest

from openpyxl import load_workbook
from info_extract.source import ExcelReader

class TestExcelReader(unittest.TestCase):
    @override
    def setUp(self) -> None:
        self.excel_reader = ExcelReader(source_dir=r"D:\tmp\work\source", processing_dir=r"D:\tmp\work\processing")
        return super().setUp()
        
    def test_fetch_row_colors(self):
        book = load_workbook(r"D:\tmp\work\source\工作簿1.xlsx")
        sheet = book["Sheet1"]

        colors = self.excel_reader.fetch_row_colors(sheet=sheet, header_row=1, row_count=21)
        print(colors)
    
    def test_fetch_row_colors2(self):
        book = load_workbook(r"D:\tmp\work\source\工作簿1.xls")
        sheet = book["Sheet1"]

        colors = self.excel_reader.fetch_row_colors(sheet=sheet, header_row=1, row_count=21)
        print(colors)
