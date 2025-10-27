import os
import unittest

from info_extract.source import EMLReader, MSGReader

class TestEmailReader(unittest.TestCase):
    def _clean_processing_dir(self):
        for root, dirs, files in os.walk('./processing', topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    os.rmdir(dir_path)
                except Exception:
                    pass

    def setUp(self) -> None:
        self._clean_processing_dir()
        self.eml_reader = EMLReader(source_dir='./source', processing_dir='./processing')
        self.msg_reader = MSGReader(source_dir='./source', processing_dir='./processing')
        return super().setUp()

    @unittest.skip("跳过EMLReader测试")
    def test_eml_reader(self):
        for _ in self.eml_reader.run():
            pass
        excel_files = []
        for root, _, files in os.walk('./processing'):
            for file in files:
                if file.lower().endswith('.xlsx') or file.lower().endswith('.xls'):
                    excel_files.append(os.path.join(root, file))
        assert len(excel_files) > 0, "未能正确提取Excel文件"
    
    def test_msg_reader(self):
        for _ in self.msg_reader.run():
            pass
        excel_files = []
        for root, _, files in os.walk('./processing'):
            for file in files:
                if file.lower().endswith('.xlsx') or file.lower().endswith('.xls'):
                    excel_files.append(os.path.join(root, file))
        assert len(excel_files) > 0, "未能正确提取Excel文件"
