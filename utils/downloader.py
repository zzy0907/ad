import requests
from typing import Dict, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import os
from dataclasses import dataclass
from datetime import datetime
import time
import uuid
from plyer import notification
import threading
import tempfile

@dataclass
class ProxyConfig:
    """代理配置"""
    enabled: bool = False
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    
    def get_proxy_dict(self) -> Dict[str, str]:
        """获取代理配置字典"""
        if not self.enabled or not self.host or not self.port:
            return {}
        
        auth = f"{self.username}:{self.password}@" if self.username and self.password else ""
        proxy = f"http://{auth}{self.host}:{self.port}"
        return {
            "http": proxy,
            "https": proxy
        }

@dataclass
class DownloadChunk:
    """下载分片数据"""
    start: int
    end: int
    downloaded: int = 0
    status: str = "等待中"  # 等待中、下载中、已完成、已暂停、错误
    temp_file: str = ""

@dataclass
class DownloadTask:
    """下载任务数据类"""
    url: str
    save_path: str
    total_size: int = 0
    downloaded_size: int = 0
    status: str = "等待中"  # 等待中、下载中、已完成、已暂停、错误
    speed: float = 0.0  # KB/s
    start_time: Optional[datetime] = None
    error_msg: str = ""
    speed_limit: float = 0.0  # KB/s, 0表示不限速
    chunks: List[DownloadChunk] = None
    chunk_size: int = 10 * 1024 * 1024  # 10MB per chunk
    merge_lock: threading.Lock = None
    thread_count: int = 8  # 默认8线程

    def __post_init__(self):
        self.chunks = []
        self.merge_lock = threading.Lock()

    def calculate_chunk_size(self):
        """根据文件大小和线程数计算分片大小"""
        if self.total_size > 0:
            # 确保每个线程至少处理1MB的数据
            min_chunk = 1024 * 1024  # 1MB
            chunk_size = max(min_chunk, self.total_size // self.thread_count)
            self.chunk_size = chunk_size

class ChunkDownloader(QThread):
    """分片下载线程"""
    progress = pyqtSignal(int)  # 下载进度
    completed = pyqtSignal()    # 完成信号
    error = pyqtSignal(str)     # 错误信号
    speed = pyqtSignal(float)   # 下载速度信号
    status = pyqtSignal(str)    # 状态信号

    def __init__(self, url: str, chunk: DownloadChunk, proxies: Dict = None):
        super().__init__()
        self.url = url
        self.chunk = chunk
        self.proxies = proxies
        self.is_paused = False
        self.is_cancelled = False
        self._last_download_time = time.time()
        self._downloaded_in_period = 0
        self.current_speed = 0.0
        self._speed_limit = 0  # KB/s
        self._speed_limit_sleep = 0.1  # 限速检查间隔

    def set_speed_limit(self, limit: float):
        """设置速度限制 (KB/s)"""
        self._speed_limit = limit

    def run(self):
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False) as tf:
                self.chunk.temp_file = tf.name

            headers = {'Range': f'bytes={self.chunk.start}-{self.chunk.end}'}
            response = requests.get(
                self.url,
                headers=headers,
                stream=True,
                proxies=self.proxies,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()

            self.status.emit("下载中")
            self.chunk.status = "下载中"

            with open(self.chunk.temp_file, 'wb') as f:
                start_time = time.time()
                chunk_size = 8192  # 8KB
                
                for data in response.iter_content(chunk_size=chunk_size):
                    if self.is_cancelled:
                        return
                        
                    if self.is_paused:
                        self.status.emit("已暂停")
                        self.chunk.status = "已暂停"
                        while self.is_paused and not self.is_cancelled:
                            time.sleep(0.1)
                        if self.is_cancelled:
                            return
                        self.status.emit("下载中")
                        self.chunk.status = "下载中"
                        start_time = time.time()  # 重置计时

                    if data:
                        f.write(data)
                        self.chunk.downloaded += len(data)
                        
                        # 计算进度
                        progress = int((self.chunk.downloaded / (self.chunk.end - self.chunk.start + 1)) * 100)
                        self.progress.emit(progress)
                        
                        # 计算速度
                        current_time = time.time()
                        elapsed = current_time - self._last_download_time
                        if elapsed >= 1:
                            self.current_speed = (self.chunk.downloaded - self._downloaded_in_period) / 1024 / elapsed  # KB/s
                            self.speed.emit(self.current_speed)
                            self._last_download_time = current_time
                            self._downloaded_in_period = self.chunk.downloaded
                        
                        # 速度限制
                        if self._speed_limit > 0:
                            actual_speed = len(data) / 1024  # KB
                            if actual_speed > self._speed_limit * self._speed_limit_sleep:
                                sleep_time = actual_speed / self._speed_limit - self._speed_limit_sleep
                                if sleep_time > 0:
                                    time.sleep(sleep_time)

            self.status.emit("已完成")
            self.chunk.status = "已完成"
            self.completed.emit()

        except Exception as e:
            self.status.emit("错误")
            self.chunk.status = "错误"
            self.error.emit(str(e))
            print(f"分片下载错误：{str(e)}")  # 添加错误日志

        finally:
            if self.is_cancelled and os.path.exists(self.chunk.temp_file):
                try:
                    os.remove(self.chunk.temp_file)
                except:
                    pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def cancel(self):
        self.is_cancelled = True
        if self.is_paused:
            self.resume()

class DownloadWorker(QThread):
    """下载管理线程"""
    chunk_progress = pyqtSignal(str, int, int, float, str)  # task_id, chunk_index, progress, speed, status

    def __init__(self, task_id: str, task: DownloadTask, progress_handler: 'DownloadProgress', proxy_config: 'ProxyConfig'):
        super().__init__()
        self.task_id = task_id
        self.task = task
        self.progress_handler = progress_handler
        self.proxy_config = proxy_config
        self.is_paused = False
        self.is_cancelled = False
        self.chunk_threads: List[ChunkDownloader] = []
        self._speed_limit = 0.0
        self._last_download_time = time.time()
        self._downloaded_in_period = 0

    def _init_download(self):
        """初始化下载，获取文件大小并创建分片"""
        try:
            # 先发送HEAD请求获取文件大小
            response = requests.head(
                self.task.url,
                proxies=self.proxy_config.get_proxy_dict(),
                timeout=30,
                allow_redirects=True  # 允许重定向
            )
            response.raise_for_status()
            
            # 检查是否支持断点续传
            if 'accept-ranges' not in response.headers:
                # 不支持断点续传，使用单线程下载
                self.task.thread_count = 1
                self.task.total_size = int(response.headers.get('content-length', 0))
                if self.task.total_size == 0:
                    raise ValueError("无法获取文件大小")
                self.task.chunks = [DownloadChunk(start=0, end=self.task.total_size-1)]
                return

            total_size = int(response.headers.get('content-length', 0))
            if total_size == 0:
                raise ValueError("无法获取文件大小")

            self.task.total_size = total_size
            
            # 根据线程数计算分片大小
            chunk_size = total_size // self.task.thread_count
            
            # 确保每个分片至少1MB
            min_chunk_size = 1024 * 1024  # 1MB
            if chunk_size < min_chunk_size:
                chunk_size = min_chunk_size
                thread_count = max(1, total_size // chunk_size)
                self.task.thread_count = thread_count
            
            # 创建分片
            chunks = []
            for i in range(self.task.thread_count):
                start = i * chunk_size
                if i == self.task.thread_count - 1:
                    # 最后一个分片包含剩余的所有数据
                    end = total_size - 1
                else:
                    end = start + chunk_size - 1
                chunks.append(DownloadChunk(start=start, end=end))
            
            self.task.chunks = chunks
            print(f"初始化下载：总大小={total_size}字节，分片数={len(chunks)}")
            for i, chunk in enumerate(chunks):
                print(f"分片{i+1}: {chunk.start}-{chunk.end}")

        except requests.exceptions.RequestException as e:
            raise Exception(f"初始化下载失败：{str(e)}")

    def _merge_chunks(self):
        """合并下载的分片"""
        with open(self.task.save_path, 'wb') as outfile:
            for chunk in self.task.chunks:
                if os.path.exists(chunk.temp_file):
                    with open(chunk.temp_file, 'rb') as infile:
                        outfile.write(infile.read())
                    # 删除临时文件
                    try:
                        os.remove(chunk.temp_file)
                    except:
                        pass

    def run(self):
        try:
            # 初始化下载
            self._init_download()
            
            self.task.start_time = datetime.now()
            self.task.status = "下载中"
            self.progress_handler.status.emit(self.task_id, "下载中")

            # 创建并启动分片下载线程
            proxies = self.proxy_config.get_proxy_dict()
            for i, chunk in enumerate(self.task.chunks):
                downloader = ChunkDownloader(self.task.url, chunk, proxies)
                downloader.progress.connect(lambda p, i=i: self._update_chunk_progress(i, p))
                downloader.speed.connect(lambda s, i=i: self._update_chunk_speed(i, s))
                downloader.status.connect(lambda st, i=i: self._update_chunk_status(i, st))
                downloader.error.connect(lambda e: self.progress_handler.error.emit(self.task_id, e))
                self.chunk_threads.append(downloader)
                downloader.start()

            # 等待所有分片完成
            while True:
                if self.is_cancelled:
                    for thread in self.chunk_threads:
                        thread.cancel()
                    for thread in self.chunk_threads:
                        thread.wait()
                    return

                if self.is_paused:
                    for thread in self.chunk_threads:
                        thread.pause()
                    continue

                # 检查是否所有分片都完成
                all_completed = True
                total_downloaded = 0
                for chunk in self.task.chunks:
                    if chunk.status != "已完成":
                        all_completed = False
                    total_downloaded += chunk.downloaded

                # 更新总进度
                self.task.downloaded_size = total_downloaded
                progress = int((total_downloaded / self.task.total_size) * 100)
                self.progress_handler.progress.emit(self.task_id, progress)

                # 计算速度
                current_time = time.time()
                elapsed = current_time - self._last_download_time
                if elapsed >= 1:
                    speed = (total_downloaded - self._downloaded_in_period) / 1024 / elapsed  # KB/s
                    self.task.speed = speed
                    self.progress_handler.speed.emit(self.task_id, speed)
                    self._last_download_time = current_time
                    self._downloaded_in_period = total_downloaded

                if all_completed:
                    break

                time.sleep(0.1)

            # 合并分片
            self._merge_chunks()

            self.task.status = "已完成"
            self.progress_handler.status.emit(self.task_id, "已完成")
            self.progress_handler.completed.emit(self.task_id)

            # 显示完成通知
            filename = os.path.basename(self.task.save_path)
            self._show_notification(
                "下载完成",
                f"文件 {filename} 已下载完成"
            )

        except Exception as e:
            self.task.status = "错误"
            self.task.error_msg = str(e)
            self.progress_handler.error.emit(self.task_id, str(e))

            # 显示错误通知
            filename = os.path.basename(self.task.save_path)
            self._show_notification(
                "下载失败",
                f"文件 {filename} 下载失败：{str(e)}"
            )

        finally:
            # 清理临时文件
            for chunk in self.task.chunks:
                if os.path.exists(chunk.temp_file):
                    try:
                        os.remove(chunk.temp_file)
                    except:
                        pass

    def _update_chunk_progress(self, chunk_index: int, progress: int):
        """更新分片下载进度"""
        chunk = self.task.chunks[chunk_index]
        chunk_size = chunk.end - chunk.start + 1
        chunk.downloaded = int(chunk_size * progress / 100)
        self.chunk_progress.emit(self.task_id, chunk_index, progress, 
                               self.chunk_threads[chunk_index].current_speed,
                               chunk.status)

    def _update_chunk_speed(self, chunk_index: int, speed: float):
        """更新分片下载速度"""
        self.chunk_progress.emit(self.task_id, chunk_index, 
                               int((self.task.chunks[chunk_index].downloaded / 
                                   (self.task.chunks[chunk_index].end - 
                                    self.task.chunks[chunk_index].start + 1)) * 100),
                               speed,
                               self.task.chunks[chunk_index].status)

    def _update_chunk_status(self, chunk_index: int, status: str):
        """更新分片状态"""
        self.task.chunks[chunk_index].status = status
        self.chunk_progress.emit(self.task_id, chunk_index,
                               int((self.task.chunks[chunk_index].downloaded /
                                   (self.task.chunks[chunk_index].end -
                                    self.task.chunks[chunk_index].start + 1)) * 100),
                               self.chunk_threads[chunk_index].current_speed,
                               status)

    def _show_notification(self, title: str, message: str):
        try:
            notification.notify(
                title=title,
                message=message,
                app_icon=None,
                timeout=10,
            )
        except Exception:
            pass

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False
        for thread in self.chunk_threads:
            thread.resume()

    def cancel(self):
        self.is_cancelled = True
        if self.is_paused:
            self.resume()

class DownloadProgress(QObject):
    """下载进度信号类"""
    progress = pyqtSignal(str, int)  # 任务ID, 进度
    status = pyqtSignal(str, str)    # 任务ID, 状态
    speed = pyqtSignal(str, float)   # 任务ID, 速度
    error = pyqtSignal(str, str)     # 任务ID, 错误信息
    completed = pyqtSignal(str)      # 任务ID

class Downloader:
    def __init__(self):
        self.progress_handler = DownloadProgress()
        self.tasks: Dict[str, DownloadTask] = {}
        self.workers: Dict[str, DownloadWorker] = {}
        self.global_speed_limit: float = 0.0  # KB/s
        self.proxy_config = ProxyConfig()
        self.default_thread_count: int = 8  # 默认线程数
    
    def set_default_thread_count(self, count: int) -> None:
        """设置默认线程数"""
        self.default_thread_count = max(1, min(32, count))  # 限制在1-32之间
    
    def add_task(self, task_id: str, url: str, save_path: str, thread_count: int = None) -> DownloadWorker:
        """添加下载任务"""
        task = DownloadTask(url=url, save_path=save_path)
        if thread_count is not None:
            task.thread_count = max(1, min(32, thread_count))
        else:
            task.thread_count = self.default_thread_count
        self.tasks[task_id] = task
        
        # 创建并启动下载线程
        worker = DownloadWorker(task_id, task, self.progress_handler, self.proxy_config)
        worker.speed_limit = self.global_speed_limit
        self.workers[task_id] = worker
        worker.start()
        return worker  # 返回worker实例
    
    def add_batch_tasks(self, urls: list[str], save_dir: str, thread_count: int = None) -> None:
        """批量添加下载任务"""
        for url in urls:
            filename = url.split('/')[-1]
            if not filename:
                filename = 'download_' + str(uuid.uuid4())[:8]
            save_path = os.path.join(save_dir, filename)
            self.add_task(str(uuid.uuid4()), url, save_path, thread_count)
    
    def set_speed_limit(self, speed: float) -> None:
        """设置全局限速（KB/s）"""
        self.global_speed_limit = speed
        for worker in self.workers.values():
            worker.speed_limit = speed
    
    def set_task_speed_limit(self, task_id: str, speed: float) -> None:
        """设置单个任务限速（KB/s）"""
        if task_id in self.workers:
            self.workers[task_id].speed_limit = speed
    
    def pause_task(self, task_id: str) -> None:
        """暂停下载任务"""
        if task_id in self.workers:
            worker = self.workers[task_id]
            worker.pause()
            self.tasks[task_id].status = "已暂停"
            self.progress_handler.status.emit(task_id, "已暂停")
    
    def resume_task(self, task_id: str) -> None:
        """恢复下载任务"""
        if task_id in self.workers:
            worker = self.workers[task_id]
            worker.resume()
            self.tasks[task_id].status = "下载中"
            self.progress_handler.status.emit(task_id, "下载中")
    
    def cancel_task(self, task_id: str) -> None:
        """取消下载任务"""
        if task_id in self.workers:
            self.workers[task_id].cancel()
            self.workers[task_id].wait()
            del self.workers[task_id]
            del self.tasks[task_id]
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """获取下载任务信息"""
        return self.tasks.get(task_id) 