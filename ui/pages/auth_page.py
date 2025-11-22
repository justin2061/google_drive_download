"""
認證頁面模組
處理 Google Drive 認證流程
"""

import streamlit as st
import time
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.oauth_setup import oauth_setup_manager
from ..utils.session_manager import SessionManager, get_auth_manager


def render_auth_page():
    """渲染認證頁面"""
    st.title("🔐 Google Drive 認證")

    st.markdown("""
    ### 歡迎使用 Google Drive 下載工具

    請先完成 Google Drive 認證以開始使用下載功能。
    """)

    # ADC 自動認證區塊
    _render_adc_section()

    st.markdown("---")

    # 手動 OAuth 認證區塊
    _render_oauth_section()

    # 安全性說明
    _render_security_notice()

    # 認證按鈕區域
    _render_auth_buttons()

    # 詳細認證說明
    _render_auth_guide()


def _render_adc_section():
    """渲染 ADC 認證區塊"""
    with st.container():
        st.subheader("⚡ 自動認證 (ADC)")

        st.markdown("""
        **Application Default Credentials (ADC)** 會自動檢查以下認證來源：

        1. 🔑 **GOOGLE_APPLICATION_CREDENTIALS** 環境變數（服務帳戶）
        2. 🔧 **gcloud CLI** 使用者認證
        3. ☁️ **Google Cloud** 環境中繼資料服務

        如果您已設定任何一種，無需手動認證！
        """)

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔍 檢查 ADC 狀態", use_container_width=True):
                _check_adc_status()

        with col2:
            if st.button("📖 ADC 設定指南", use_container_width=True):
                st.session_state.show_adc_guide = not st.session_state.get('show_adc_guide', False)

        # ADC 設定指南
        if st.session_state.get('show_adc_guide', False):
            _render_adc_guide()


def _check_adc_status():
    """檢查 ADC 認證狀態"""
    auth_manager = get_auth_manager()

    with st.spinner("檢查 ADC 認證來源..."):
        success = auth_manager.authenticate()

        if success:
            current_method = auth_manager._current_auth_method
            if current_method == "adc":
                st.success("🎉 ADC 認證成功！自動跳轉到主頁面...")
            elif current_method == "oauth":
                st.success("🎉 使用現有 OAuth 認證成功！自動跳轉到主頁面...")
                st.info("💡 提示：ADC 不可用，已自動使用 OAuth 認證")
            else:
                st.success("🎉 認證成功！自動跳轉到主頁面...")

            time.sleep(2)
            st.rerun()
        else:
            st.error("❌ 認證失敗")
            st.info("ℹ️ 沒有找到可用的認證，請使用下方的手動認證或檢查設定")


def _render_adc_guide():
    """渲染 ADC 設定指南"""
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


def _render_oauth_section():
    """渲染 OAuth 認證區塊"""
    with st.container():
        st.subheader("🔧 手動 OAuth 認證")

        # OAuth 應用程式設定
        with st.expander("⚙️ Google OAuth 應用程式設定", expanded=False):
            _render_oauth_config()

        st.markdown("---")
        st.markdown("### 📖 如何取得 OAuth 憑證")
        with st.container():
            st.markdown(oauth_setup_manager.create_sample_credentials())

        st.markdown("---")

        # 使用者認證設定
        _render_user_auth_input()


def _render_oauth_config():
    """渲染 OAuth 配置區塊"""
    st.markdown("""
    **設定您的 Google OAuth 應用程式**

    這些設定會影響 Google 認證頁面上顯示的開發人員資訊。
    如果您有自己的 Google Cloud 專案，請填入相關資訊。
    """)

    # OAuth 憑證設定
    st.subheader("🔑 OAuth 憑證")

    col1, col2 = st.columns([2, 1])

    with col1:
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

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ 驗證憑證", help="驗證 OAuth 憑證格式"):
            if client_id and client_secret:
                if oauth_setup_manager.validate_oauth_config(client_id, client_secret):
                    st.success("✅ OAuth 憑證格式正確")
                    st.session_state.oauth_client_id = client_id
                    st.session_state.oauth_client_secret = client_secret
                else:
                    st.error("❌ OAuth 憑證格式不正確")

    # 開發人員資訊設定
    st.subheader("👨‍💻 開發人員資訊")

    col1, col2 = st.columns([2, 1])

    with col1:
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

    with col2:
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
    _render_credentials_generator()


def _render_credentials_generator():
    """渲染 credentials.json 生成器"""
    st.subheader("📄 生成 Credentials 檔案")

    has_oauth_config = (
        hasattr(st.session_state, 'oauth_client_id') and
        hasattr(st.session_state, 'oauth_client_secret') and
        st.session_state.oauth_client_id and
        st.session_state.oauth_client_secret
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        if has_oauth_config:
            st.success("✅ OAuth 憑證已設定")
            dev_email = st.session_state.get('developer_email', 'your.dev.email@gmail.com')
            app_name_val = st.session_state.get('app_name', 'Google Drive 下載工具')
            st.info(f"開發人員: {dev_email}")
            st.info(f"應用程式: {app_name_val}")
        else:
            st.warning("⚠️ 請先設定並驗證 OAuth 憑證")

    with col2:
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


def _render_user_auth_input():
    """渲染使用者認證輸入"""
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
        st.markdown("<br>", unsafe_allow_html=True)
        validate_email = st.button("✅ 驗證", help="驗證 Email 格式")

    # Email 格式驗證
    if validate_email or user_email:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if user_email and re.match(email_pattern, user_email):
            st.success(f"✅ Email 格式正確: {user_email}")
            st.session_state.validated_email = user_email
        elif user_email:
            st.error("❌ Email 格式不正確，請重新輸入")
            st.session_state.validated_email = None


def _render_security_notice():
    """渲染安全性說明"""
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


def _render_auth_buttons():
    """渲染認證按鈕"""
    has_valid_email = hasattr(st.session_state, 'validated_email') and st.session_state.validated_email

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button(
            "⚡ 智能認證",
            type="primary",
            use_container_width=True,
            disabled=not has_valid_email,
            help="先嘗試 ADC 自動認證，失敗時使用 OAuth" if has_valid_email else "請先輸入並驗證 Email 地址"
        ):
            _perform_smart_auth()

    with col2:
        if st.button(
            "🔧 強制 OAuth",
            use_container_width=True,
            disabled=not has_valid_email,
            help="強制使用 OAuth 流程認證" if has_valid_email else "請先輸入並驗證 Email 地址"
        ):
            _perform_oauth_auth()

    with col3:
        st.markdown("")

    # 顯示認證提示
    if not has_valid_email:
        st.info("💡 請先輸入您的 Google 帳戶 Email 地址")
    else:
        st.info(f"ℹ️ 準備為 {st.session_state.validated_email} 認證")


def _perform_smart_auth():
    """執行智能認證"""
    auth_manager = get_auth_manager()

    try:
        with st.spinner(f"正在為 {st.session_state.validated_email} 執行智能認證..."):
            success = auth_manager.authenticate(force_refresh=False)

        if success:
            _handle_auth_success(auth_manager, "smart")
        else:
            st.error("❌ 智能認證失敗，請嘗試強制 OAuth 認證")

    except Exception as e:
        st.error(f"❌ 智能認證過程發生錯誤: {e}")


def _perform_oauth_auth():
    """執行 OAuth 認證"""
    auth_manager = get_auth_manager()

    try:
        with st.spinner(f"正在為 {st.session_state.validated_email} 執行 OAuth 認證..."):
            success = auth_manager.authenticate(force_refresh=True)

        if success:
            _handle_auth_success(auth_manager, "oauth")
        else:
            st.error("❌ OAuth 認證失敗，請檢查 credentials.json 檔案")

    except Exception as e:
        st.error(f"❌ OAuth 認證過程發生錯誤: {e}")


def _handle_auth_success(auth_manager, auth_type: str):
    """處理認證成功"""
    user_info = auth_manager.get_user_info()
    actual_email = user_info.get('email', '')
    auth_method = auth_manager._current_auth_method or "unknown"

    if actual_email.lower() == st.session_state.validated_email.lower():
        st.success(f"✅ 認證成功！歡迎 {actual_email} (使用 {auth_method.upper()})")
        SessionManager.set('authenticated', True)
        SessionManager.set('user_info', user_info)
        st.rerun()
    else:
        st.warning(f"⚠️ 您使用了不同的帳戶進行認證（{actual_email}）。如果這是您想要的帳戶，請點擊確認。")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ 確認使用此帳戶", type="primary", key=f"confirm_{auth_type}"):
                SessionManager.set('authenticated', True)
                SessionManager.set('user_info', user_info)
                st.session_state.validated_email = actual_email
                st.rerun()
        with col_b:
            if st.button("🔄 重新認證", key=f"retry_{auth_type}"):
                auth_manager.logout()
                st.rerun()


def _render_auth_guide():
    """渲染詳細認證說明"""
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
        """)
