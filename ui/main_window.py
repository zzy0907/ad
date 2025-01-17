from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                             QProgressBar, QLineEdit, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from utils.downloader import Downloader

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("下载器")
        self.setMinimumSize(800, 600)
        
        # 创建下载器实例
        self.downloader = Downloader()
        self.downloader.progress_handler.progress.connect(self.update_progress)
        self.downloader.progress_handler.completed.connect(self.download_completed)
        self.downloader.progress_handler.error.connect(self.show_error)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 添加URL输入框
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("请输入下载地址")
        layout.addWidget(self.url_input)
        
        # 添加下载按钮
        self.download_btn = QPushButton("开始下载")
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)
    
    def start_download(self):
        """开始下载的处理函数"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入下载地址")
            return
        
        # 选择保存位置
        save_path, _ = QFileDialog.getSaveFileName(
            self, "选择保存位置", "", "所有文件 (*.*)"
        )
        
        if save_path:
            self.download_btn.setEnabled(False)
            self.progress_bar.setValue(0)
            # 开始下载
            self.downloader.download(url, save_path)
    
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
    
    def download_completed(self):
        """下载完成的处理函数"""
        self.download_btn.setEnabled(True)
        QMessageBox.information(self, "提示", "下载完成！")
    
    def show_error(self, message):
        """显示错误信息"""
        self.download_btn.setEnabled(True)
        QMessageBox.critical(self, "错误", f"下载失败：{message}") 