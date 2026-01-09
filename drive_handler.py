"""
Google Drive Handler Module
负责处理所有 Google Drive 相关的 API 操作
"""

import io
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from connection import get_credentials

def upload_to_drive(file, folder_id, filename=None):
    """
    上传文件到 Google Drive
    
    Args:
        file: 文件对象（可以是 Streamlit UploadedFile 或 BytesIO）
        folder_id: 目标文件夹 ID
        filename: 可选的文件名（如果 file 没有 name 属性）
    
    Returns:
        str: 可分享的文件链接
    """
    try:
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        # 获取文件名
        if filename is None:
            filename = getattr(file, 'name', f'upload_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        
        # 准备文件内容
        if hasattr(file, 'read'):
            file_content = file.read()
            if hasattr(file, 'seek'):
                file.seek(0)  # 重置文件指针
        else:
            file_content = file
        
        file_stream = io.BytesIO(file_content)
        
        # 文件元数据
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        # 上传文件（小文件使用非断点续传模式更稳定）
        media = MediaIoBaseUpload(
            file_stream,
            mimetype='application/octet-stream',
            resumable=False
        )
        
        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink',
            supportsAllDrives=True,
            supportsTeamDrives=True  # 旧版兼容性，对 Service Account 依然有效
        ).execute()
        
        # 设置文件为公开可访问
        try:
            service.permissions().create(
                fileId=uploaded_file['id'],
                body={'type': 'anyone', 'role': 'reader'},
                supportsAllDrives=True
            ).execute()
            print(f"✅ 文件已设为公开访问")
        except Exception as e:
            print(f"⚠️ 设置公开访问失败: {str(e)}")
        
        link = uploaded_file.get('webViewLink')
        print(f"✅ 文件上传成功: {filename}")
        return link
        
    except Exception as e:
        print(f"❌ 上传文件失败: {str(e)}")
        raise Exception(f"Drive 上传失败: {str(e)}")

def create_folder(folder_name, parent_id):
    """
    在指定父文件夹下创建新文件夹
    
    Args:
        folder_name: 新文件夹名称
        parent_id: 父文件夹 ID
        
    Returns:
        str: 新文件夹的 ID
    """
    try:
        credentials = get_credentials()
        service = build('drive', 'v3', credentials=credentials)
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        
        folder = service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True,
            supportsTeamDrives=True
        ).execute()
        
        folder_id = folder.get('id')
        print(f"✅ 文件夹创建成功: {folder_name} (ID: {folder_id})")
        return folder_id
        
    except Exception as e:
        print(f"❌ 创建文件夹失败: {str(e)}")
        raise Exception(f"Drive 创建文件夹失败: {str(e)}")
