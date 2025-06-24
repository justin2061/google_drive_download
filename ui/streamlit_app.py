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
        st.session_state.auto_refresh = False  # 預設關閉自動重新整理，避免頁面一直running


def check_authentication():
    """檢查認證狀態（不進行自動認證）"""
    try:
        # 只檢查現有認證狀態，不嘗試新的認證
        if auth_manager.is_authenticated():
            if not st.session_state.authenticated:
                st.session_state.authenticated = True
                # 只在第一次認證時取得用戶資訊，避免重複API呼叫
                try:
                    st.session_state.user_info = auth_manager.get_user_info()
                except Exception as e:
                    logger.warning(f"取得用戶資訊失敗: {e}")
                    st.session_state.user_info = {
                        'email': 'Unknown',
                        'display_name': 'Unknown User',
                        'is_authenticated': True
                    }
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
                        # 檢查實際使用的認證方式
                        current_method = auth_manager._current_auth_method
                        if current_method == "adc":
                            st.success("🎉 ADC 認證成功！自動跳轉到主頁面...")
                        elif current_method == "oauth":
                            st.success("🎉 使用現有 OAuth 認證成功！自動跳轉到主頁面...")
                            st.info("💡 提示：ADC 不可用，已自動使用 OAuth 認證")
                        else:
                            st.success("🎉 認證成功！自動跳轉到主頁面...")
                        
                        time.sleep(2)  # 增加一點時間讓用戶看到訊息
                        st.rerun()
                    else:
                        st.error("❌ 認證失敗")
                        st.info("ℹ️ 沒有找到可用的認證，請使用下方的手動認證或檢查設定")
        
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
        
        # 網路診斷按鈕
        if st.button("🔍 網路診斷", use_container_width=True):
            with st.spinner("正在檢查網路連接..."):
                try:
                    # 簡單的 Google API 連接測試
                    drive_service = auth_manager.get_drive_service()
                    about = drive_service.about().get(fields='user').execute()
                    st.success("✅ Google Drive API 連接正常")
                except Exception as e:
                    st.error(f"❌ 網路連接問題: {e}")
                    st.info("💡 建議：\n1. 檢查網路連接\n2. 嘗試重新登入\n3. 檢查防火牆設定")
        
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
                            contents = file_handler.get_folder_contents(file_id, recursive=True, max_depth=3)
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


def get_root_folder_contents():
    """取得根資料夾的內容"""
    max_retries = 3
    retry_delay = 1.0
    
    for attempt in range(max_retries):
        try:
            # 使用輕量級方法避免卡住
            return file_handler.get_folder_contents_lite('root')
            
        except Exception as e:
            logger.error(f"取得根資料夾內容失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:
                # 還有重試次數，等待後重試
                st.warning(f"⚠️ 網路連接問題，正在重試... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay * (attempt + 1))  # 遞增延遲
            else:
                # 最後一次嘗試失敗
                st.error(f"❌ 無法載入 Google Drive 內容: {e}")
                st.info("💡 請檢查網路連接，然後點擊「重新整理」按鈕重試")
                return []


def folder_browser_page():
    """資料夾瀏覽頁面"""
    st.header("📁 Google Drive 資料夾瀏覽")
    
    # 當前路徑顯示
    if 'current_folder_id' not in st.session_state:
        st.session_state.current_folder_id = None
        st.session_state.current_folder_name = "我的雲端硬碟"
        st.session_state.folder_path = ["我的雲端硬碟"]
        st.session_state.folder_id_path = [None]
    
    # 路徑導航
    st.markdown("### 📍 當前位置")
    
    # 顯示面包屑導航
    breadcrumb_cols = st.columns(len(st.session_state.folder_path))
    for i, (folder_name, folder_id) in enumerate(zip(st.session_state.folder_path, st.session_state.folder_id_path)):
        with breadcrumb_cols[i]:
            if st.button(f"📁 {folder_name}", key=f"breadcrumb_{i}"):
                # 點擊面包屑導航
                st.session_state.current_folder_id = folder_id
                st.session_state.current_folder_name = folder_name
                st.session_state.folder_path = st.session_state.folder_path[:i+1]
                st.session_state.folder_id_path = st.session_state.folder_id_path[:i+1]
                st.rerun()
    
    st.markdown("---")
    
    # 搜尋和篩選區域
    with st.expander("🔍 搜尋與篩選", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_query = st.text_input("🔍 搜尋檔案/資料夾", placeholder="輸入關鍵字...")
        
        with col2:
            file_type_filter = st.selectbox(
                "📄 檔案類型篩選",
                ["全部", "僅資料夾", "僅檔案", "Google 文件", "圖片", "影片", "PDF"],
                index=0
            )
        
        with col3:
            sort_order = st.selectbox(
                "📊 排序方式",
                ["名稱 (A-Z)", "名稱 (Z-A)", "修改時間 (新→舊)", "修改時間 (舊→新)", "大小 (大→小)", "大小 (小→大)"],
                index=0
            )
    
    # 載入資料夾內容
    with st.spinner("🔄 載入資料夾內容..."):
        if st.session_state.current_folder_id is None:
            # 載入根資料夾
            folder_contents = get_root_folder_contents()
        else:
            # 載入指定資料夾，帶有重試機制
            folder_contents = []
            max_retries = 3
            
            for attempt in range(max_retries):
                                        try:
                            # 使用輕量級方法避免卡住
                            folder_contents = file_handler.get_folder_contents_lite(st.session_state.current_folder_id)
                    break  # 成功則跳出重試迴圈
                except Exception as e:
                    logger.error(f"載入資料夾失敗 (嘗試 {attempt + 1}/{max_retries}): {e}")
                    
                    if attempt < max_retries - 1:
                        st.warning(f"⚠️ 載入資料夾時遇到問題，正在重試... ({attempt + 1}/{max_retries})")
                        time.sleep(1.0 * (attempt + 1))  # 遞增延遲
                    else:
                        st.error(f"❌ 載入資料夾失敗: {e}")
                        st.info("💡 請檢查網路連接，然後點擊「重新整理」按鈕重試")
                        folder_contents = []
    
    if not folder_contents:
        st.info("📭 此資料夾是空的或載入失敗")
        return
    
    # 應用搜尋篩選
    if search_query:
        folder_contents = [
            item for item in folder_contents 
            if search_query.lower() in item.get('name', '').lower()
        ]
    
    # 應用檔案類型篩選
    if file_type_filter == "僅資料夾":
        folder_contents = [item for item in folder_contents if item.get('mimeType') == 'application/vnd.google-apps.folder']
    elif file_type_filter == "僅檔案":
        folder_contents = [item for item in folder_contents if item.get('mimeType') != 'application/vnd.google-apps.folder']
    elif file_type_filter == "Google 文件":
        folder_contents = [item for item in folder_contents if 'google-apps' in item.get('mimeType', '')]
    elif file_type_filter == "圖片":
        folder_contents = [item for item in folder_contents if item.get('mimeType', '').startswith('image/')]
    elif file_type_filter == "影片":
        folder_contents = [item for item in folder_contents if item.get('mimeType', '').startswith('video/')]
    elif file_type_filter == "PDF":
        folder_contents = [item for item in folder_contents if item.get('mimeType') == 'application/pdf']
    
    # 應用排序
    if sort_order == "名稱 (A-Z)":
        folder_contents.sort(key=lambda x: x.get('name', '').lower())
    elif sort_order == "名稱 (Z-A)":
        folder_contents.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
    elif sort_order == "修改時間 (新→舊)":
        folder_contents.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)
    elif sort_order == "修改時間 (舊→新)":
        folder_contents.sort(key=lambda x: x.get('modifiedTime', ''))
    elif sort_order == "大小 (大→小)":
        folder_contents.sort(key=lambda x: int(x.get('size', 0)), reverse=True)
    elif sort_order == "大小 (小→大)":
        folder_contents.sort(key=lambda x: int(x.get('size', 0)))
    
    # 分離資料夾和檔案
    folders = [item for item in folder_contents if item.get('mimeType') == 'application/vnd.google-apps.folder']
    files = [item for item in folder_contents if item.get('mimeType') != 'application/vnd.google-apps.folder']
    
    # 統計資訊
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📁 資料夾數量", len(folders))
    with col2:
        st.metric("📄 檔案數量", len(files))
    with col3:
        if files:
            total_size = sum(int(f.get('size', 0)) for f in files if f.get('size'))
            st.metric("💾 總大小", format_bytes(total_size))
        else:
            st.metric("💾 總大小", "N/A")
    
    st.markdown("---")
    
    # 快速操作區域
    if st.session_state.current_folder_id is not None:
        with st.container():
            st.markdown("### ⚡ 快速操作")
            quick_col1, quick_col2, quick_col3 = st.columns(3)
            
            with quick_col1:
                if st.button("📥 下載整個資料夾", use_container_width=True, type="primary"):
                    # 下載當前資料夾
                    current_folder = {
                        'id': st.session_state.current_folder_id,
                        'name': st.session_state.current_folder_name
                    }
                    st.session_state.selected_folder_for_download = current_folder
                    st.session_state.show_download_options = True
                    st.rerun()
            
            with quick_col2:
                if st.button("🔄 重新整理", use_container_width=True):
                    st.rerun()
            
            with quick_col3:
                if st.button("🔙 回到上層", use_container_width=True):
                    if len(st.session_state.folder_path) > 1:
                        st.session_state.folder_path.pop()
                        st.session_state.folder_id_path.pop()
                        st.session_state.current_folder_id = st.session_state.folder_id_path[-1]
                        st.session_state.current_folder_name = st.session_state.folder_path[-1]
                        st.rerun()
        
        st.markdown("---")
    
    # 資料夾顯示
    if folders:
        st.subheader("📁 資料夾")
        
        # 創建資料夾網格布局
        folder_cols = 3
        folder_rows = (len(folders) + folder_cols - 1) // folder_cols
        
        for row in range(folder_rows):
            cols = st.columns(folder_cols)
            for col_idx in range(folder_cols):
                folder_idx = row * folder_cols + col_idx
                if folder_idx < len(folders):
                    folder = folders[folder_idx]
                    
                    with cols[col_idx]:
                        with st.container():
                            # 資料夾卡片
                            import html
                            folder_name = folder.get('name', '未命名資料夾')
                            folder_name_display = html.escape(folder_name[:20] + ('...' if len(folder_name) > 20 else ''))
                            modified_time = folder.get('modifiedTime', 'N/A')[:10] if folder.get('modifiedTime') else 'N/A'
                            
                            st.markdown(f"""
                            <div style="
                                border: 1px solid #ddd; 
                                border-radius: 8px; 
                                padding: 15px; 
                                margin: 5px; 
                                background-color: #f8f9fa;
                                text-align: center;
                                min-height: 120px;
                                display: flex;
                                flex-direction: column;
                                justify-content: space-between;
                                transition: transform 0.2s;
                            ">
                                <div>
                                    <div style="font-size: 24px; margin-bottom: 8px;">📁</div>
                                    <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px; word-wrap: break-word; text-align: center; color: #333;">
                                        {folder_name_display}
                                    </div>
                                    <div style="font-size: 12px; color: #666;">
                                        修改時間: {modified_time}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # 操作按鈕
                            button_col1, button_col2 = st.columns(2)
                            
                            with button_col1:
                                if st.button("🔍 進入", key=f"enter_folder_{folder['id']}", use_container_width=True):
                                    # 進入資料夾
                                    st.session_state.current_folder_id = folder['id']
                                    st.session_state.current_folder_name = folder['name']
                                    st.session_state.folder_path.append(folder['name'])
                                    st.session_state.folder_id_path.append(folder['id'])
                                    st.rerun()
                            
                            with button_col2:
                                if st.button("📥 下載", key=f"download_folder_{folder['id']}", use_container_width=True):
                                    # 添加下載任務
                                    st.session_state.selected_folder_for_download = folder
                                    st.session_state.show_download_options = True
                                    st.rerun()
        
        st.markdown("---")
    
    # 檔案顯示（改進版本）
    if files:
        st.subheader("📄 檔案")
        
        # 檔案視圖切換
        view_mode = st.radio("顯示模式", ["表格視圖", "卡片視圖"], horizontal=True)
        
        if view_mode == "表格視圖":
            # 檔案清單（表格形式）
            file_data = []
            for file in files[:50]:  # 最多顯示 50 個檔案
                # 檔案類型圖示
                mime_type = file.get('mimeType', '')
                if 'google-apps.document' in mime_type:
                    icon = "📝"
                elif 'google-apps.spreadsheet' in mime_type:
                    icon = "📊"
                elif 'google-apps.presentation' in mime_type:
                    icon = "📽️"
                elif mime_type.startswith('image/'):
                    icon = "🖼️"
                elif mime_type.startswith('video/'):
                    icon = "🎥"
                elif 'pdf' in mime_type:
                    icon = "📕"
                else:
                    icon = "📄"
                
                # 處理檔案名稱
                file_name = file.get('name', '未命名檔案')
                file_name_display = file_name[:40] + ('...' if len(file_name) > 40 else '')
                
                file_data.append({
                    '類型': icon,
                    '名稱': file_name_display,
                    '大小': format_bytes(int(file.get('size', 0))) if file.get('size') else 'N/A',
                    '修改時間': file.get('modifiedTime', 'N/A')[:10] if file.get('modifiedTime') else 'N/A'
                })
            
            if file_data:
                df = pd.DataFrame(file_data)
                st.dataframe(df, use_container_width=True)
                
                if len(files) > 50:
                    st.info(f"顯示前 50 個檔案，共 {len(files)} 個檔案")
        
        else:  # 卡片視圖
            file_cols = 4
            file_rows = (min(len(files), 20) + file_cols - 1) // file_cols
            
            for row in range(file_rows):
                cols = st.columns(file_cols)
                for col_idx in range(file_cols):
                    file_idx = row * file_cols + col_idx
                    if file_idx < min(len(files), 20):
                        file = files[file_idx]
                        
                        with cols[col_idx]:
                            # 檔案類型圖示
                            import html
                            mime_type = file.get('mimeType', '')
                            if 'google-apps.document' in mime_type:
                                icon = "📝"
                                color = "#4285f4"
                            elif 'google-apps.spreadsheet' in mime_type:
                                icon = "📊"
                                color = "#34a853"
                            elif 'google-apps.presentation' in mime_type:
                                icon = "📽️"
                                color = "#fbbc04"
                            elif mime_type.startswith('image/'):
                                icon = "🖼️"
                                color = "#ea4335"
                            elif mime_type.startswith('video/'):
                                icon = "🎥"
                                color = "#9c27b0"
                            elif 'pdf' in mime_type:
                                icon = "📕"
                                color = "#ff5722"
                            else:
                                icon = "📄"
                                color = "#757575"
                            
                            # 檔案名稱處理
                            file_name = file.get('name', '未命名檔案')
                            file_name_display = html.escape(file_name[:15] + ('...' if len(file_name) > 15 else ''))
                            file_size = format_bytes(int(file.get('size', 0))) if file.get('size') else 'N/A'
                            
                            st.markdown(f"""
                            <div style="
                                border: 1px solid #ddd; 
                                border-radius: 8px; 
                                padding: 10px; 
                                margin: 3px; 
                                background-color: #fff;
                                text-align: center;
                                min-height: 100px;
                                border-left: 4px solid {color};
                            ">
                                <div style="font-size: 20px; margin-bottom: 5px;">{icon}</div>
                                <div style="font-size: 12px; font-weight: bold; margin-bottom: 3px; word-wrap: break-word;">
                                    {file_name_display}
                                </div>
                                <div style="font-size: 10px; color: #666;">
                                    {file_size}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            
            if len(files) > 20:
                st.info(f"顯示前 20 個檔案，共 {len(files)} 個檔案")
    
    # 下載選項對話框
    if st.session_state.get('show_download_options', False):
        st.markdown("---")
        st.subheader("📥 下載設定")
        
        selected_folder = st.session_state.get('selected_folder_for_download')
        if selected_folder:
            st.info(f"準備下載資料夾: **{selected_folder['name']}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**下載選項**")
                include_subfolders = st.checkbox("包含子資料夾", value=True)
                max_concurrent = st.slider("最大並發數", min_value=1, max_value=10, value=3)
                preferred_format = st.selectbox(
                    "Google Workspace 檔案格式",
                    ["pdf", "docx", "xlsx", "pptx", "txt", "html"],
                    index=0
                )
            
            with col2:
                st.markdown("**輸出設定**")
                output_path = st.text_input(
                    "輸出路徑",
                    value=str(Path("output") / selected_folder['name']),
                    help="下載檔案的儲存位置"
                )
                
                # 預估資訊
                try:
                    with st.spinner("計算資料夾大小..."):
                                            folder_stats = file_handler.get_download_stats(
                        file_handler.get_folder_contents(selected_folder['id'], recursive=include_subfolders, max_depth=5)
                    )
                    
                    st.markdown("**預估資訊**")
                    st.text(f"檔案數量: {folder_stats.get('total_files', 0)}")
                    st.text(f"總大小: {format_bytes(folder_stats.get('total_size', 0))}")
                    
                except Exception as e:
                    st.warning(f"無法計算資料夾大小: {e}")
            
            # 下載按鈕
            button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
            
            with button_col1:
                if st.button("✅ 開始下載", type="primary", use_container_width=True):
                    # 創建下載任務 - 避免在 UI 中進行耗時操作
                    try:
                        folder_url = f"https://drive.google.com/drive/folders/{selected_folder['id']}"
                        
                        # 快速創建任務，不進行預先分析
                        task_id = download_manager.create_task(
                            source_url=folder_url,
                            output_path=Path(output_path),
                            max_concurrent=max_concurrent,
                            preferred_format=preferred_format
                        )
                        
                        st.success(f"✅ 下載任務已創建！任務 ID: {task_id}")
                        st.info("📋 任務將在後台進行分析和下載，請到「任務管理」頁面查看進度")
                        
                        # 清除狀態
                        st.session_state.show_download_options = False
                        st.session_state.selected_folder_for_download = None
                        
                        # 提示用戶切換到任務管理頁面
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ 創建下載任務失敗: {e}")
            
            with button_col2:
                if st.button("❌ 取消", use_container_width=True):
                    st.session_state.show_download_options = False
                    st.session_state.selected_folder_for_download = None
                    st.rerun()
            
            with button_col3:
                if st.button("🔍 預覽內容", use_container_width=True):
                    # 顯示資料夾詳細內容
                    st.session_state.show_folder_preview = True
                    st.rerun()

    # 資料夾預覽對話框
    if st.session_state.get('show_folder_preview', False):
        st.markdown("---")
        st.subheader("🔍 資料夾詳細預覽")
        
        selected_folder = st.session_state.get('selected_folder_for_download')
        if selected_folder:
            st.info(f"預覽資料夾: **{selected_folder['name']}**")
            
            try:
                with st.spinner("載入資料夾內容詳細資訊..."):
                    # 帶有重試機制的資料夾內容載入
                    preview_contents = []
                    max_retries = 2
                    
                    for attempt in range(max_retries):
                        try:
                            preview_contents = file_handler.get_folder_contents(selected_folder['id'], recursive=True, max_depth=3)
                            break
                        except Exception as inner_e:
                            if attempt < max_retries - 1:
                                st.warning(f"⚠️ 載入預覽時遇到問題，正在重試...")
                                time.sleep(2.0)
                            else:
                                raise inner_e
                
                # 統計分析
                total_files = len([f for f in preview_contents if f.get('mimeType') != 'application/vnd.google-apps.folder'])
                total_folders = len([f for f in preview_contents if f.get('mimeType') == 'application/vnd.google-apps.folder'])
                total_size = sum(int(f.get('size', 0)) for f in preview_contents if f.get('size'))
                
                # 檔案類型統計
                file_types = {}
                for item in preview_contents:
                    if item.get('mimeType') != 'application/vnd.google-apps.folder':
                        mime_type = item.get('mimeType', 'unknown')
                        if 'google-apps.document' in mime_type:
                            file_types['Google 文件'] = file_types.get('Google 文件', 0) + 1
                        elif 'google-apps.spreadsheet' in mime_type:
                            file_types['Google 試算表'] = file_types.get('Google 試算表', 0) + 1
                        elif 'google-apps.presentation' in mime_type:
                            file_types['Google 簡報'] = file_types.get('Google 簡報', 0) + 1
                        elif mime_type.startswith('image/'):
                            file_types['圖片'] = file_types.get('圖片', 0) + 1
                        elif mime_type.startswith('video/'):
                            file_types['影片'] = file_types.get('影片', 0) + 1
                        elif 'pdf' in mime_type:
                            file_types['PDF'] = file_types.get('PDF', 0) + 1
                        else:
                            file_types['其他'] = file_types.get('其他', 0) + 1
                
                # 顯示統計資訊
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("### 📊 內容統計")
                    st.metric("📁 子資料夾", total_folders)
                    st.metric("📄 檔案總數", total_files) 
                    st.metric("💾 總大小", format_bytes(total_size))
                    
                    # 檔案類型分佈圓餅圖
                    if file_types:
                        fig_pie = px.pie(
                            values=list(file_types.values()),
                            names=list(file_types.keys()),
                            title="檔案類型分佈"
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    st.markdown("### 📝 檔案類型詳細")
                    for file_type, count in file_types.items():
                        st.text(f"{file_type}: {count} 個")
                    
                    # 最大的檔案
                    largest_files = sorted(
                        [f for f in preview_contents if f.get('size')],
                        key=lambda x: int(x.get('size', 0)),
                        reverse=True
                    )[:5]
                    
                    if largest_files:
                        st.markdown("### 📈 最大的檔案")
                        for file in largest_files:
                            st.text(f"📄 {file['name'][:30]}... - {format_bytes(int(file.get('size', 0)))}")
                
                # 資料夾結構樹
                st.markdown("### 🌳 資料夾結構")
                
                # 構建資料夾樹狀結構
                folder_tree = {}
                for item in preview_contents:
                    if item.get('mimeType') == 'application/vnd.google-apps.folder':
                        parents = item.get('parents', [])
                        if parents:
                            parent_id = parents[0]
                            if parent_id not in folder_tree:
                                folder_tree[parent_id] = []
                            folder_tree[parent_id].append(item['name'])
                
                # 顯示樹狀結構（簡化版）
                for parent, children in list(folder_tree.items())[:10]:  # 限制顯示數量
                    for child in children[:5]:  # 每個父資料夾最多顯示5個子資料夾
                        st.text(f"📁 {child}")
                
                if len(folder_tree) > 10:
                    st.info(f"還有 {len(folder_tree) - 10} 個資料夾未顯示...")
                
                # 操作按鈕
                button_preview_col1, button_preview_col2 = st.columns(2)
                
                with button_preview_col1:
                    if st.button("📥 確認下載此資料夾", type="primary", use_container_width=True):
                        st.session_state.show_folder_preview = False
                        # 保持下載選項開啟
                        st.rerun()
                
                with button_preview_col2:
                    if st.button("❌ 關閉預覽", use_container_width=True):
                        st.session_state.show_folder_preview = False
                        st.rerun()
                
            except Exception as e:
                st.error(f"載入資料夾預覽失敗: {e}")
                if st.button("❌ 關閉預覽"):
                    st.session_state.show_folder_preview = False
                    st.rerun()

    # 性能提示
    if st.session_state.get('show_download_options', False) or st.session_state.get('show_folder_preview', False):
        with st.expander("⚡ 性能優化提示", expanded=False):
            st.markdown("""
            ### 🚀 避免應用程式卡住的建議
            
            **對於大型資料夾：**
            - ✅ **直接下載**：不需要預覽，直接創建下載任務
            - ✅ **限制遞迴深度**：系統已自動限制遞迴深度為 3-5 層
            - ✅ **分批處理**：系統會自動分批處理大量檔案
            
            **如果應用程式無響應：**
            1. 🔄 重新整理瀏覽器頁面
            2. 🔄 重新啟動 Streamlit 應用程式
            3. 💡 使用「輕量級」瀏覽模式（已啟用）
            
            **推薦操作流程：**
            1. 📁 瀏覽到目標資料夾
            2. 📥 直接點擊「下載」（跳過預覽）
            3. 📋 到「任務管理」頁面監控進度
            """)


def main():
    """主函數"""
    # 初始化
    init_session_state()
    
    # 檢查認證
    if not check_authentication():
        authentication_page()
        return
    
    # 性能警告
    if 'performance_warning_shown' not in st.session_state:
        st.session_state.performance_warning_shown = True
        st.info("💡 **性能提示**：本應用已優化大型資料夾處理。如遇到卡頓，請使用「重新整理」或重新啟動應用程式。")
    
    # 側邊欄
    sidebar()
    
    # 主要內容 - 新增資料夾瀏覽 tab
    tab1, tab2, tab3 = st.tabs(["🌐 資料夾瀏覽", "📥 下載", "📋 任務管理"])
    
    with tab1:
        folder_browser_page()
    
    with tab2:
        download_page()
    
    with tab3:
        tasks_page()
    
    # 自動重新整理（只在任務管理頁面需要時使用）
    # 移除全域自動重新整理，避免造成頁面一直running的問題
    # 如果需要即時更新，請在特定元件中使用 st.empty() 和手動更新


if __name__ == "__main__":
    main() 