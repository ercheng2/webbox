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

log("=== WebBox 启动 ===")

try:
    # 在导入Qt之前设置环境变量，禁用GPU加速
    os.environ['QT_OPENGL'] = 'angle'
    os.environ['QT_QUICK_BACKEND'] = 'software'
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = '--disable-gpu --disable-gpu-compositing --software-rendering'
    
    log("设置OpenGL环境变量...")
    
    log("导入 PyQt5...")
    from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
    from PyQt5.QtCore import Qt
    log("PyQt5 导入成功")
    
    log("导入 WebEngine...")
    from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings
    log("WebEngine 导入成功")
    
    import json
    from pathlib import Path
    from PyQt5.QtCore import QUrl, QTimer
    from PyQt5.QtGui import QIcon
    
except Exception as e:
    log(f"导入失败: {e}\n{traceback.format_exc()}")
    raise

class WebBoxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log("初始化窗口...")
        
        try:
            self.setWindowTitle("WebBox v1.9")
            self.resize(1280, 720)
            
            # 先创建一个普通widget测试
            log("创建中央widget...")
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            
            # 创建WebEngineView
            log("创建WebEngineView...")
            self.web_view = QWebEngineView()
            layout.addWidget(self.web_view)
            
            # 配置设置
            log("配置settings...")
            settings = self.web_view.settings()
            settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
            
            # 加载默认网页
            log("加载网页...")
            self.web_view.setUrl(QUrl("https://www.baidu.com"))
            
            log("窗口初始化完成")
            
        except Exception as e:
            log(f"窗口初始化失败: {e}\n{traceback.format_exc()}")
            raise
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def closeEvent(self, event):
        log("退出WebBox")
        event.accept()


def main():
    try:
        log("main() 开始")
        
        # 启用高DPI
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # 使用软件渲染
        QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)
        
        log("创建 QApplication...")
        app = QApplication(sys.argv)
        log("QApplication 创建成功")
        
        log("创建窗口...")
        window = WebBoxWindow()
        window.show()
        log("窗口显示成功")
        
        log("进入主循环...")
        sys.exit(app.exec_())
        
    except Exception as e:
        log(f"main() 错误: {e}\n{traceback.format_exc()}")
        
        # 尝试用tkinter显示错误
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("WebBox 错误", f"启动失败:\n{e}\n\n请查看webbox.log文件")
        except:
            pass
        
        sys.exit(1)


if __name__ == '__main__':
    main()
