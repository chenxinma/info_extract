"""
Excel工具函数，提供Excel转PNG等实用功能
"""

import os
import logging
import pythoncom
import win32com.client
from PIL import Image
import tempfile


logger = logging.getLogger(__name__)


def excel_to_png_via_com(
    excel_file_path, output_png_path, sheet_name=None, width=0, height=0
):
    """
    使用COM组件将Excel转换为PNG图片

    Args:
        excel_file_path (str): Excel文件路径
        output_png_path (str): 输出PNG图片路径
        sheet_name (str, optional): 指定工作表名称，默认为第一个工作表
        width (int, optional): 输出图片宽度，默认自适应
        height (int, optional): 输出图片高度，默认自适应
    """
    import win32clipboard
    import io

    excel_app = None
    temp_image_path = None
    try:
        # 初始化COM库
        pythoncom.CoInitialize()

        # 启动Excel应用
        excel_app = win32com.client.Dispatch("Excel.Application")
        excel_app.Visible = False
        excel_app.DisplayAlerts = False

        # 打开工作簿
        workbook = excel_app.Workbooks.Open(os.path.abspath(excel_file_path))

        # 选择工作表
        if sheet_name:
            worksheet = workbook.Worksheets(sheet_name)
        else:
            worksheet = workbook.ActiveSheet

        # 选择整个数据范围
        used_range = worksheet.UsedRange
        used_range.CopyPicture(Appearance=1, Format=2)  # xlScreen, xlBitmap

        # 从剪贴板获取图像数据
        win32clipboard.OpenClipboard()
        try:
            # 获取剪贴板中的DIB格式图像
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                # 获取DIB数据
                dib_data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)

                # 生成临时文件路径
                temp_dir = tempfile.gettempdir()
                temp_image_path = os.path.join(
                    temp_dir, f"temp_{os.path.basename(output_png_path)}.bmp"
                )

                # 将DIB数据写入临时BMP文件
                with open(temp_image_path, "wb") as f:
                    # BMP文件头
                    f.write(b"BM")  # 文件标识符
                    f.write(
                        (len(dib_data) + 54).to_bytes(4, byteorder="little")
                    )  # 文件大小
                    f.write(b"\x00\x00\x00\x00")  # 保留字段
                    f.write((54).to_bytes(4, byteorder="little"))  # 偏移量到图像数据
                    # 写入DIB数据
                    f.write(dib_data)

                # 使用PIL调整图片尺寸（如果指定了宽高）
                if width > 0 or height > 0:
                    img = Image.open(temp_image_path)
                    original_width, original_height = img.size

                    if width > 0 and height > 0:
                        new_size = (width, height)
                    elif width > 0:
                        # 按比例调整高度
                        ratio = width / original_width
                        new_size = (width, int(original_height * ratio))
                    else:  # height > 0 且 width == 0
                        # 按比例调整宽度
                        ratio = height / original_height
                        new_size = (int(original_width * ratio), height)

                    resized_img = img.resize(new_size, Image.Resampling.LANCZOS)
                    resized_img.save(output_png_path, "PNG")
                else:
                    # 直接将BMP转换为PNG
                    img = Image.open(temp_image_path)
                    img.save(output_png_path, "PNG")
            else:
                raise RuntimeError("未能从剪贴板获取图像数据")
        finally:
            win32clipboard.CloseClipboard()

        workbook.Close(SaveChanges=False)
        logger.info(f"成功将{excel_file_path}转换为{output_png_path}")

    except Exception as e:
        logger.error(f"Excel转PNG过程中发生错误: {str(e)}")
        raise
    finally:
        # 清理资源
        if excel_app:
            excel_app.Quit()
            excel_app = None

        # 删除临时文件
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except:
                pass  # 忽略删除临时文件的错误

        # 反初始化COM库
        try:
            pythoncom.CoUninitialize()
        except:
            pass  # 如果已经反初始化，则忽略错误
