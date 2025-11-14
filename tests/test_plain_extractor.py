import textwrap
import unittest

import langextract as lx
from info_extract.extract.tokenizer import tokenize
import absl.logging as logging
from info_extract.extract.plain_extract import PlainExtractor

lx.core.tokenizer.tokenize = tokenize

logging.get_absl_logger().setLevel(logging.INFO)

class TestPlainExtractor(unittest.TestCase):
    def setUp(self) -> None:
        self.extractor = PlainExtractor(r"/data/home/macx/work/tmp/processing")
        self.content = textwrap.dedent(r"""
                    Hi Kris,
                    Please be informed that Zhengmao Sheng and Zhenyu (Joanna) Ma will complete their internship with us on 31 July, 2025.  Thank you.
                    Best regards,
                    Ivy
                    **Ivy Yang****杨静**
                    Mobile
                    手机: +86 13810049559 | E-mail
                    电子邮件:
                    [ivyyang@quinnemanuel.com](mailto:ivyyang@quinnemanuel.com)
                    **Quinn Emanuel Urquhart & Sullivan, LLP Beijing Office****美国昆鹰律师事务所驻北京代表处**
                    Central Park Plaza A1-1301, 10 Chaoyang Park South Road, Chaoyang District, Beijing |
                    北京市朝阳区朝阳公园南路10号骏豪中央公园广场A1-1301
                    *\*As an international law firm with representative offices in the PRC, we are not licensed to practice Chinese law.  Any information in the above email relating to the PRC is based on our general experience
                    as an international firm assisting clients in the PRC and does not constitute legal advice regarding the interpretation or application of PRC law.*
                    *作为国际律所的驻中国代表处，我们不能代理任何中国法业务。上述邮件任何涉及中国的内容仅基于我们作为国际律所协助在中国境内有商业活动的客户所积累的经验，不构成关于中国法解释或适用的法律意见。*
                    """)
        return super().setUp()

    # @unittest.skip("skip test_extract_one")
    def test_extract_one(self):
        doc = lx.data.Document(self.content,
                                document_id="test")
        result = self.extractor.fetch_all([doc])
        for extract_result in result:
            assert extract_result is not None, "extract_result must not be None"
            assert extract_result.data is not None, "data must not be None"
            print(extract_result.data)
    
    @unittest.skip("lang data")
    def test_extract_01(self):
        source = "./tests/DNCP.txt"
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
            doc = lx.data.Document(content,
                                   document_id="test")
            result = self.extractor.fetch_all([doc], debug=False)
            for extract_result in result:
                assert extract_result is not None, "extract_result must not be None"
       
