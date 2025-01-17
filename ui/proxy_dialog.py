from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QSpinBox, QCheckBox, QPushButton,
                             QFormLayout, QGroupBox)
from PyQt6.QtCore import Qt

class ProxyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("代理设置")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 代理组
        proxy_group = QGroupBox("HTTP/HTTPS 代理")
        proxy_layout = QFormLayout()
        
        # 启用代理复选框
        self.enable_proxy = QCheckBox("启用代理")
        self.enable_proxy.stateChanged.connect(self._on_proxy_enabled)
        proxy_layout.addRow(self.enable_proxy)
        
        # 代理服务器
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("例如：127.0.0.1")
        proxy_layout.addRow("服务器:", self.host_input)
        
        # 端口
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(8080)
        proxy_layout.addRow("端口:", self.port_input)
        
        # 认证组
        auth_group = QGroupBox("代理认证")
        auth_layout = QFormLayout()
        
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        auth_layout.addRow("用户名:", self.username_input)
        auth_layout.addRow("密码:", self.password_input)
        
        auth_group.setLayout(auth_layout)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        layout.addWidget(auth_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 初始状态
        self._on_proxy_enabled(False)
        self.enable_proxy.setChecked(False)
    
    def _on_proxy_enabled(self, enabled):
        """处理代理启用状态改变"""
        self.host_input.setEnabled(enabled)
        self.port_input.setEnabled(enabled)
        self.username_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
    
    def get_proxy_config(self) -> tuple[bool, str, int, str, str]:
        """获取代理配置"""
        return (
            self.enable_proxy.isChecked(),
            self.host_input.text().strip(),
            self.port_input.value(),
            self.username_input.text().strip(),
            self.password_input.text().strip()
        )
    
    def set_proxy_config(self, enabled: bool, host: str, port: int,
                        username: str, password: str):
        """设置代理配置"""
        self.enable_proxy.setChecked(enabled)
        self.host_input.setText(host)
        self.port_input.setValue(port)
        self.username_input.setText(username)
        self.password_input.setText(password) 