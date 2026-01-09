"""
Google Services Connection Module
处理 Google Sheets 和 Google Drive 的所有交互
"""

import os
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread
import pandas as pd

# Google API Scopes
# 注意：使用完整的 drive 权限而非 drive.file 以避免配额死锁
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'  # 完整 Drive 权限
]

def get_credentials():
    """
    获取 Google OAuth 2.0 用户凭证
    使用主账号的配额，避免 Service Account 的 0GB 限制
    
    认证流程：
    1. 检查是否存在 token.json（已保存的凭证）
    2. 如果凭证过期，自动刷新
    3. 如果没有凭证，启动浏览器让用户授权
    4. 保存凭证到 token.json 供下次使用
    """
    creds = None
    
    # 如果已有 token.json，直接加载
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("✅ 使用已保存的用户凭证 (token.json)")
    
    # 如果没有有效凭据，则让用户登录
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 刷新过期的凭证...")
            creds.refresh(Request())
            print("✅ 凭证刷新成功")
        else:
            # 使用下载的 client_secrets.json 发起流程
            if not os.path.exists('client_secrets.json'):
                raise FileNotFoundError(
                    "未找到 client_secrets.json 文件！\n"
                    "请从 Google Cloud Console 下载 OAuth 2.0 客户端密钥\n"
                    "https://console.cloud.google.com/apis/credentials"
                )
            
            print("🌐 启动 OAuth 2.0 授权流程...")
            print("   浏览器将自动打开，请登录您的 Google 账号并授权")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets.json', SCOPES)
            creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')
            
            print("✅ 授权成功！")
            
        # 保存凭据供下次使用
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("💾 凭证已保存到 token.json")
            
    return creds

def get_config():
    """
    获取配置信息（Spreadsheet ID, Drive Folder ID, Admin Password）
    """
    try:
        import streamlit as st
        # 优先读取 [connections] 部分
        if "connections" in st.secrets:
            secrets = st.secrets["connections"]
            return {
                'spreadsheet_id': secrets.get('google_sheet_id'),
                'drive_folder_id': secrets.get('google_drive_folder_id'),
                'admin_password': secrets.get('admin_password', 'admin123')
            }
        # 兼容旧配置 [google_config]
        elif "google_config" in st.secrets:
            return {
                'spreadsheet_id': st.secrets['google_config']['spreadsheet_id'],
                'drive_folder_id': st.secrets['google_config']['drive_folder_id'],
                'admin_password': 'admin123'
            }
        return {
            'spreadsheet_id': None,
            'drive_folder_id': None,
            'admin_password': None
        }
    except:
        # 本地开发模式返回空配置
        return {
            'spreadsheet_id': None,
            'drive_folder_id': None,
            'admin_password': None
        }


def save_to_sheets(data_dict, spreadsheet_id=None):
    """
    保存数据到 Google Sheets
    
    Args:
        data_dict: 数据字典，键为列名
        spreadsheet_id: Spreadsheet ID（可选，不提供则从配置读取）
    """
    try:
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        # 获取 spreadsheet ID
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            if spreadsheet_id is None:
                raise ValueError("未配置 spreadsheet_id")
        
        # 打开工作表
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        # 准备行数据（按列顺序）
        headers = worksheet.row_values(1)
        if not headers:
            # 如果没有表头，使用数据字典的键作为表头
            headers = list(data_dict.keys())
            worksheet.append_row(headers)
        
        # 按表头顺序准备数据
        row_data = [data_dict.get(header, '') for header in headers]
        
        # 追加行
        worksheet.append_row(row_data)
        print("✅ 数据保存成功")
        
    except Exception as e:
        print(f"❌ 保存数据失败: {str(e)}")
        raise Exception(f"Sheets 写入失败: {str(e)}")

def load_data(spreadsheet_id=None):
    """
    从 Google Sheets 加载所有数据
    
    Args:
        spreadsheet_id: Spreadsheet ID（可选）
    
    Returns:
        pd.DataFrame: 数据框架
    """
    try:
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        # 获取 spreadsheet ID
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            if spreadsheet_id is None:
                raise ValueError("未配置 spreadsheet_id")
        
        # 打开工作表
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        # 获取所有记录
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        print(f"✅ 加载数据成功: {len(df)} 行")
        return df
        
    except Exception as e:
        print(f"❌ 加载数据失败: {str(e)}")
        raise Exception(f"Sheets 读取失败: {str(e)}")

def append_data_to_sheet(data_row, spreadsheet_id=None):
    """
    向 Google Sheets 追加一行数据
    
    Args:
        data_row: 数据列表 (List)
        spreadsheet_id: 可选，指定表格 ID
    """
    try:
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        # 打开工作表
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        # 追加数据
        worksheet.append_row(data_row)
        print(f"✅ 数据写入成功: {data_row}")
        return True
        
    except Exception as e:
        print(f"❌ 数据写入失败: {str(e)}")
        raise Exception(f"Sheets 写入失败: {str(e)}")

def read_all_data(spreadsheet_id=None):
    """
    读取所有数据并返回 DataFrame
    """
    try:
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        print(f"❌ 读取数据失败: {str(e)}")
        raise Exception(f"读取失败: {str(e)}")

def update_sheet(dataframe, spreadsheet_id=None):
    """
    更新整个工作表（保留表头）
    """
    try:
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        # 准备数据：表头 + 内容
        data = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
        
        # 清空并更新
        worksheet.clear()
        worksheet.update(data)
        print("✅ 数据更新成功")
        return True
    except Exception as e:
        print(f"❌ 更新数据失败: {str(e)}")
        raise Exception(f"更新失败: {str(e)}")

if __name__ == "__main__":
    print("Connection module loaded successfully!")
    print(f"Scopes: {SCOPES}")
