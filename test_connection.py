"""
Google Services 连接测试脚本
测试 Google Sheets 写入和 Google Drive 上传功能
"""

import io
from datetime import datetime
from connection import get_credentials, save_to_sheets, load_data
from drive_handler import upload_to_drive

def test_google_connection():
    """
    执行完整的连接性测试
    """
    print("=" * 60)
    print("🚀 开始 Google Services 连接测试")
    print("=" * 60)
    
    # 测试 1: 认证测试
    print("\n[测试 1] Google 用户认证...")
    try:
        credentials = get_credentials()
        print("✅ 用户认证成功")
    except Exception as e:
        print(f"❌ 认证失败: {str(e)}")
        print("\n可能的原因:")
        print("  - client_secrets.json 文件不存在")
        print("  - OAuth 授权被拒绝")
        print("  - token.json 已损坏")
        return False
    
    # 测试 2: Google Sheets 写入测试
    print("\n[测试 2] Google Sheets 写入测试...")
    
    # 获取用户输入的 Spreadsheet ID
    print("\n请提供 Google Spreadsheet ID:")
    print("(可在 Google Sheets URL 中找到，格式: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit)")
    spreadsheet_id = input("Spreadsheet ID: ").strip()
    
    if not spreadsheet_id:
        print("❌ 未提供 Spreadsheet ID，跳过 Sheets 测试")
    else:
        try:
            test_data = {
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Column1': 'Test',
                'Column2': 'Connection',
                'Column3': 'Success'
            }
            save_to_sheets(test_data, spreadsheet_id)
            print("✅ Google Sheets 写入成功")
            
            # 尝试读取数据验证
            print("\n[测试 2.1] 验证数据读取...")
            df = load_data(spreadsheet_id)
            print(f"✅ 数据读取成功，共 {len(df)} 行")
            print("\n最新 3 行数据:")
            print(df.tail(3))
            
        except Exception as e:
            print(f"❌ Google Sheets 操作失败: {str(e)}")
            print("\n可能的原因:")
            print("  - Spreadsheet 未与 Service Account 共享")
            print("  - Spreadsheet ID 错误")
            print("  - Google Sheets API 未启用")
    
    # 测试 3: Google Drive 上传测试
    print("\n[测试 3] Google Drive 上传测试...")
    
    # 获取用户输入的 Drive Folder ID
    print("\n请提供 Google Drive 文件夹 ID:")
    print("(可在文件夹 URL 中找到，格式: https://drive.google.com/drive/folders/FOLDER_ID)")
    folder_id = input("Folder ID: ").strip()
    
    if not folder_id:
        print("❌ 未提供 Folder ID，跳过 Drive 测试")
    else:
        print("ℹ️ 使用 OAuth 用户凭证，文件将自动归属到您的账号")
        try:
            # 创建测试图片（纯色梯度）
            print("正在生成测试图片...")
            from PIL import Image, ImageDraw
            
            # 创建渐变图像
            width, height = 400, 300
            image = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(image)
            
            for y in range(height):
                # 从蓝色渐变到紫色
                r = int(100 + (155 * y / height))
                g = int(100 - (100 * y / height))
                b = int(255 - (100 * y / height))
                draw.line([(0, y), (width, y)], fill=(r, g, b))
            
            # 转换为 BytesIO
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            
            filename = f"test_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            link = upload_to_drive(img_bytes, folder_id, filename)
            
            print(f"✅ Google Drive 上传成功")
            print(f"   文件名: {filename}")
            print(f"   链接: {link}")
            
        except ImportError:
            print("⚠️ PIL/Pillow 未安装，使用文本文件测试...")
            try:
                # 创建简单的文本文件
                text_content = f"Test upload at {datetime.now()}\nConnection test successful!"
                text_bytes = io.BytesIO(text_content.encode('utf-8'))
                
                filename = f"test_file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                link = upload_to_drive(text_bytes, folder_id, filename)
                
                print(f"✅ Google Drive 上传成功")
                print(f"   文件名: {filename}")
                print(f"   链接: {link}")
                
            except Exception as e:
                print(f"❌ Google Drive 上传失败: {str(e)}")
                print("\n可能的原因:")
                print("  - Drive 文件夹未与 Service Account 共享（需要编辑者权限）")
                print("  - Folder ID 错误")
                print("  - Google Drive API 未启用")
        except Exception as e:
            print(f"❌ Google Drive 上传失败: {str(e)}")
            print("\n可能的原因:")
            print("  - Drive 文件夹未与 Service Account 共享（需要编辑者权限）")
            print("  - Folder ID 错误")
            print("  - Google Drive API 未启用")
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    test_google_connection()
