"""
WebBox - 网页全屏盒子
"""

import sys
import os
import traceback
from datetime import datetime

# 写日志函数
def log(msg):
    try:
        if getattr(sys, 'frozen', False):
            log_path = os.path.join(os.path.dirname(sys.executable), 'webbox.log')
        else:
            log_path = os.path.join(os.path.dirname(__file__), 'webbox.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now()}] {msg}\n")
    except:
        pass

log("=== WebBox v2.0 启动 ===")

try:
    # WebEngine环境设置
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu --no-sandbox --disable-software-rasterizer'
    
    log("导入 PyQt5...")
    from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
    from PyQt5.QtCore import Qt, QUrl
    log("PyQt5 导入成功")
    
    log("导入 WebEngineWidgets...")
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    log("WebEngineWidgets 导入成功")
    
    from PyQt5.QtGui import QIcon
    
except Exception as e:
    log(f"导入失败: {e}\n{traceback.format_exc()}")
    raise

class WebBoxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log("WebBoxWindow.__init__ 开始")
        
        self.setWindowTitle("WebBox v2.0")
        self.resize(1024, 768)
        self.setStyleSheet("background-color: white;")
        
        log("创建中央widget")
        central = QWidget()
        self.setCentralWidget(central)
        self.layout = QVBoxLayout(central)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        log("创建QWebEngineView")
        self.web_view = QWebEngineView()
        self.layout.addWidget(self.web_view)
        
        log("配置WebEngineSettings")
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        
        log("加载URL")
        self.web_view.setUrl(QUrl("https://www.baidu.com"))
        
        log("WebBoxWindow.__init__ 完成")
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        log("关闭窗口")
        event.accept()


def main():
    try:
        log("main() 开始")
        
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        log("创建QApplication")
        app = QApplication(sys.argv)
        
        log("创建WebBoxWindow")
        window = WebBoxWindow()
        
        log("显示窗口")
        window.show()
        
        log("进入事件循环")
        ret = app.exec_()
        log(f"事件循环结束: {ret}")
        sys.exit(ret)
        
    except Exception as e:
        log(f"main错误: {e}\n{traceback.format_exc()}")
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("WebBox错误", f"{e}")
        except:
            pass
        sys.exit(1)


if __name__ == '__main__':
    main()
