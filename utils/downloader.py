import requests
from typing import Callable
from PyQt6.QtCore import QObject, pyqtSignal

class DownloadProgress(QObject):
    """下载进度信号类"""
    progress = pyqtSignal(int)  # 进度信号
    completed = pyqtSignal()    # 完成信号
    error = pyqtSignal(str)     # 错误信号

class Downloader:
    def __init__(self):
        self.progress_handler = DownloadProgress()
    
    def download(self, url: str, save_path: str) -> None:
        """
        下载文件
        :param url: 下载地址
        :param save_path: 保存路径
        """
        try:
            # 发送请求并获取响应
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            
            # 如果文件大小为0，发出错误信号
            if total_size == 0:
                self.progress_handler.error.emit("无法获取文件大小")
                return
            
            # 写入文件并更新进度
            downloaded_size = 0
            chunk_size = 1024  # 1KB
            
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)
                        progress = int((downloaded_size / total_size) * 100)
                        self.progress_handler.progress.emit(progress)
            
            # 发送完成信号
            self.progress_handler.completed.emit()
            
        except requests.RequestException as e:
            # 发送错误信号
            self.progress_handler.error.emit(str(e)) 