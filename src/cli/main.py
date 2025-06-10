"""
命令列介面主程式
提供簡潔的 CLI 操作介面
"""

import asyncio
import click
from pathlib import Path
import sys
from typing import Optional

# 添加專案根目錄到路徑
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.auth import auth_manager
from src.core.downloader import download_manager, DownloadStatus
from src.core.file_handler import file_handler
from src.utils.config import get_config, load_config
from src.utils.logger import setup_logging, get_logger
from src.utils.helpers import extract_file_id_from_url, format_bytes


# 設定日誌
setup_logging()
logger = get_logger(__name__)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='配置檔案路徑')
@click.option('--debug', is_flag=True, help='啟用除錯模式')
def cli(config: Optional[str], debug: bool):
    """Google Drive 下載工具命令列介面"""
    if config:
        load_config(config)
    
    if debug:
        logger.setLevel('DEBUG')
        logger.debug("除錯模式已啟用")


@cli.command()
def auth():
    """執行 Google Drive 認證"""
    click.echo("🔐 開始 Google Drive 認證...")
    
    try:
        success = auth_manager.authenticate(force_refresh=True)
        
        if success:
            # 測試連線
            if auth_manager.test_connection():
                user_info = auth_manager.get_user_info()
                click.echo(f"✅ 認證成功！")
                click.echo(f"👤 使用者: {user_info.get('email')}")
                click.echo(f"📊 儲存空間: {user_info.get('storage_quota', {})}")
            else:
                click.echo("⚠️ 認證完成，但連線測試失敗")
        else:
            click.echo("❌ 認證失敗")
            
    except Exception as e:
        click.echo(f"❌ 認證過程發生錯誤: {e}")
        logger.error(f"認證失敗: {e}")


@cli.command()
@click.argument('url')
@click.option('--output', '-o', default=None, help='輸出目錄路徑')
@click.option('--name', '-n', default=None, help='任務名稱')
@click.option('--concurrent', '-j', default=None, type=int, help='並發下載數量')
@click.option('--format', '-f', default=None, help='偏好檔案格式 (docx, pdf, xlsx 等)')
@click.option('--wait', '-w', is_flag=True, help='等待下載完成')
def download(url: str, output: Optional[str], name: Optional[str], 
           concurrent: Optional[int], format: Optional[str], wait: bool):
    """下載 Google Drive 檔案或資料夾
    
    URL: Google Drive 分享連結或檔案 ID
    """
    click.echo(f"📥 準備下載: {url}")
    
    # 檢查認證
    if not auth_manager.is_authenticated():
        click.echo("🔐 需要先進行認證...")
        if not auth_manager.authenticate():
            click.echo("❌ 認證失敗，無法下載")
            return
    
    # 設定輸出路徑
    if not output:
        output = get_config('download.default_output_dir', './downloads')
    
    output_path = Path(output)
    
    try:
        # 建立下載任務
        task_id = download_manager.create_task(
            source_url=url,
            output_path=str(output_path),
            name=name,
            max_concurrent=concurrent,
            preferred_format=format
        )
        
        click.echo(f"📋 任務已建立: {task_id}")
        
        if wait:
            # 同步等待下載完成
            asyncio.run(_wait_for_download(task_id))
        else:
            # 非同步啟動下載
            asyncio.run(download_manager.start_task(task_id))
            click.echo(f"🚀 下載已開始，使用 'status {task_id}' 查看進度")
            
    except Exception as e:
        click.echo(f"❌ 下載失敗: {e}")
        logger.error(f"下載失敗: {e}")


async def _wait_for_download(task_id: str):
    """等待下載任務完成"""
    # 啟動任務
    await download_manager.start_task(task_id)
    
    # 等待完成
    while True:
        task = download_manager.get_task(task_id)
        if not task:
            break
            
        if task.status in [DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED]:
            break
            
        # 顯示進度
        if task.file_list:
            total_files = len([f for f in task.file_list if f.get('mimeType') != 'application/vnd.google-apps.folder'])
            downloaded_files = len(task.downloaded_files)
            progress = (downloaded_files / total_files * 100) if total_files > 0 else 0
            
            click.echo(f"\r📊 進度: {downloaded_files}/{total_files} ({progress:.1f}%)", nl=False)
        
        await asyncio.sleep(1)
    
    # 顯示最終結果
    task = download_manager.get_task(task_id)
    if task:
        if task.status == DownloadStatus.COMPLETED:
            click.echo(f"\n✅ 下載完成！")
            click.echo(f"📂 檔案位置: {task.output_path}")
            if task.failed_files:
                click.echo(f"⚠️ {len(task.failed_files)} 個檔案下載失敗")
        elif task.status == DownloadStatus.FAILED:
            click.echo(f"\n❌ 下載失敗: {task.error_message}")
        else:
            click.echo(f"\n🛑 下載已取消")


@cli.command()
@click.argument('task_id', required=False)
def status(task_id: Optional[str]):
    """查看下載任務狀態"""
    if task_id:
        # 顯示特定任務狀態
        task = download_manager.get_task(task_id)
        if not task:
            click.echo(f"❌ 任務不存在: {task_id}")
            return
        
        click.echo(f"📋 任務: {task.name}")
        click.echo(f"🆔 ID: {task.id}")
        click.echo(f"📊 狀態: {task.status.value}")
        click.echo(f"📁 輸出路徑: {task.output_path}")
        
        if task.file_list:
            total_files = len([f for f in task.file_list if f.get('mimeType') != 'application/vnd.google-apps.folder'])
            downloaded_files = len(task.downloaded_files)
            failed_files = len(task.failed_files)
            
            click.echo(f"📄 檔案數量: {total_files}")
            click.echo(f"✅ 已下載: {downloaded_files}")
            click.echo(f"❌ 失敗: {failed_files}")
            
            if task.total_size > 0:
                click.echo(f"💾 總大小: {format_bytes(task.total_size)}")
        
        if task.error_message:
            click.echo(f"🚨 錯誤訊息: {task.error_message}")
            
    else:
        # 顯示所有任務總覽
        stats = download_manager.get_summary_stats()
        
        click.echo("📊 下載任務總覽")
        click.echo("-" * 30)
        click.echo(f"📋 總任務數: {stats['total_tasks']}")
        click.echo(f"⏳ 等待中: {stats['pending_tasks']}")
        click.echo(f"📥 下載中: {stats['downloading_tasks']}")
        click.echo(f"✅ 已完成: {stats['completed_tasks']}")
        click.echo(f"❌ 失敗: {stats['failed_tasks']}")
        click.echo(f"🔄 活躍下載: {stats['active_downloads']}")
        
        if stats['total_downloaded_size'] > 0:
            click.echo(f"💾 總下載量: {format_bytes(stats['total_downloaded_size'])}")
        
        # 顯示最近任務
        recent_tasks = download_manager.get_all_tasks()[-5:]  # 最近 5 個任務
        if recent_tasks:
            click.echo("\n📋 最近任務:")
            for task in recent_tasks:
                status_icon = {
                    DownloadStatus.PENDING: "⏳",
                    DownloadStatus.DOWNLOADING: "📥",
                    DownloadStatus.COMPLETED: "✅",
                    DownloadStatus.FAILED: "❌",
                    DownloadStatus.CANCELLED: "🛑"
                }.get(task.status, "❓")
                
                click.echo(f"  {status_icon} {task.name[:30]:<30} ({task.id[:8]})")


@cli.command()
@click.argument('task_id')
def cancel(task_id: str):
    """取消下載任務"""
    if download_manager.cancel_task(task_id):
        click.echo(f"🛑 任務已取消: {task_id}")
    else:
        click.echo(f"❌ 無法取消任務: {task_id}")


@cli.command()
@click.argument('task_id')
def delete(task_id: str):
    """刪除下載任務"""
    if download_manager.delete_task(task_id):
        click.echo(f"🗑️ 任務已刪除: {task_id}")
    else:
        click.echo(f"❌ 無法刪除任務: {task_id}")


@cli.command()
@click.argument('url_or_id')
def info(url_or_id: str):
    """查看檔案或資料夾資訊"""
    # 檢查認證
    if not auth_manager.is_authenticated():
        click.echo("🔐 需要先進行認證...")
        if not auth_manager.authenticate():
            click.echo("❌ 認證失敗")
            return
    
    try:
        # 提取檔案 ID
        file_id = extract_file_id_from_url(url_or_id)
        if not file_id:
            file_id = url_or_id
        
        # 取得檔案資訊
        file_info = file_handler.get_file_info(file_id)
        
        click.echo(f"📄 檔案資訊")
        click.echo("-" * 30)
        click.echo(f"📝 名稱: {file_info.get('name')}")
        click.echo(f"🆔 ID: {file_info.get('id')}")
        click.echo(f"📋 類型: {file_info.get('mimeType')}")
        
        if file_info.get('size'):
            size = int(file_info['size'])
            click.echo(f"💾 大小: {format_bytes(size)}")
        
        click.echo(f"📅 建立時間: {file_info.get('createdTime')}")
        click.echo(f"📝 修改時間: {file_info.get('modifiedTime')}")
        click.echo(f"🔗 檢視連結: {file_info.get('webViewLink')}")
        
        # 如果是資料夾，顯示內容統計
        if file_info.get('mimeType') == 'application/vnd.google-apps.folder':
            click.echo("\n📂 資料夾內容分析中...")
            contents = file_handler.get_folder_contents(file_id, recursive=True)
            stats = file_handler.get_download_stats(contents)
            
            click.echo(f"📄 總檔案數: {stats['total_files']}")
            click.echo(f"💾 總大小: {format_bytes(stats['total_size'])}")
            click.echo(f"📊 Google Workspace 檔案: {stats['google_workspace_files']}")
            click.echo(f"📎 一般檔案: {stats['regular_files']}")
            
            # 顯示檔案類型分布
            if stats['file_types']:
                click.echo("\n📋 檔案類型分布:")
                for mime_type, count in sorted(stats['file_types'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    type_name = mime_type.split('/')[-1] if '/' in mime_type else mime_type
                    click.echo(f"  {type_name}: {count}")
        
    except Exception as e:
        click.echo(f"❌ 取得檔案資訊失敗: {e}")
        logger.error(f"取得檔案資訊失敗: {e}")


@cli.command()
def logout():
    """登出並清除認證"""
    auth_manager.logout()
    click.echo("🚪 已登出並清除認證資料")


if __name__ == '__main__':
    cli() 