"""
WebBox - 网页全屏盒子
使用PyQt5 QWebEngineView实现全屏网页展示
"""

import sys
import json
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon

# WebEngine导入 - PyQt5 5.15+ 所有类都从QtWebEngineWidgets导入
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineSettings


class WebBoxPage(QWebEnginePage):
    """自定义网页页面，处理链接和新窗口"""
    
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self._parent_view = parent
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """处理导航请求"""
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            self.setUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class WebBoxWindow(QMainWindow):
    """全屏网页盒子主窗口"""
    
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal(bool)
    load_progress = pyqtSignal(int)
    
    def __init__(self, config_path: str = None):
        super().__init__()
        
        self.config = self._load_config(config_path)
        self.current_index = self.config.get('default_index', 0)
        self.websites = self.config.get('websites', [])
        
        if config_path:
            self.config_file = Path(config_path)
        else:
            self.config_file = self._get_config_path()
        
        self._init_ui()
        self._connect_signals()
        self._load_current_website()
    
    def _get_config_path(self):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent
        return base_path / 'webbox_config.json'
    
    def _load_config(self, config_path: str = None) -> dict:
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = self._get_config_path()
        
        default_config = {
            'websites': [{'name': '默认', 'url': 'https://www.baidu.com'}],
            'default_index': 0,
            'hotkeys': {
                'quit': ['Escape', 'Ctrl+Q'],
                'next': ['Ctrl+Right'],
                'prev': ['Ctrl+Left'],
                'reload': ['F5', 'Ctrl+R']
            },
            'window': {'fullscreen': True}
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"配置文件加载失败: {e}")
        
        return default_config
    
    def _get_resource_path(self, relative_path):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent
        return str(base_path / relative_path)
    
    def _init_ui(self):
        icon_path = self._get_resource_path('Kunzhancheng.ico')
        if Path(icon_path).exists():
            self.setWindowIcon(QIcon(icon_path))
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.CustomizeWindowHint
        )
        
        if self.config.get('window', {}).get('fullscreen', True):
            self.showFullScreen()
        
        self.setStyleSheet("background-color: #1a1a1a;")
        
        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)
        
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)
        
        self.web_view.setAttribute(Qt.WA_AcceptTouchEvents, True)
        
        profile = self.web_view.page().profile()
        profile.setHttpUserAgent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    
    def _connect_signals(self):
        self.web_view.loadStarted.connect(self.on_load_started)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.loadProgress.connect(self.on_load_progress)
    
    def _load_current_website(self):
        if 0 <= self.current_index < len(self.websites):
            site = self.websites[self.current_index]
            url = site.get('url', '')
            if url:
                print(f"加载网站: {site.get('name', '未命名')} - {url}")
                self.web_view.setUrl(QUrl(url))
    
    def on_load_started(self):
        print("开始加载...")
        self.loading_started.emit()
    
    def on_load_finished(self, success: bool):
        if success:
            print("页面加载成功")
        else:
            print("页面加载失败")
            QTimer.singleShot(3000, lambda: self.web_view.setHtml(
                '<html><body style="background:#1a1a1a;color:white;display:flex;'
                'justify-content:center;align-items:center;font-family:sans-serif;">'
                '<div style="text-align:center;"><h2>页面加载失败</h2>'
                '<p>请检查网络连接或配置文件中填写的网址</p></div></body></html>'
            ))
        self.loading_finished.emit(success)
    
    def on_load_progress(self, progress: int):
        self.load_progress.emit(progress)
    
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        if key == Qt.Key_Escape or (key == Qt.Key_Q and modifiers == Qt.ControlModifier):
            self.close()
            return
        
        if key == Qt.Key_Right and modifiers == Qt.ControlModifier:
            self.next_website()
            return
        
        if key == Qt.Key_Left and modifiers == Qt.ControlModifier:
            self.prev_website()
            return
        
        if key == Qt.Key_F5 or (key == Qt.Key_R and modifiers == Qt.ControlModifier):
            self.web_view.reload()
            return
        
        if key == Qt.Key_F12:
            page = self.web_view.page()
            if hasattr(page, 'toggleDevTools'):
                page.toggleDevTools()
            return
        
        super().keyPressEvent(event)
    
    def next_website(self):
        if len(self.websites) > 1:
            self.current_index = (self.current_index + 1) % len(self.websites)
            self._load_current_website()
    
    def prev_website(self):
        if len(self.websites) > 1:
            self.current_index = (self.current_index - 1) % len(self.websites)
            self._load_current_website()
    
    def switch_to_website(self, index: int):
        if 0 <= index < len(self.websites):
            self.current_index = index
            self._load_current_website()
    
    def closeEvent(self, event):
        print("退出WebBox")
        event.accept()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("WebBox")
    app.setApplicationVersion("1.5.0")
    app.setQuitOnLastWindowClosed(True)
    
    app.setStyleSheet("QMainWindow { background-color: #1a1a1a; }")
    
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    window = WebBoxWindow(config_path)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
