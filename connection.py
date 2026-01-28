"""
Google Services Connection Module
Handles interactions with Google Sheets and Google Drive using Service Account.
Supports Dual-Mode Authentication: Streamlit Cloud (st.secrets) & Local (JSON file).
"""

import streamlit as st
import json
import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Google API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_credentials():
    """
    Get Google OAuth 2.0 Credentials (Service Account).
    
    Logic:
    1. Cloud Mode: Check st.secrets["gcp_service_account"]
    2. Local Mode: Check client_secrets.json or service_account.json
    3. Error: Raise FileNotFoundError if neither exists
    """
    creds = None
    
    # 1. Cloud Mode: Streamlit Secrets
    if "gcp_service_account" in st.secrets:
        try:
            # Create a dict from the secrets object
            service_account_info = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(
                service_account_info, 
                scopes=SCOPES
            )
            print("✅ Loaded credentials from st.secrets (Cloud Mode)")
            return creds
        except Exception as e:
            print(f"⚠️ Error loading from st.secrets: {e}")
    
    # 2. Local Mode: JSON File Fallback
    # Check common filenames
    json_files = ['client_secrets.json', 'service_account.json', 'credentials.json']
    for filename in json_files:
        if os.path.exists(filename):
            try:
                creds = Credentials.from_service_account_file(
                    filename, 
                    scopes=SCOPES
                )
                print(f"✅ Loaded credentials from local file: {filename}")
                return creds
            except Exception as e:
                print(f"⚠️ Error loading {filename}: {e}")

    # 3. Critical Error
    raise FileNotFoundError(
        "❌ Unable to find valid credentials!\n"
        "1. Cloud: Ensure 'gcp_service_account' is in .streamlit/secrets.toml\n"
        "2. Local: Ensure 'client_secrets.json' or 'service_account.json' exists."
    )

def get_config():
    """
    Get configuration (Spreadsheet ID, Drive Folder ID, Admin Password).
    """
    try:
        # Priority: [connections] section
        if "connections" in st.secrets:
            secrets = st.secrets["connections"]
            return {
                'spreadsheet_id': secrets.get('google_sheet_id'),
                'drive_folder_id': secrets.get('google_drive_folder_id'),
                'admin_password': secrets.get('admin_password', 'admin123')
            }
        # Backward Compatibility: [google_config]
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
        # Local dev fallback if secrets missing completely
        return {
            'spreadsheet_id': None,
            'drive_folder_id': None,
            'admin_password': None
        }

# ==============================================================================
# WRAPPER FUNCTIONS (Using new get_credentials)
# ==============================================================================

def save_to_sheets(data_dict, spreadsheet_id=None):
    """Save data to Google Sheets."""
    try:
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            if not spreadsheet_id:
                raise ValueError("Missing spreadsheet_id")
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        # Prepare headers if empty
        headers = worksheet.row_values(1)
        if not headers:
            headers = list(data_dict.keys())
            worksheet.append_row(headers)
        
        # Align data with headers
        row_data = [data_dict.get(h, '') for h in headers]
        
        worksheet.append_row(row_data)
        print("✅ Data saved successfully")
        
    except Exception as e:
        print(f"❌ Save failed: {str(e)}")
        raise Exception(f"Sheets Write Error: {str(e)}")

def load_data(spreadsheet_id=None):
    """Load all data as DataFrame."""
    try:
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            if not spreadsheet_id:
                raise ValueError("Missing spreadsheet_id")
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        records = worksheet.get_all_records()
        df = pd.DataFrame(records)
        
        print(f"✅ Data loaded: {len(df)} rows")
        return df
        
    except Exception as e:
        print(f"❌ Load failed: {str(e)}")
        raise Exception(f"Sheets Read Error: {str(e)}")

def append_data_to_sheet(data_row, spreadsheet_id=None):
    """Append a raw list as a row."""
    try:
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        worksheet.append_row(data_row)
        print(f"✅ Row appended: {data_row}")
        return True
        
    except Exception as e:
        print(f"❌ Append failed: {str(e)}")
        raise Exception(f"Sheets Append Error: {str(e)}")

def read_all_data(spreadsheet_id=None):
    """Alias for load_data logic but returns DataFrame."""
    return load_data(spreadsheet_id)

def update_sheet(dataframe, spreadsheet_id=None):
    """Update entire sheet with DataFrame content."""
    try:
        if spreadsheet_id is None:
            config = get_config()
            spreadsheet_id = config['spreadsheet_id']
            
        credentials = get_credentials()
        gc = gspread.authorize(credentials)
        
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.sheet1
        
        # Prepare data: Header + Rows
        data = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
        
        worksheet.clear()
        worksheet.update(data)
        print("✅ Sheet updated successfully")
        return True
    except Exception as e:
        print(f"❌ Update failed: {str(e)}")
        raise Exception(f"Sheet Update Error: {str(e)}")

if __name__ == "__main__":
    print("Connection module loaded.")

