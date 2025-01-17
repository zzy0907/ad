from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                             QProgressBar, QLineEdit, QFileDialog, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHBoxLayout, QHeaderView,
                             QLabel, QSpinBox, QStyle, QMenu, QMenuBar, QStatusBar,
                             QStyleFactory, QDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QPalette, QColor, QActionGroup
from utils.downloader import Downloader
import uuid
from datetime import datetime
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多线程下载器")
        self.setMinimumSize(1000, 600)
        
        # 设置应用样式
        self.setStyle(QStyleFactory.create("Fusion"))
        self.is_dark_theme = True
        self._set_dark_theme()
        
        # 创建下载器实例
        self.downloader = Downloader()
        self.downloader.progress_handler.progress.connect(self.update_progress)
        self.downloader.progress_handler.status.connect(self.update_status)
        self.downloader.progress_handler.speed.connect(self.update_speed)
        self.downloader.progress_handler.completed.connect(self.download_completed)
        self.downloader.progress_handler.error.connect(self.show_error)
        
        # 创建菜单栏
        self._create_menu_bar()
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建顶部控制区域
        control_layout = QHBoxLayout()
        
        # URL输入框
        url_layout = QVBoxLayout()
        url_label = QLabel("下载地址:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入URL或将多个URL粘贴到此处（每行一个）")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        control_layout.addLayout(url_layout, stretch=4)
        
        # 限速控制
        speed_layout = QVBoxLayout()
        speed_label = QLabel("限速 (KB/s):")
        self.speed_limit = QSpinBox()
        self.speed_limit.setRange(0, 100000)
        self.speed_limit.setValue(0)
        self.speed_limit.setSpecialValueText("不限速")
        self.speed_limit.valueChanged.connect(self.set_speed_limit)
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_limit)
        control_layout.addLayout(speed_layout, stretch=1)
        
        # 下载按钮
        btn_layout = QVBoxLayout()
        btn_label = QLabel("")  # 占位对齐
        self.download_btn = QPushButton("添加下载")
        self.download_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.download_btn.clicked.connect(self.add_download)
        btn_layout.addWidget(btn_label)
        btn_layout.addWidget(self.download_btn)
        control_layout.addLayout(btn_layout, stretch=1)
        
        main_layout.addLayout(control_layout)
        
        # 创建下载列表
        self.download_table = QTableWidget()
        self.download_table.setColumnCount(7)
        self.download_table.setHorizontalHeaderLabels(["文件名", "大小", "进度", "状态", "速度", "操作", "ID"])
        self.download_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.download_table.setColumnHidden(6, True)  # 隐藏ID列
        self.download_table.setAlternatingRowColors(True)
        main_layout.addWidget(self.download_table)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
    
    def _create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 批量下载动作
        batch_action = QAction("批量下载", self)
        batch_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogStart))
        batch_action.triggered.connect(self.batch_download)
        file_menu.addAction(batch_action)
        
        file_menu.addSeparator()
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        
        # 线程设置动作
        thread_action = QAction("线程设置", self)
        thread_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_CommandLink))
        thread_action.triggered.connect(self.show_thread_settings)
        settings_menu.addAction(thread_action)
        
        # 限速设置动作
        speed_action = QAction("限速设置", self)
        speed_action.triggered.connect(lambda: self.speed_limit.setFocus())
        settings_menu.addAction(speed_action)
        
        # 代理设置动作
        proxy_action = QAction("代理设置", self)
        proxy_action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon))
        proxy_action.triggered.connect(self.show_proxy_settings)
        settings_menu.addAction(proxy_action)
        
        # 主题菜单
        theme_menu = settings_menu.addMenu("主题设置")
        theme_menu.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon))
        
        # 深色主题动作
        dark_action = QAction("深色主题", self)
        dark_action.setCheckable(True)
        dark_action.setChecked(self.is_dark_theme)
        dark_action.triggered.connect(lambda: self.switch_theme(True))
        theme_menu.addAction(dark_action)
        
        # 浅色主题动作
        light_action = QAction("浅色主题", self)
        light_action.setCheckable(True)
        light_action.setChecked(not self.is_dark_theme)
        light_action.triggered.connect(lambda: self.switch_theme(False))
        theme_menu.addAction(light_action)
        
        # 将主题动作添加到动作组
        theme_group = QActionGroup(self)
        theme_group.addAction(dark_action)
        theme_group.addAction(light_action)
        theme_group.setExclusive(True)
    
    def _set_dark_theme(self):
        """设置深色主题"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.setPalette(palette)
    
    def _set_light_theme(self):
        """设置浅色主题"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        self.setPalette(palette)
    
    def switch_theme(self, is_dark: bool):
        """切换主题"""
        self.is_dark_theme = is_dark
        if is_dark:
            self._set_dark_theme()
            self.statusBar.showMessage("已切换到深色主题")
        else:
            self._set_light_theme()
            self.statusBar.showMessage("已切换到浅色主题")
    
    def add_download(self):
        """添加新的下载任务"""
        urls = self.url_input.text().strip().split('\n')
        if not urls or not urls[0]:
            QMessageBox.warning(self, "警告", "请输入下载地址")
            return
        
        if len(urls) > 1:
            # 批量下载
            save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
            if save_dir:
                self.downloader.add_batch_tasks(urls, save_dir)
                self.url_input.clear()
                self.statusBar.showMessage(f"已添加 {len(urls)} 个下载任务")
        else:
            # 单个下载
            url = urls[0]
            # 从URL中获取文件名
            filename = url.split('/')[-1]
            if not filename:
                filename = 'download_' + str(uuid.uuid4())[:8]
            
            # 获取文件扩展名（如果有）
            ext = os.path.splitext(filename)[1]
            
            # 选择保存位置，使用URL中的文件名作为默认名称
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "选择保存位置",
                os.path.join(os.path.expanduser("~"), "Downloads", filename),  # 默认保存到下载文件夹
                f"所有文件 (*{ext} *.*)" if ext else "所有文件 (*.*)"
            )
            
            if save_path:
                self._add_task_to_table(url, save_path)
                self.url_input.clear()
                self.statusBar.showMessage("已添加下载任务")
    
    def batch_download(self):
        """批量下载"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择URL列表文件", "", "文本文件 (*.txt)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                if urls:
                    save_dir = QFileDialog.getExistingDirectory(self, "选择保存目录")
                    if save_dir:
                        self.downloader.add_batch_tasks(urls, save_dir)
                        self.statusBar.showMessage(f"已添加 {len(urls)} 个下载任务")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"读取文件失败：{str(e)}")
    
    def _add_task_to_table(self, url: str, save_path: str):
        """添加任务到下载列表"""
        task_id = str(uuid.uuid4())
        
        # 添加到下载列表
        row_position = self.download_table.rowCount()
        self.download_table.insertRow(row_position)
        
        # 设置文件名
        filename = os.path.basename(save_path)
        self.download_table.setItem(row_position, 0, QTableWidgetItem(filename))
        
        # 设置初始状态
        self.download_table.setItem(row_position, 1, QTableWidgetItem("计算中"))
        self.download_table.setItem(row_position, 2, QTableWidgetItem("0%"))
        self.download_table.setItem(row_position, 3, QTableWidgetItem("等待中"))
        self.download_table.setItem(row_position, 4, QTableWidgetItem("0 KB/s"))
        
        # 添加控制按钮
        control_widget = QWidget()
        control_layout = QHBoxLayout(control_widget)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建暂停按钮
        pause_btn = QPushButton("⏸️ 暂停")
        pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        pause_btn.clicked.connect(lambda: self.toggle_pause(task_id))
        pause_btn.setProperty("task_id", task_id)
        
        # 创建详情按钮
        detail_btn = QPushButton("📊 详情")
        detail_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
        """)
        detail_btn.clicked.connect(lambda: self.show_task_detail(task_id))
        
        # 创建取消按钮
        cancel_btn = QPushButton("❌ 取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        cancel_btn.clicked.connect(lambda: self.cancel_download(task_id))
        
        control_layout.addWidget(pause_btn)
        control_layout.addWidget(detail_btn)
        control_layout.addWidget(cancel_btn)
        self.download_table.setCellWidget(row_position, 5, control_widget)
        
        # 保存任务ID
        self.download_table.setItem(row_position, 6, QTableWidgetItem(task_id))
        
        # 开始下载
        worker = self.downloader.add_task(task_id, url, save_path)
        worker.chunk_progress.connect(lambda tid, idx, prog, spd, st: 
            self.update_chunk_progress(tid, idx, prog, spd, st))

    def show_task_detail(self, task_id: str):
        """显示任务详情对话框"""
        task = self.downloader.get_task(task_id)
        if not task:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("下载详情")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        layout = QVBoxLayout(dialog)
        
        # 创建线程状态表格
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["线程", "进度", "速度", "状态"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(task.chunks))
        table.setAlternatingRowColors(True)  # 设置交替行颜色
        
        # 设置表格样式
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d3d3d3;
                border: 1px solid #d3d3d3;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #d3d3d3;
                font-weight: bold;
            }
        """)
        
        # 保存表格引用以便更新
        task.detail_table = table
        
        # 初始化表格数据
        for i, chunk in enumerate(task.chunks):
            # 线程列
            thread_item = QTableWidgetItem(f"线程 {i+1}")
            thread_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 0, thread_item)
            
            # 进度列
            progress = int((chunk.downloaded / (chunk.end - chunk.start + 1)) * 100)
            progress_item = QTableWidgetItem(f"{progress}%")
            progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 1, progress_item)
            
            # 速度列
            speed_item = QTableWidgetItem("0 KB/s")
            speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, 2, speed_item)
            
            # 状态列
            status_item = QTableWidgetItem(chunk.status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_status_color(status_item, chunk.status)
            table.setItem(i, 3, status_item)
        
        layout.addWidget(table)
        
        # 添加关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(dialog.close)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        dialog.show()
    
    def _set_status_color(self, item: QTableWidgetItem, status: str):
        """设置状态颜色"""
        if status == "下载中":
            item.setForeground(QColor(0, 128, 0))  # 绿色
        elif status == "已暂停":
            item.setForeground(QColor(128, 128, 0))  # 黄色
        elif status == "已完成":
            item.setForeground(QColor(0, 0, 255))  # 蓝色
        elif status == "错误":
            item.setForeground(QColor(255, 0, 0))  # 红色
    
    def update_chunk_progress(self, task_id: str, chunk_index: int, progress: int, speed: float, status: str):
        """更新线程进度"""
        task = self.downloader.get_task(task_id)
        if not task or not hasattr(task, 'detail_table'):
            return
        
        table = task.detail_table
        if not table or chunk_index >= table.rowCount():
            return
        
        # 更新进度
        progress_item = QTableWidgetItem(f"{progress}%")
        progress_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(chunk_index, 1, progress_item)
        
        # 更新速度
        speed_item = QTableWidgetItem(f"{speed:.1f} KB/s")
        speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(chunk_index, 2, speed_item)
        
        # 更新状态
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._set_status_color(status_item, status)
        table.setItem(chunk_index, 3, status_item)
    
    def set_speed_limit(self, speed: int):
        """设置下载限速"""
        self.downloader.set_speed_limit(float(speed))
        if speed == 0:
            self.statusBar.showMessage("已取消限速")
        else:
            self.statusBar.showMessage(f"已设置限速：{speed} KB/s")
    
    def find_row_by_task_id(self, task_id: str) -> int:
        """根据任务ID查找对应的行号"""
        for row in range(self.download_table.rowCount()):
            if self.download_table.item(row, 6).text() == task_id:
                return row
        return -1
    
    def update_progress(self, task_id: str, progress: int):
        """更新进度"""
        row = self.find_row_by_task_id(task_id)
        if row >= 0:
            self.download_table.setItem(row, 2, QTableWidgetItem(f"{progress}%"))
    
    def update_status(self, task_id: str, status: str):
        """更新状态"""
        row = self.find_row_by_task_id(task_id)
        if row >= 0:
            self.download_table.setItem(row, 3, QTableWidgetItem(status))
            
            # 更新暂停/继续按钮文本和样式
            control_widget = self.download_table.cellWidget(row, 5)
            if not control_widget:
                return
                
            pause_btn = control_widget.layout().itemAt(0).widget()
            if status == "已暂停":
                pause_btn.setText("▶️ 继续")
                pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 3px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #F57C00;
                    }
                """)
            elif status == "下载中":
                pause_btn.setText("⏸️ 暂停")
                pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2196F3;
                        color: white;
                        border: none;
                        padding: 5px 10px;
                        border-radius: 3px;
                        min-width: 80px;
                    }
                    QPushButton:hover {
                        background-color: #1976D2;
                    }
                """)
    
    def update_speed(self, task_id: str, speed: float):
        """更新下载速度"""
        row = self.find_row_by_task_id(task_id)
        if row >= 0:
            speed_text = f"{speed:.1f} KB/s"
            self.download_table.setItem(row, 4, QTableWidgetItem(speed_text))
            
            # 更新文件大小
            task = self.downloader.get_task(task_id)
            if task and task.total_size > 0:
                size_text = self._format_size(task.total_size)
                self.download_table.setItem(row, 1, QTableWidgetItem(size_text))
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def toggle_pause(self, task_id: str):
        """切换暂停/继续状态"""
        task = self.downloader.get_task(task_id)
        if not task:
            return
            
        row = self.find_row_by_task_id(task_id)
        if row < 0:
            return
            
        control_widget = self.download_table.cellWidget(row, 5)
        pause_btn = control_widget.layout().itemAt(0).widget()
        current_status = self.download_table.item(row, 3).text()
        
        if current_status == "已暂停":
            # 当前是暂停状态，需要继续下载
            self.downloader.resume_task(task_id)
            pause_btn.setText("⏸️ 暂停")
            pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            self.download_table.setItem(row, 3, QTableWidgetItem("下载中"))
            self.statusBar.showMessage("继续下载")
        else:
            # 当前是下载状态，需要暂停
            self.downloader.pause_task(task_id)
            pause_btn.setText("▶️ 继续")
            pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    padding: 5px 10px;
                    border-radius: 3px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            self.download_table.setItem(row, 3, QTableWidgetItem("已暂停"))
            self.statusBar.showMessage("已暂停下载")
    
    def cancel_download(self, task_id: str):
        """取消下载"""
        row = self.find_row_by_task_id(task_id)
        if row >= 0:
            self.downloader.cancel_task(task_id)
            self.download_table.removeRow(row)
            self.statusBar.showMessage("已取消下载任务")
    
    def download_completed(self, task_id: str):
        """下载完成的处理函数"""
        row = self.find_row_by_task_id(task_id)
        if row >= 0:
            self.download_table.setItem(row, 3, QTableWidgetItem("已完成"))
            self.download_table.setItem(row, 4, QTableWidgetItem("--"))
            
            # 禁用控制按钮
            control_widget = self.download_table.cellWidget(row, 5)
            for i in range(control_widget.layout().count()):
                control_widget.layout().itemAt(i).widget().setEnabled(False)
            
            self.statusBar.showMessage("下载完成")
    
    def show_error(self, task_id: str, message: str):
        """显示错误信息"""
        row = self.find_row_by_task_id(task_id)
        if row >= 0:
            self.download_table.setItem(row, 3, QTableWidgetItem("错误"))
            self.download_table.setItem(row, 4, QTableWidgetItem("--"))
            QMessageBox.critical(self, "错误", f"下载失败：{message}")
            self.statusBar.showMessage("下载失败")
    
    def show_proxy_settings(self):
        """显示代理设置对话框"""
        from ui.proxy_dialog import ProxyDialog
        dialog = ProxyDialog(self)
        if dialog.exec():
            enabled, host, port, username, password = dialog.get_proxy_config()
            self.downloader.set_proxy(enabled, host, port, username, password)
            
            if enabled:
                self.statusBar.showMessage(f"已启用代理：{host}:{port}")
            else:
                self.statusBar.showMessage("已禁用代理")
    
    def show_thread_settings(self):
        """显示线程设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("线程设置")
        dialog.setModal(True)
        
        layout = QVBoxLayout(dialog)
        
        # 线程数设置
        thread_layout = QHBoxLayout()
        thread_label = QLabel("下载线程数:")
        thread_spinbox = QSpinBox()
        thread_spinbox.setRange(1, 32)
        thread_spinbox.setValue(self.downloader.default_thread_count)
        thread_spinbox.setToolTip("设置每个任务的下载线程数（1-32）")
        thread_layout.addWidget(thread_label)
        thread_layout.addWidget(thread_spinbox)
        layout.addLayout(thread_layout)
        
        # 说明文本
        info_label = QLabel("提示：线程数越多，下载速度可能越快，但也会占用更多系统资源。\n建议根据网络状况和系统配置调整，一般4-16个线程即可。")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(dialog.reject)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        if dialog.exec():
            thread_count = thread_spinbox.value()
            self.downloader.set_default_thread_count(thread_count)
            self.statusBar.showMessage(f"已设置下载线程数：{thread_count}") 