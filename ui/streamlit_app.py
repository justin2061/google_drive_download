"""
Streamlit Web 管理介面
提供直觀的圖形化下載管理介面
"""

import streamlit as st
import asyncio
import time
from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 添加專案根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

from src.core.auth import AuthManager
from src.core.downloader import download_manager, DownloadStatus
from src.core.file_handler import file_handler
from src.core.progress import progress_manager
from src.utils.config import get_config, load_config
from src.utils.logger import setup_logging, get_logger
from src.utils.helpers import extract_file_id_from_url, format_bytes, format_duration
from src.utils.oauth_setup import oauth_setup_manager


# 設定頁面配置
st.set_page_config(
    page_title="Google Drive 下載工具",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 設定日誌
setup_logging()
logger = get_logger(__name__)


# 使用 session_state 來確保 AuthManager 只被初始化一次
def get_auth_manager():
    """獲取 AuthManager 的單例"""
    if 'auth_manager' not in st.session_state:
        logger.info("在 session_state 中初始化 AuthManager")
        st.session_state.auth_manager = AuthManager()
    return st.session_state.auth_manager

auth_manager = get_auth_manager() # 全域獲取一次


def init_session_state():
    """初始化 session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True


def check_authentication():
    """檢查認證狀態（不進行自動認證）"""
    try:
        # 只檢查現有認證狀態，不嘗試新的認證
        if auth_manager.is_authenticated():
            if not st.session_state.authenticated:
                st.session_state.authenticated = True
                st.session_state.user_info = auth_manager.get_user_info()
            return True
        else:
            st.session_state.authenticated = False
            st.session_state.user_info = None
            return False
    except Exception as e:
        logger.error(f"檢查認證失敗: {e}")
        st.session_state.authenticated = False
        st.session_state.user_info = None
        return False


def authentication_page():
    """認證頁面"""
    st.title("🔐 Google Drive 認證")
    
    st.markdown("""
    ### 歡迎使用 Google Drive 下載工具
    
    請先完成 Google Drive 認證以開始使用下載功能。
    """)
    
    # ADC 自動認證說明
    with st.container():
        st.subheader("⚡ 自動認證 (ADC)")
        
        st.markdown("""
        **Application Default Credentials (ADC)** 會自動檢查以下認證來源：
        
        1. 🔑 **GOOGLE_APPLICATION_CREDENTIALS** 環境變數（服務帳戶）
        2. 🔧 **gcloud CLI** 使用者認證
        3. ☁️ **Google Cloud** 環境中繼資料服務
        
        如果您已設定任何一種，無需手動認證！
        """)
        
        # ADC 狀態檢查按鈕
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔍 檢查 ADC 狀態", use_container_width=True):
                with st.spinner("檢查 ADC 認證來源..."):
                    # 嘗試 ADC 認證（不強制刷新）
                    success = auth_manager.authenticate()
                    if success:
                        st.success("🎉 ADC 認證成功！自動跳轉到主頁面...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.info("ℹ️ 沒有找到 ADC 認證，請使用下方的手動認證")
        
        with col2:
            if st.button("📖 ADC 設定指南", use_container_width=True):
                st.session_state.show_adc_guide = not st.session_state.get('show_adc_guide', False)
        
        # ADC 設定指南
        if st.session_state.get('show_adc_guide', False):
            with st.expander("📖 ADC 詳細設定指南", expanded=True):
                st.markdown("""
                ### 🔸 方法 1: 個人開發（推薦用於開發測試）
                
                ```bash
                # 1. 安裝 Google Cloud SDK
                # https://cloud.google.com/sdk/docs/install
                
                # 2. 初始化並登入
                gcloud init
                gcloud auth application-default login
                
                # 3. 確認設定
                gcloud auth application-default print-access-token
                ```
                
                ### 🔸 方法 2: 服務帳戶（推薦用於生產環境）
                
                1. 在 Google Cloud Console 中建立服務帳戶
                2. 下載 JSON 金鑰檔案
                3. 設定環境變數：
                
                ```bash
                # Windows
                set GOOGLE_APPLICATION_CREDENTIALS=C:\\path\\to\\service-account.json
                
                # Linux/Mac
                export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
                ```
                
                ### 🔸 方法 3: Google Cloud 環境
                在 Google Cloud Platform (GCE, GKE, Cloud Run 等) 上運行時自動可用。
                
                ### ✨ 優點
                - ✅ **零配置**: 環境設定好後完全自動
                - ✅ **多環境支援**: 從開發到生產無縫切換  
                - ✅ **安全性高**: 不需要在程式碼中存放認證
                """)
        
        st.markdown("---")
    
    # 手動認證設定區域
    with st.container():
        st.subheader("🔧 手動 OAuth 認證")
        
        # Google OAuth 應用程式設定
        with st.expander("⚙️ Google OAuth 應用程式設定", expanded=False):
            st.markdown("""
            **設定您的 Google OAuth 應用程式**
            
            這些設定會影響 Google 認證頁面上顯示的開發人員資訊。
            如果您有自己的 Google Cloud 專案，請填入相關資訊。
            """)
            
            # OAuth 憑證設定
            st.subheader("🔑 OAuth 憑證")
            
            col_oauth1, col_oauth2 = st.columns([2, 1])
            
            with col_oauth1:
                client_id = st.text_input(
                    "Client ID",
                    value=st.session_state.get('oauth_client_id', ''),
                    placeholder="your-client-id.apps.googleusercontent.com",
                    help="從 Google Cloud Console 取得的 OAuth Client ID",
                    key="oauth_client_id_input",
                    type="password"
                )
                
                client_secret = st.text_input(
                    "Client Secret",
                    value=st.session_state.get('oauth_client_secret', ''),
                    placeholder="your-client-secret",
                    help="從 Google Cloud Console 取得的 OAuth Client Secret",
                    key="oauth_client_secret_input",
                    type="password"
                )
            
            with col_oauth2:
                st.markdown("<br>", unsafe_allow_html=True)
                validate_oauth = st.button("✅ 驗證憑證", help="驗證 OAuth 憑證格式")
                
                if validate_oauth and client_id and client_secret:
                    if oauth_setup_manager.validate_oauth_config(client_id, client_secret):
                        st.success("✅ OAuth 憑證格式正確")
                        st.session_state.oauth_client_id = client_id
                        st.session_state.oauth_client_secret = client_secret
                    else:
                        st.error("❌ OAuth 憑證格式不正確")
            
            # 開發人員資訊設定
            st.subheader("👨‍💻 開發人員資訊")
            
            col_dev1, col_dev2 = st.columns([2, 1])
            
            with col_dev1:
                developer_email = st.text_input(
                    "開發人員 Email",
                    value=st.session_state.get('developer_email', 'your.dev.email@gmail.com'),
                    placeholder="developer@yourcompany.com",
                    help="會在 Google 認證頁面顯示的開發人員聯絡信箱",
                    key="developer_email_input"
                )
                
                app_name = st.text_input(
                    "應用程式名稱",
                    value=st.session_state.get('app_name', 'Google Drive 下載工具'),
                    placeholder="您的應用程式名稱",
                    help="會在 Google 認證頁面顯示的應用程式名稱",
                    key="app_name_input"
                )
            
            with col_dev2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 儲存應用設定", help="儲存開發人員和應用程式資訊"):
                    st.session_state.developer_email = developer_email
                    st.session_state.app_name = app_name
                    st.success("✅ 應用程式設定已儲存")
                    
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 重設為預設值"):
                    st.session_state.developer_email = 'your.dev.email@gmail.com'
                    st.session_state.app_name = 'Google Drive 下載工具'
                    st.rerun()
            
            # 生成 credentials.json
            st.subheader("📄 生成 Credentials 檔案")
            
            has_oauth_config = (
                hasattr(st.session_state, 'oauth_client_id') and 
                hasattr(st.session_state, 'oauth_client_secret') and
                st.session_state.oauth_client_id and 
                st.session_state.oauth_client_secret
            )
            
            col_gen1, col_gen2 = st.columns([2, 1])
            
            with col_gen1:
                if has_oauth_config:
                    st.success("✅ OAuth 憑證已設定")
                    dev_email = st.session_state.get('developer_email', 'your.dev.email@gmail.com')
                    app_name = st.session_state.get('app_name', 'Google Drive 下載工具')
                    st.info(f"開發人員: {dev_email}")
                    st.info(f"應用程式: {app_name}")
                else:
                    st.warning("⚠️ 請先設定並驗證 OAuth 憑證")
            
            with col_gen2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(
                    "🔧 生成 Credentials",
                    disabled=not has_oauth_config,
                    help="生成 credentials.json 檔案用於認證" if has_oauth_config else "請先設定 OAuth 憑證"
                ):
                    success = oauth_setup_manager.save_credentials_file(
                        client_id=st.session_state.oauth_client_id,
                        client_secret=st.session_state.oauth_client_secret,
                        developer_email=st.session_state.developer_email,
                        app_name=st.session_state.app_name
                    )
                    
                    if success:
                        st.success("🎉 Credentials 檔案已生成！")
                        st.info("現在可以使用自訂的開發人員資訊進行認證")
                    else:
                        st.error("❌ 生成 Credentials 檔案失敗")
            
        
        # OAuth 設定說明（移到 expander 外面）
        st.markdown("---")
        st.markdown("### 📖 如何取得 OAuth 憑證")
        with st.container():
            st.markdown(oauth_setup_manager.create_sample_credentials())
        
        st.markdown("---")
        
        # 使用者認證設定
        st.subheader("👤 使用者認證")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            user_email = st.text_input(
                "請輸入您的 Google 帳戶 Email",
                placeholder="your.email@gmail.com",
                help="輸入您要用於認證的 Google 帳戶 Email 地址",
                key="auth_email"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # 對齊
            validate_email = st.button("✅ 驗證", help="驗證 Email 格式")
        
        # Email 格式驗證
        if validate_email or user_email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if user_email and re.match(email_pattern, user_email):
                st.success(f"✅ Email 格式正確: {user_email}")
                st.session_state.validated_email = user_email
            elif user_email:
                st.error("❌ Email 格式不正確，請重新輸入")
                st.session_state.validated_email = None
    
    # 安全性說明
    st.warning("""
    **⚠️ 安全性提醒：**
    
    當您點擊"開始認證"後，Google 可能會顯示安全警告，提示此應用尚未通過 Google 驗證。
    這是正常的，因為這是測試/開發版本。
    
    **在測試環境中安全操作步驟：**
    1. 點擊 "Advanced"（進階）
    2. 點擊 "Go to Google Drive 下載工具 (unsafe)"（前往應用程式）
    3. 授權必要的權限（僅讀取權限）
    4. **請確保選擇上方輸入的 Email 帳戶進行授權**
    
    **我們承諾：**
    - ✅ 僅請求 Google Drive 讀取權限
    - ✅ 不會修改、刪除或上傳任何檔案
    - ✅ 不會儲存您的個人資訊
    - ✅ 本地處理，資料不會傳送到外部伺服器
    """)
    
    # 檢查是否有驗證過的 Email
    has_valid_email = hasattr(st.session_state, 'validated_email') and st.session_state.validated_email
    
    # 認證按鈕區域
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button(
            "⚡ 智能認證",
            type="primary", 
            use_container_width=True,
            disabled=not has_valid_email,
            help="先嘗試 ADC 自動認證，失敗時使用 OAuth" if has_valid_email else "請先輸入並驗證 Email 地址"
        ):
            try:
                with st.spinner(f"正在為 {st.session_state.validated_email} 執行智能認證..."):
                    # 先嘗試 ADC，不強制刷新
                    success = auth_manager.authenticate(force_refresh=False)
                
                if success:
                    # 驗證認證的帳戶是否匹配
                    user_info = auth_manager.get_user_info()
                    actual_email = user_info.get('email', '')
                    auth_method = auth_manager._current_auth_method or "unknown"
                    
                    if actual_email.lower() == st.session_state.validated_email.lower():
                        st.success(f"✅ 認證成功！歡迎 {actual_email} (使用 {auth_method.upper()})")
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_info
                        st.rerun()
                    else:
                        st.warning(f"⚠️ 您使用了不同的帳戶進行認證（{actual_email}）。如果這是您想要的帳戶，請點擊確認。")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ 確認使用此帳戶", type="primary", key="confirm_smart"):
                                st.session_state.authenticated = True
                                st.session_state.user_info = user_info
                                st.session_state.validated_email = actual_email
                                st.rerun()
                        with col_b:
                            if st.button("🔄 重新認證", key="retry_smart"):
                                auth_manager.logout()
                                st.rerun()
                else:
                    st.error("❌ 智能認證失敗，請嘗試強制 OAuth 認證")
                    
            except Exception as e:
                st.error(f"❌ 智能認證過程發生錯誤: {e}")
    
    with col2:
        if st.button(
            "🔧 強制 OAuth",
            use_container_width=True,
            disabled=not has_valid_email,
            help="強制使用 OAuth 流程認證" if has_valid_email else "請先輸入並驗證 Email 地址"
        ):
            try:
                with st.spinner(f"正在為 {st.session_state.validated_email} 執行 OAuth 認證..."):
                    # 強制使用 OAuth
                    success = auth_manager.authenticate(force_refresh=True)
                
                if success:
                    # 驗證認證的帳戶是否匹配
                    user_info = auth_manager.get_user_info()
                    actual_email = user_info.get('email', '')
                    
                    if actual_email.lower() == st.session_state.validated_email.lower():
                        st.success(f"✅ OAuth 認證成功！歡迎 {actual_email}")
                        st.session_state.authenticated = True
                        st.session_state.user_info = user_info
                        st.rerun()
                    else:
                        st.warning(f"⚠️ 您使用了不同的帳戶進行認證（{actual_email}）。如果這是您想要的帳戶，請點擊確認。")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ 確認使用此帳戶", type="primary", key="confirm_oauth"):
                                st.session_state.authenticated = True
                                st.session_state.user_info = user_info
                                st.session_state.validated_email = actual_email
                                st.rerun()
                        with col_b:
                            if st.button("🔄 重新認證", key="retry_oauth"):
                                auth_manager.logout()
                                st.rerun()
                else:
                    st.error("❌ OAuth 認證失敗，請檢查 credentials.json 檔案")
                    
            except Exception as e:
                st.error(f"❌ OAuth 認證過程發生錯誤: {e}")
    
    with col3:
        st.markdown("") # 空白列
    
    # 顯示認證提示
    if not has_valid_email:
        st.info("💡 請先輸入您的 Google 帳戶 Email 地址")
    else:
        st.info(f"ℹ️ 準備為 {st.session_state.validated_email} 認證")
    
    # 認證說明
    with st.expander("ℹ️ 詳細認證說明"):
        st.markdown("""
        ### 📋 認證流程步驟
        
        #### ⚡ 智能認證（推薦）
        1. **點擊「智能認證」按鈕**
        2. **系統自動檢查 ADC 認證來源**
        3. **如果 ADC 可用，立即完成認證**
        4. **如果 ADC 不可用，自動使用 OAuth 流程**
        
        #### 🔧 強制 OAuth 認證
        1. **點擊「強制 OAuth」按鈕**
        2. **瀏覽器自動開啟 Google 認證頁面**
        3. **如果出現安全警告：**
           - 點擊 "Advanced"（進階）
           - 點擊 "Go to Google Drive 下載工具 (unsafe)"
           - 這是正常的測試環境行為
        4. **選擇您的 Google 帳戶**
        5. **授權讀取權限**
        6. **完成後返回此頁面**
        
        ### 🔒 權限說明
        
        本應用僅請求以下權限：
        - **Google Drive 檔案讀取權限**：用於下載您指定的檔案
        - **基本個人資料**：顯示您的姓名和 email
        
        ### 🛡️ 隱私保護
        
        - 所有處理都在您的本地電腦進行
        - 不會將檔案或個人資訊傳送到外部伺服器
        - 認證令牌安全儲存在本地
        - 您可以隨時撤銷授權
        
                 ### 👨‍💻 開發人員資訊
         
         - **開發者：** 可在上方設定區域自訂
         - **應用類型：** 測試/開發版本  
         - **用途：** Google Drive 檔案下載工具
         - **配置方式：** 支援自訂 OAuth 憑證和開發人員資訊
        """)


def sidebar():
    """側邊欄"""
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/google-drive.png", width=64)
        st.title("Google Drive 下載工具")
        
        # 使用者資訊
        if st.session_state.authenticated and st.session_state.user_info:
            user_info = st.session_state.user_info
            
            st.markdown("---")
            st.markdown("### 👤 使用者資訊")
            st.markdown(f"**Email:** {user_info.get('email', 'Unknown')}")
            st.markdown(f"**名稱:** {user_info.get('display_name', 'Unknown')}")
            
            # 儲存空間資訊
            storage = user_info.get('storage_quota', {})
            if storage:
                used = int(storage.get('usage', 0))
                limit = int(storage.get('limit', 0)) if storage.get('limit') else None
                
                st.markdown("### 💾 儲存空間")
                st.markdown(f"**已使用:** {format_bytes(used)}")
                if limit:
                    st.markdown(f"**總容量:** {format_bytes(limit)}")
                    usage_percent = (used / limit) * 100
                    st.progress(usage_percent / 100)
            
            st.markdown("---")
            
            # 登出按鈕
            if st.button("🚪 登出", use_container_width=True):
                auth_manager.logout()
                st.session_state.authenticated = False
                st.session_state.user_info = None
                st.rerun()
        
        st.markdown("---")
        
        # 設定
        st.markdown("### ⚙️ 設定")
        
        # 自動重新整理
        auto_refresh = st.checkbox(
            "🔄 自動重新整理",
            value=st.session_state.auto_refresh,
            help="每 5 秒自動更新任務狀態"
        )
        st.session_state.auto_refresh = auto_refresh
        
        # 手動重新整理
        if st.button("🔄 立即重新整理", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        
        # 統計資訊
        if st.session_state.authenticated:
            stats = download_manager.get_summary_stats()
            
            st.markdown("### 📊 統計")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("總任務", stats['total_tasks'])
                st.metric("已完成", stats['completed_tasks'])
            
            with col2:
                st.metric("下載中", stats['downloading_tasks'])
                st.metric("失敗", stats['failed_tasks'])


def download_page():
    """下載頁面"""
    st.title("📥 檔案下載")
    
    # 新建下載任務
    with st.container():
        st.subheader("🆕 新建下載任務")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            url = st.text_input(
                "Google Drive 連結或檔案 ID",
                placeholder="https://drive.google.com/... 或直接輸入檔案 ID",
                help="支援 Google Drive 分享連結或直接輸入檔案/資料夾 ID"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # 對齊
            preview = st.button("👁️ 預覽", help="預覽檔案資訊")
        
        # 進階設定
        with st.expander("⚙️ 進階設定"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                task_name = st.text_input("任務名稱", placeholder="可選，留空自動生成")
                output_dir = st.text_input(
                    "輸出目錄", 
                    value=get_config('download.default_output_dir', './downloads')
                )
            
            with col2:
                max_concurrent = st.slider(
                    "並發下載數", 
                    min_value=1, 
                    max_value=10, 
                    value=get_config('download.max_concurrent', 5)
                )
                
                format_options = ["預設", "docx", "pdf", "xlsx", "csv", "png", "jpg"]
                preferred_format = st.selectbox("偏好格式", format_options)
                if preferred_format == "預設":
                    preferred_format = None
            
            with col3:
                auto_start = st.checkbox("建立後自動開始", value=True)
        
        # 預覽檔案資訊
        if preview and url:
            try:
                file_id = extract_file_id_from_url(url)
                if file_id:
                    with st.spinner("正在取得檔案資訊..."):
                        file_info = file_handler.get_file_info(file_id)
                    
                    st.success("✅ 檔案資訊取得成功")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**📝 名稱:** {file_info.get('name')}")
                        st.markdown(f"**📋 類型:** {file_info.get('mimeType')}")
                        if file_info.get('size'):
                            st.markdown(f"**💾 大小:** {format_bytes(int(file_info['size']))}")
                    
                    with col2:
                        st.markdown(f"**🆔 ID:** {file_info.get('id')}")
                        st.markdown(f"**📅 修改時間:** {file_info.get('modifiedTime')}")
                    
                    # 如果是資料夾，顯示內容統計
                    if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
                        with st.spinner("正在分析資料夾內容..."):
                            contents = file_handler.get_folder_contents(file_id, recursive=True)
                            stats = file_handler.get_download_stats(contents)
                        
                        st.info(f"📂 資料夾包含 {stats['total_files']} 個檔案，總大小 {format_bytes(stats['total_size'])}")
                else:
                    st.error("❌ 無法解析檔案 ID")
                    
            except Exception as e:
                st.error(f"❌ 取得檔案資訊失敗: {e}")
        
        # 建立任務按鈕
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 建立下載任務", type="primary", use_container_width=True):
                if not url:
                    st.error("請輸入 Google Drive 連結或檔案 ID")
                else:
                    try:
                        task_id = download_manager.create_task(
                            source_url=url,
                            output_path=output_dir,
                            name=task_name or None,
                            max_concurrent=max_concurrent,
                            preferred_format=preferred_format
                        )
                        
                        st.success(f"✅ 任務建立成功！ID: {task_id[:8]}...")
                        
                        if auto_start:
                            # 啟動任務
                            asyncio.run(download_manager.start_task(task_id))
                            st.info("🚀 任務已自動開始")
                        
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 建立任務失敗: {e}")


def tasks_page():
    """任務管理頁面"""
    st.title("📋 任務管理")
    
    # 取得所有任務
    tasks = download_manager.get_all_tasks()
    
    if not tasks:
        st.info("📭 目前沒有下載任務")
        return
    
    # 統計圖表
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # 狀態分布餅圖
        status_counts = {}
        for task in tasks:
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            fig_pie = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                title="任務狀態分布"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 檔案數量統計
        completed_tasks = [t for t in tasks if t.status == DownloadStatus.COMPLETED]
        if completed_tasks:
            file_counts = [len(t.downloaded_files) for t in completed_tasks]
            
            fig_bar = px.bar(
                x=[f"Task {i+1}" for i in range(len(file_counts))],
                y=file_counts,
                title="已完成任務檔案數量"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    with col3:
        # 下載大小統計
        if completed_tasks:
            download_sizes = [t.total_size / (1024*1024) for t in completed_tasks if t.total_size > 0]  # MB
            
            if download_sizes:
                fig_scatter = px.scatter(
                    x=range(len(download_sizes)),
                    y=download_sizes,
                    title="任務下載大小 (MB)"
                )
                st.plotly_chart(fig_scatter, use_container_width=True)
    
    st.markdown("---")
    
    # 任務清單
    st.subheader("📝 任務清單")
    
    # 篩選器
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "狀態篩選",
            ["全部"] + [status.value for status in DownloadStatus]
        )
    
    with col2:
        sort_by = st.selectbox(
            "排序方式",
            ["建立時間 (新→舊)", "建立時間 (舊→新)", "名稱", "狀態"]
        )
    
    with col3:
        show_details = st.checkbox("顯示詳細資訊", value=False)
    
    # 篩選和排序任務
    filtered_tasks = tasks
    
    if status_filter != "全部":
        filtered_tasks = [t for t in filtered_tasks if t.status.value == status_filter]
    
    if sort_by == "建立時間 (新→舊)":
        filtered_tasks.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == "建立時間 (舊→新)":
        filtered_tasks.sort(key=lambda x: x.created_at)
    elif sort_by == "名稱":
        filtered_tasks.sort(key=lambda x: x.name)
    elif sort_by == "狀態":
        filtered_tasks.sort(key=lambda x: x.status.value)
    
    # 顯示任務
    for i, task in enumerate(filtered_tasks):
        with st.container():
            # 狀態圖示
            status_icons = {
                DownloadStatus.PENDING: "⏳",
                DownloadStatus.PREPARING: "🔄",
                DownloadStatus.DOWNLOADING: "📥",
                DownloadStatus.COMPLETED: "✅",
                DownloadStatus.FAILED: "❌",
                DownloadStatus.CANCELLED: "🛑",
                DownloadStatus.PAUSED: "⏸️"
            }
            
            status_icon = status_icons.get(task.status, "❓")
            
            # 主要資訊行
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            
            with col1:
                st.markdown(f"**{status_icon} {task.name}**")
                if show_details:
                    st.caption(f"ID: {task.id}")
            
            with col2:
                st.markdown(f"**狀態:** {task.status.value}")
                if show_details and task.error_message:
                    st.error(f"錯誤: {task.error_message[:50]}...")
            
            with col3:
                if task.file_list:
                    total_files = len([f for f in task.file_list if f.get('mimeType') != 'application/vnd.google-apps.folder'])
                    downloaded_files = len(task.downloaded_files)
                    progress_percent = (downloaded_files / total_files * 100) if total_files > 0 else 0
                    
                    st.markdown(f"**進度:** {downloaded_files}/{total_files}")
                    st.progress(progress_percent / 100)
                else:
                    st.markdown("**進度:** 準備中...")
            
            with col4:
                if task.total_size > 0:
                    st.markdown(f"**大小:** {format_bytes(task.total_size)}")
                
                if show_details:
                    if task.started_at:
                        duration = datetime.now() - task.started_at
                        st.caption(f"執行時間: {format_duration(duration.total_seconds())}")
            
            with col5:
                # 操作按鈕
                button_col1, button_col2 = st.columns(2)
                
                with button_col1:
                    if task.status == DownloadStatus.PENDING:
                        if st.button("▶️", key=f"start_{task.id}", help="開始"):
                            asyncio.run(download_manager.start_task(task.id))
                            st.rerun()
                    elif task.status == DownloadStatus.DOWNLOADING:
                        if st.button("⏸️", key=f"pause_{task.id}", help="暫停"):
                            download_manager.pause_task(task.id)
                            st.rerun()
                    elif task.status == DownloadStatus.PAUSED:
                        if st.button("▶️", key=f"resume_{task.id}", help="繼續"):
                            asyncio.run(download_manager.start_task(task.id))
                            st.rerun()
                
                with button_col2:
                    if task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED]:
                        if st.button("🛑", key=f"cancel_{task.id}", help="取消"):
                            download_manager.cancel_task(task.id)
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"delete_{task.id}", help="刪除"):
                            download_manager.delete_task(task.id)
                            st.rerun()
            
            # 詳細資訊（可展開）
            if show_details:
                with st.expander(f"詳細資訊 - {task.name}"):
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.markdown(f"**來源 URL:** {task.source_url}")
                        st.markdown(f"**輸出路徑:** {task.output_path}")
                        st.markdown(f"**建立時間:** {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        if task.started_at:
                            st.markdown(f"**開始時間:** {task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        if task.completed_at:
                            st.markdown(f"**完成時間:** {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    with detail_col2:
                        st.markdown(f"**最大並發數:** {task.max_concurrent}")
                        st.markdown(f"**重試次數:** {task.retry_count}/{task.max_retries}")
                        if task.preferred_format:
                            st.markdown(f"**偏好格式:** {task.preferred_format}")
                        
                        if task.failed_files:
                            st.error(f"失敗檔案: {len(task.failed_files)} 個")
                            
                            # 顯示失敗檔案詳情
                            failed_df = pd.DataFrame([
                                {
                                    'filename': f['file_info'].get('name', 'Unknown'),
                                    'error': f['error']
                                }
                                for f in task.failed_files[:5]  # 只顯示前 5 個
                            ])
                            
                            if not failed_df.empty:
                                st.dataframe(failed_df, use_container_width=True)
            
            st.markdown("---")


def main():
    """主函數"""
    # 初始化
    init_session_state()
    
    # 檢查認證
    if not check_authentication():
        authentication_page()
        return
    
    # 側邊欄
    sidebar()
    
    # 主要內容
    tab1, tab2 = st.tabs(["📥 下載", "📋 任務管理"])
    
    with tab1:
        download_page()
    
    with tab2:
        tasks_page()
    
    # 自動重新整理
    if st.session_state.auto_refresh:
        time.sleep(5)
        st.rerun()


if __name__ == "__main__":
    main() 