import os
import unittest
from pathlib import Path

from info_extract.destination.excel_export import ExcelExporter


class TestExcelExporter(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        processing_dir = r"/data/home/macx/work/tmp/processing"
        destination_dir = r"/data/home/macx/work/tmp/destination"
        self.export = ExcelExporter(
            processing_dir=processing_dir,
            destination_dir=destination_dir
        )
        self.export.pre_results = [
            (str(f), []) for f in Path(processing_dir).glob("*.json")
        ]
    
    async def test_excel_export(self):
        # 运行导出
        async for output_path, row_count in self.export.run():
            self.assertTrue(os.path.exists(output_path))

if __name__ == "__main__":
    unittest.main()