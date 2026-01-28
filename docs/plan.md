# Laporan Web App - 架构计划

## 项目概述

这是一个基于 Streamlit 的报告提交系统，允许用户提交活动报告（含图片和可选的邀请信），数据存储在 Google Sheets，文件上传至 Google Drive。

---

## 文件结构

```
KK Laporan/
├── docs/
│   └── plan.md                    # 本架构文档
├── app.py                         # Streamlit 主应用程序
├── connection.py                  # Google Services 连接模块
├── test_connection.py             # 连接测试脚本
├── requirements.txt               # Python 依赖
├── .streamlit/
│   └── secrets.toml              # 云端部署密钥配置
├── service_account.json          # 本地测试用的 Google Service Account
└── .gitignore                    # Git 忽略配置
```

---

## 核心功能模块

### 1. **connection.py** - Google Services 集成

负责与 Google Sheets 和 Google Drive 的所有交互。

#### 功能清单：

| 功能 | 函数名 | 说明 |
|------|--------|------|
| 认证 | `get_credentials()` | 支持本地 JSON 和云端 secrets 双模式 |
| 上传文件 | `upload_to_drive(file, folder_id)` | 上传文件至指定 Drive 文件夹，返回可分享链接 |
| 保存数据 | `save_to_sheets(data_dict)` | 将一行数据追加到 Google Sheets |
| 加载数据 | `load_data()` | 从 Sheets 读取所有记录，返回 DataFrame |

#### 认证策略：

```python
def get_credentials():
    """
    优先级：
    1. 尝试读取 st.secrets (云端部署)
    2. 回退到 service_account.json (本地开发)
    """
    try:
        # 云端模式
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = service_account.Credentials.from_service_account_info(...)
    except:
        # 本地模式
        credentials = service_account.Credentials.from_service_account_file(
            'service_account.json', 
            scopes=[...]
        )
    return credentials
```

---

### 2. **app.py** - Streamlit 前端应用

#### 页面结构：

```
├── 主页配置 (st.set_page_config)
├── 侧边栏导航
│   ├── 📝 Laporan Pertandingan (报告提交)
│   └── 📊 Dashboard Admin (管理员仪表板)
└── 页面内容渲染
```

#### 2.1 Laporan Pertandingan 页面

**表单字段设计：**

| 字段名 | 类型 | 验证规则 | 说明 |
|--------|------|----------|------|
| Nama Pertandingan | `text_input` | 必填 | 竞赛名称 |
| Tarikh | `date_input` | 必填 | 日期 |
| Tempat | `text_input` | 必填 | 地点 |
| Nama Pelajar | `text_area` | 必填 | 学生名单（支持多行） |
| Pencapaian | `text_area` | 必填 | 成就描述 |
| **Gambar** | `file_uploader` | **2-4 张必填** | 活动照片 |
| **Surat Jemputan** | `file_uploader` | **可选** | 邀请信 PDF/图片 |

#### 2.2 文件上传逻辑处理

> [!IMPORTANT]
> **Gambar 上传限制的核心实现**

```python
# Gambar 上传器配置
gambar_files = st.file_uploader(
    "上传活动照片 (Gambar Aktiviti)",
    type=['jpg', 'jpeg', 'png'],
    accept_multiple_files=True,
    help="必须上传 2-4 张照片"
)

# 验证逻辑
if gambar_files:
    num_photos = len(gambar_files)
    if num_photos < 2:
        st.error("❌ 至少需要上传 2 张照片！")
        valid = False
    elif num_photos > 4:
        st.error("❌ 最多只能上传 4 张照片！")
        valid = False
    else:
        st.success(f"✅ 已选择 {num_photos} 张照片")
else:
    st.warning("⚠️ 请上传活动照片")
    valid = False
```

> [!WARNING]
> **Surat Jemputan 可选逻辑**

```python
# Surat Jemputan 上传器（可选）
surat_file = st.file_uploader(
    "上传邀请信 (Surat Jemputan) - 可选",
    type=['pdf', 'jpg', 'jpeg', 'png'],
    accept_multiple_files=False
)

# 处理逻辑
if surat_file:
    surat_link = upload_to_drive(surat_file, DRIVE_FOLDER_ID)
else:
    surat_link = ""  # 空字符串表示未上传
```

#### 2.3 提交流程图

```mermaid
graph TD
    A[用户填写表单] --> B{表单验证}
    B -->|验证失败| C[显示错误提示]
    B -->|验证通过| D{检查 Gambar 数量}
    D -->|< 2 张| E[错误: 至少 2 张]
    D -->|> 4 张| F[错误: 最多 4 张]
    D -->|2-4 张| G[上传 Gambar 至 Drive]
    G --> H{检查 Surat Jemputan}
    H -->|已上传| I[上传 Surat 至 Drive]
    H -->|未上传| J[跳过 Surat 上传]
    I --> K[准备数据字典]
    J --> K
    K --> L[保存至 Google Sheets]
    L --> M[显示成功消息]
```

---

## 数据流架构

### 数据流向图

```mermaid
graph LR
    A[用户浏览器] -->|提交表单| B[Streamlit App]
    B -->|上传文件| C[Google Drive API]
    C -->|返回链接| B
    B -->|保存记录| D[Google Sheets API]
    D -->|确认写入| B
    B -->|显示结果| A
    
    E[管理员] -->|查看数据| B
    B -->|读取记录| D
    D -->|返回 DataFrame| B
    B -->|渲染表格| E
```

### Google Sheets 数据结构

| 列名 | 数据类型 | 示例 | 说明 |
|------|----------|------|------|
| Timestamp | DateTime | `2026-01-09 14:30:00` | 自动生成 |
| Nama Pertandingan | String | `Pertandingan Pidato` | 竞赛名称 |
| Tarikh | Date | `2026-01-15` | 活动日期 |
| Tempat | String | `Dewan Sekolah` | 地点 |
| Nama Pelajar | Text | `Ahmad\nFatimah\nLee` | 学生名单 |
| Pencapaian | Text | `Juara Pertama` | 成就 |
| Gambar_1 | URL | `https://drive.google.com/...` | 第1张照片链接 |
| Gambar_2 | URL | `https://drive.google.com/...` | 第2张照片 |
| Gambar_3 | URL | `https://drive.google.com/...` | 第3张（可能为空） |
| Gambar_4 | URL | `https://drive.google.com/...` | 第4张（可能为空） |
| Surat_Jemputan | URL | `https://drive.google.com/...` | 邀请信（可能为空） |

> [!NOTE]
> **数据填充策略**
> - 如果只上传 2 张照片，`Gambar_3` 和 `Gambar_4` 填充空字符串 `""`
> - 如果未上传 `Surat_Jemputan`，该列填充空字符串 `""`
> - 这确保每行数据列数一致，便于 DataFrame 处理

---

## 关键业务逻辑

### 1. Gambar 上传限制 (2-4 张)

#### 实现细节：

```python
def validate_and_upload_photos(photo_files, drive_folder_id):
    """
    验证并上传照片
    
    Args:
        photo_files: Streamlit file_uploader 返回的文件列表
        drive_folder_id: Google Drive 目标文件夹 ID
    
    Returns:
        tuple: (success: bool, links: list, error_msg: str)
    """
    # 验证数量
    num_photos = len(photo_files)
    if num_photos < 2:
        return False, [], "必须上传至少 2 张照片"
    if num_photos > 4:
        return False, [], "最多只能上传 4 张照片"
    
    # 上传照片
    links = []
    for idx, photo in enumerate(photo_files, 1):
        try:
            link = upload_to_drive(photo, drive_folder_id)
            links.append(link)
        except Exception as e:
            return False, [], f"上传第 {idx} 张照片失败: {str(e)}"
    
    # 填充至 4 个元素（确保数据一致性）
    while len(links) < 4:
        links.append("")
    
    return True, links, ""
```

#### UI 反馈设计：

```python
# 实时照片计数显示
if gambar_files:
    count = len(gambar_files)
    if count < 2:
        st.error(f"❌ 已选 {count} 张，还需 {2 - count} 张")
    elif count > 4:
        st.error(f"❌ 已选 {count} 张，超过限制 {count - 4} 张")
    else:
        st.success(f"✅ 已选 {count} 张照片（符合要求）")
```

---

### 2. Surat Jemputan 可选逻辑

#### 实现策略：

```python
def handle_optional_surat(surat_file, drive_folder_id):
    """
    处理可选的邀请信上传
    
    Returns:
        str: 上传成功返回链接，未上传返回空字符串
    """
    if surat_file is None:
        st.info("ℹ️ 未上传邀请信（可选项）")
        return ""
    
    try:
        link = upload_to_drive(surat_file, drive_folder_id)
        st.success("✅ 邀请信上传成功")
        return link
    except Exception as e:
        st.error(f"❌ 邀请信上传失败: {str(e)}")
        return ""
```

#### 数据保存处理：

```python
# 准备数据字典
data = {
    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "Nama_Pertandingan": nama_pertandingan,
    "Tarikh": tarikh.strftime("%Y-%m-%d"),
    "Tempat": tempat,
    "Nama_Pelajar": nama_pelajar,
    "Pencapaian": pencapaian,
    "Gambar_1": photo_links[0],
    "Gambar_2": photo_links[1],
    "Gambar_3": photo_links[2],  # 可能为空
    "Gambar_4": photo_links[3],  # 可能为空
    "Surat_Jemputan": surat_link  # 可能为空
}

# 保存至 Sheets
save_to_sheets(data)
```

---

## 配置管理

### requirements.txt

```txt
streamlit>=1.28.0
google-auth>=2.23.0
google-auth-oauthlib>=1.1.0
google-auth-httplib2>=0.1.1
google-api-python-client>=2.100.0
gspread>=5.11.0
pandas>=2.1.0
```

### .streamlit/secrets.toml (云端部署)

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "xxx"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "xxx@xxx.iam.gserviceaccount.com"
client_id = "xxx"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/xxx"

[google_config]
spreadsheet_id = "your-spreadsheet-id"
drive_folder_id = "your-drive-folder-id"
```

---

## 错误处理策略

### 1. 文件上传失败

```python
try:
    link = upload_to_drive(file, folder_id)
except Exception as e:
    st.error(f"文件上传失败: {str(e)}")
    st.info("请检查网络连接和 Google Drive 权限")
    return
```

### 2. Sheets 写入失败

```python
try:
    save_to_sheets(data)
    st.success("✅ 报告提交成功！")
except Exception as e:
    st.error(f"数据保存失败: {str(e)}")
    st.warning("请联系管理员检查 Google Sheets 配置")
```

### 3. 认证失败

```python
try:
    creds = get_credentials()
except Exception as e:
    st.error("❌ Google 认证失败")
    st.code(str(e))
    st.stop()
```

---

## 测试计划

### test_connection.py 测试脚本

测试项目：
1. ✅ Google Service Account 认证
2. ✅ Google Sheets 连接和读写
3. ✅ Google Drive 文件上传
4. ✅ 返回可分享链接格式正确

### Browser Agent 测试清单

- [ ] Streamlit 应用正常启动
- [ ] 侧边栏导航正常切换
- [ ] 文件上传器显示正确
- [ ] 照片数量验证工作正常
- [ ] 表单提交流程无错误

---

## 安全注意事项

> [!CAUTION]
> **敏感文件保护**

确保 `.gitignore` 包含：
```
service_account.json
.streamlit/secrets.toml
*.pyc
__pycache__/
```

> [!IMPORTANT]
> **Google Drive 权限**
- Service Account 需要对目标文件夹具有「编辑者」权限
- Sheets 需要与 Service Account 共享「编辑」权限

---

## 部署流程

### 本地开发
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 放置 service_account.json 到根目录

# 3. 运行测试
python test_connection.py

# 4. 启动应用
streamlit run app.py
```

### 云端部署 (Streamlit Cloud)
```bash
# 1. 推送代码至 GitHub（不包含 service_account.json）
git push origin main

# 2. 在 Streamlit Cloud 配置 secrets
# 复制 service_account.json 内容到 secrets.toml

# 3. 部署完成自动运行
```

---

## 总结

本架构设计的核心特点：

1. **灵活的认证机制**：支持本地和云端双环境
2. **严格的文件验证**：Gambar 必须 2-4 张，逻辑清晰
3. **可选字段处理**：Surat Jemputan 优雅地处理空值
4. **数据一致性**：固定列数，空值用 `""` 占位
5. **完善的错误处理**：每个关键步骤都有异常捕获

下一步等待您确认本计划后，将创建 `test_connection.py` 并使用 Browser Agent 验证系统正常运行。
