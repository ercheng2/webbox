import webview
import json
import sys
import threading
from pathlib import Path
from pynput import keyboard

def get_config_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / 'webbox_config.json'
    return Path(__file__).parent / 'webbox_config.json'

def load_config():
    config_file = get_config_path()
    default = {'url': 'https://www.baidu.com', 'title': 'WebBox'}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                default.update(json.load(f))
        except:
            pass
    return default

def save_config(config):
    config_file = get_config_path()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

class Api:
    def __init__(self):
        self.config = load_config()
    
    def get_config(self):
        return self.config
    
    def save_config(self, url, title):
        self.config['url'] = url
        self.config['title'] = title
        save_config(self.config)
        return {'status': 'ok', 'url': url, 'title': title}
    
    def reload_url(self, url):
        return {'status': 'ok'}

def create_settings_html(config):
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>设置</title>
        <style>
            body {{
                font-family: Microsoft YaHei, Arial, sans-serif;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                max-width: 400px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h2 {{
                margin: 0 0 20px 0;
                color: #333;
                text-align: center;
            }}
            .form-group {{
                margin-bottom: 15px;
            }}
            label {{
                display: block;
                margin-bottom: 5px;
                color: #666;
            }}
            input {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-sizing: border-box;
                font-size: 14px;
            }}
            input:focus {{
                border-color: #4a9eff;
                outline: none;
            }}
            .buttons {{
                margin-top: 20px;
                display: flex;
                gap: 10px;
            }}
            button {{
                flex: 1;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }}
            .btn-save {{
                background: #4a9eff;
                color: white;
            }}
            .btn-save:hover {{
                background: #3a8eef;
            }}
            .btn-cancel {{
                background: #e0e0e0;
                color: #666;
            }}
            .btn-cancel:hover {{
                background: #d0d0d0;
            }}
            .tip {{
                margin-top: 15px;
                padding: 10px;
                background: #fffbe6;
                border-radius: 4px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>WebBox 设置</h2>
            <div class="form-group">
                <label>网页地址 (URL)</label>
                <input type="text" id="urlInput" value="{config['url']}" placeholder="https://example.com">
            </div>
            <div class="form-group">
                <label>窗口标题</label>
                <input type="text" id="titleInput" value="{config['title']}" placeholder="WebBox">
            </div>
            <div class="buttons">
                <button class="btn-save" onclick="saveSettings()">保存</button>
                <button class="btn-cancel" onclick="window.close()">取消</button>
            </div>
            <div class="tip">
                提示：按 V 键可随时打开此设置窗口
            </div>
        </div>
        <script>
            function saveSettings() {{
                var url = document.getElementById('urlInput').value;
                var title = document.getElementById('titleInput').value;
                pywebview.api.save_config(url, title).then(function(response) {{
                    window.close();
                }});
            }}
        </script>
    </body>
    </html>
    '''

# 全局变量
main_window = None
settings_window = None
api = None

def on_key_press(key):
    """监听V键"""
    global main_window, settings_window, api
    try:
        if key.char and key.char.lower() == 'v':
            # 打开设置窗口
            config = load_config()
            html = create_settings_html(config)
            settings_window = webview.create_window(
                '设置',
                html=html,
                js_api=api,
                width=450,
                height=350,
                resizable=False
            )
    except AttributeError:
        pass

def main():
    global main_window, api
    
    config = load_config()
    api = Api()
    
    # 创建主窗口 - 直接加载URL
    main_window = webview.create_window(
        title=config.get('title', 'WebBox'),
        url=config.get('url', 'https://www.baidu.com'),
        fullscreen=True
    )
    
    # 启动全局热键监听（在后台线程）
    listener = keyboard.Listener(on_press=on_key_press)
    listener.daemon = True
    listener.start()
    
    webview.start()

if __name__ == '__main__':
    main()
