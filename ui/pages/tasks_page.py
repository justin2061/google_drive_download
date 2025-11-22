"""
任務管理頁面模組
顯示和管理下載任務
"""

import streamlit as st
import asyncio
import pandas as pd
import plotly.express as px
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.downloader import download_manager, DownloadStatus
from src.utils.helpers import format_bytes
from ..utils.ui_helpers import get_status_icon, format_duration


def render_tasks_page():
    """渲染任務管理頁面"""
    st.title("📋 任務管理")

    # 取得所有任務
    tasks = download_manager.get_all_tasks()

    if not tasks:
        st.info("📭 目前沒有下載任務")
        return

    # 統計圖表
    _render_statistics_charts(tasks)

    st.markdown("---")

    # 任務清單
    _render_task_list(tasks)


def _render_statistics_charts(tasks):
    """渲染統計圖表"""
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
            download_sizes = [t.total_size / (1024*1024) for t in completed_tasks if t.total_size > 0]

            if download_sizes:
                fig_scatter = px.scatter(
                    x=range(len(download_sizes)),
                    y=download_sizes,
                    title="任務下載大小 (MB)"
                )
                st.plotly_chart(fig_scatter, use_container_width=True)


def _render_task_list(tasks):
    """渲染任務清單"""
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
    filtered_tasks = _filter_and_sort_tasks(tasks, status_filter, sort_by)

    # 顯示任務
    for task in filtered_tasks:
        _render_task_item(task, show_details)


def _filter_and_sort_tasks(tasks, status_filter, sort_by):
    """篩選和排序任務"""
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

    return filtered_tasks


def _render_task_item(task, show_details):
    """渲染單個任務項目"""
    with st.container():
        status_icon = get_status_icon(task.status.value)

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

            if show_details and task.started_at:
                duration = datetime.now() - task.started_at
                st.caption(f"執行時間: {format_duration(duration.total_seconds())}")

        with col5:
            _render_task_actions(task)

        # 詳細資訊
        if show_details:
            _render_task_details(task)

        st.markdown("---")


def _render_task_actions(task):
    """渲染任務操作按鈕"""
    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
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

    with btn_col2:
        if task.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED]:
            if st.button("🛑", key=f"cancel_{task.id}", help="取消"):
                download_manager.cancel_task(task.id)
                st.rerun()
        else:
            if st.button("🗑️", key=f"delete_{task.id}", help="刪除"):
                download_manager.delete_task(task.id)
                st.rerun()


def _render_task_details(task):
    """渲染任務詳細資訊"""
    with st.expander(f"詳細資訊 - {task.name}"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**來源 URL:** {task.source_url}")
            st.markdown(f"**輸出路徑:** {task.output_path}")
            st.markdown(f"**建立時間:** {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if task.started_at:
                st.markdown(f"**開始時間:** {task.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if task.completed_at:
                st.markdown(f"**完成時間:** {task.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

        with col2:
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
                    for f in task.failed_files[:5]
                ])

                if not failed_df.empty:
                    st.dataframe(failed_df, use_container_width=True)
