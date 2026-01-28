"""
最小化 Drive 上传测试
用最简单的文件和配置测试是否真的是配额问题
"""

from connection import get_credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

def minimal_upload_test():
    """
    使用最小化配置测试上传
    """
    print("=" * 60)
    print("🧪 最小化 Drive 上传测试")
    print("=" * 60)
    
    # 获取配置
    folder_id = input("\n请提供 Drive Folder ID: ").strip()
    if not folder_id:
        print("❌ 未提供 Folder ID")
        return
    
    try:
        # 认证
        print("\n[1] 认证...")
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        print(f"✅ Service Account: {credentials.service_account_email}")
        
        # 创建最小文件（只有几个字节）
        print("\n[2] 创建极简测试文件（5 字节）...")
        file_content = b"hello"
        file_stream = io.BytesIO(file_content)
        
        # 最简化的元数据
        file_metadata = {
            'name': 'test.txt',  # 最简单的文件名
            'parents': [folder_id]
        }
        
        # 最简化的上传
        print("\n[3] 上传文件...")
        print("配置:")
        print("  - 文件名: test.txt")
        print("  - 大小: 5 bytes")
        print("  - resumable: False")
        print("  - supportsAllDrives: True")
        
        media = MediaIoBaseUpload(
            file_stream,
            mimetype='text/plain',
            resumable=False  # 确认禁用断点续传
        )
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, name, size',
            supportsAllDrives=True,
            supportsTeamDrives=True
        ).execute()
        
        print("\n✅ 上传成功！")
        print(f"  File ID: {uploaded_file.get('id')}")
        print(f"  Name: {uploaded_file.get('name')}")
        print(f"  Size: {uploaded_file.get('size')} bytes")
        print(f"  Link: {uploaded_file.get('webViewLink')}")
        
    except Exception as e:
        print(f"\n❌ 上传失败:")
        print(f"  错误: {str(e)}")
        
        # 详细分析错误
        error_str = str(e)
        if 'storageQuotaExceeded' in error_str:
            print("\n💡 错误分析:")
            print("  ✓ 确认问题：Service Account 存储配额已满 (0GB)")
            print("  ✓ 即使是 5 字节的文件也无法上传")
            print("  ✓ 这不是代码问题，而是账户限制")
            print("\n📋 解决方案:")
            print("  1. 转移文件所有权给主账号（需要主账号邮箱）")
            print("  2. 使用其他有配额的 Service Account")
            print("  3. 清理 Service Account 的 Drive 空间")
        elif 'forbidden' in error_str.lower():
            print("\n💡 错误分析:")
            print("  ✓ 权限问题：文件夹未与 Service Account 共享")
            print(f"  ✓ 需要共享给: {credentials.service_account_email}")
        else:
            print("\n💡 其他错误，请检查详细信息")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    minimal_upload_test()
