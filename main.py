"""
WebBox - 网页全屏盒子
使用PyQt5 QWebEngineView实现全屏网页展示
"""

import sys
import json
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer
from PyQt5.QtWebEngineCore import QWebEnginePage, QWebEngineProfile


class WebBoxPage(QWebEnginePage):
    """自定义网页页面，处理链接和新窗口"""
    
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self._parent_view = parent
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """处理导航请求"""
        if nav_type == QWebEnginePage.NavigationTypeLinkClicked:
            # 点击链接时在自己的页面加载
            self.setUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class WebBoxWindow(QMainWindow):
    """全屏网页盒子主窗口"""
    
    # 加载状态信号
    loading_started = pyqtSignal()
    loading_finished = pyqtSignal(bool)
    load_progress = pyqtSignal(int)
    
    def __init__(self, config_path: str = None):
        super().__init__()
        
        # 加载配置
        self.config = self._load_config(config_path)
        self.current_index = self.config.get('default_index', 0)
        self.websites = self.config.get('websites', [])
        
        # 创建设置文件路径
        if config_path:
            self.config_file = Path(config_path)
        else:
            self.config_file = Path(__file__).parent / 'webbox_config.json'
        
        # 初始化UI
        self._init_ui()
        
        # 连接信号
        self._connect_signals()
        
        # 加载初始网页
        self._load_current_website()
    
    def _load_config(self, config_path: str = None) -> dict:
        """加载配置文件"""
        if config_path:
            config_file = Path(config_path)
        else:
            config_file = Path(__file__).parent / 'webbox_config.json'
        
        default_config = {
            'websites': [{'name': '默认', 'url': 'https://example.com'}],
            'default_index': 0,
            'hotkeys': {
                'quit': ['Escape', 'Ctrl+Q'],
                'next': ['Ctrl+Right'],
                'prev': ['Ctrl+Left'],
                'reload': ['F5', 'Ctrl+R']
            },
            'window': {
                'fullscreen': True
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并配置
                    default_config.update(user_config)
                    return default_config
            except Exception as e:
                print(f"配置文件加载失败: {e}")
        
        return default_config
    
    def _init_ui(self):
        """初始化UI"""
        # 设置窗口属性
        self.setWindowFlags(
            Qt.FramelessWindowHint |  # 无边框
            Qt.WindowStaysOnTopHint |  # 始终顶层
            Qt.CustomizeWindowHint     # 自定义窗口
        )
        
        # 全屏显示
        if self.config.get('window', {}).get('fullscreen', True):
            self.showFullScreen()
        
        # 设置背景色
        self.setStyleSheet("background-color: #1a1a1a;")
        
        # 创建WebEngineView
        self.web_view = QWebEngineView(self)
        self.setCentralWidget(self.web_view)
        
        # 配置WebEngineSettings
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)
        
        # 支持触摸和滚动
        self.web_view.setAttribute(Qt.WA_AcceptTouchEvents, True)
        self.web_view.page().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self.web_view.page().setScrollBarPolicy(Qt.VentanaVertical, Qt.ScrollBarAutoHide)
        
        # 设置UserAgent
        self.web_view.page().profile().setHttpUserAgent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    
    def _connect_signals(self):
        """连接信号"""
        self.web_view.loadStarted.connect(self.on_load_started)
        self.web_view.loadFinished.connect(self.on_load_finished)
        self.web_view.loadProgress.connect(self.on_load_progress)
    
    def _load_current_website(self):
        """加载当前配置的网站"""
        if 0 <= self.current_index < len(self.websites):
            site = self.websites[self.current_index]
            url = site.get('url', '')
            if url:
                print(f"加载网站: {site.get('name', '未命名')} - {url}")
                self.web_view.setUrl(QUrl(url))
    
    def on_load_started(self):
        """页面开始加载"""
        print("开始加载...")
        self.loading_started.emit()
    
    def on_load_finished(self, success: bool):
        """页面加载完成"""
        if success:
            print("页面加载成功")
        else:
            print("页面加载失败")
            # 显示错误提示（短暂显示）
            QTimer.singleShot(3000, lambda: self.web_view.setHtml(
                '<html><body style="background:#1a1a1a;color:white;display:flex;'
                'justify-content:center;align-items:center;font-family:sans-serif;">'
                '<div style="text-align:center;"><h2>页面加载失败</h2>'
                '<p>请检查网络连接或配置文件中填写的网址</p></div></body></html>'
            ))
        self.loading_finished.emit(success)
    
    def on_load_progress(self, progress: int):
        """页面加载进度"""
        self.load_progress.emit(progress)
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        hotkeys = self.config.get('hotkeys', {})
        
        # 获取按下的键
        key = event.key()
        modifiers = event.modifiers()
        
        # ESC 或 Ctrl+Q 退出
        if key == Qt.Key_Escape or (key == Qt.Key_Q and modifiers == Qt.ControlModifier):
            self.close()
            return
        
        # Ctrl+Right 下一页
        if key == Qt.Key_Right and modifiers == Qt.ControlModifier:
            self.next_website()
            return
        
        # Ctrl+Left 上一页
        if key == Qt.Key_Left and modifiers == Qt.ControlModifier:
            self.prev_website()
            return
        
        # F5 或 Ctrl+R 刷新
        if key == Qt.Key_F5 or (key == Qt.Key_R and modifiers == Qt.ControlModifier):
            self.web_view.reload()
            return
        
        # F12 开发者工具
        if key == Qt.Key_F12:
            page = self.web_view.page()
            if hasattr(page, 'toggleDevTools'):
                page.toggleDevTools()
            return
        
        # 其他按键传递给网页
        super().keyPressEvent(event)
    
    def next_website(self):
        """切换到下一个网站"""
        if len(self.websites) > 1:
            self.current_index = (self.current_index + 1) % len(self.websites)
            self._load_current_website()
    
    def prev_website(self):
        """切换到上一个网站"""
        if len(self.websites) > 1:
            self.current_index = (self.current_index - 1) % len(self.websites)
            self._load_current_website()
    
    def switch_to_website(self, index: int):
        """切换到指定索引的网站"""
        if 0 <= index < len(self.websites):
            self.current_index = index
            self._load_current_website()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        print("退出WebBox")
        event.accept()


def main():
    """主函数"""
    # 启用高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 创建应用
    app = QApplication(sys.argv)
    app.setApplicationName("WebBox")
    app.setApplicationVersion("1.0.0")
    app.setQuitOnLastWindowClosed(True)
    
    # 设置应用样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1a1a1a;
        }
    """)
    
    # 创建主窗口
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    window = WebBoxWindow(config_path)
    
    # 显示窗口
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
