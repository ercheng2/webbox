import webview
import json
import sys
import os
from pathlib import Path

# ============ 配置管理 ============
def get_config_path():
    """配置文件保存到AppData目录"""
    if sys.platform == 'win32':
        config_dir = Path(os.environ.get('APPDATA', '.')) / 'WebBox'
    else:
        config_dir = Path.home() / '.webbox'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.json'

def load_config():
    config_file = get_config_path()
    default = {'url': 'https://www.baidu.com', 'title': 'WebBox'}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    default.update(data)
        except:
            pass
    return default

def save_config(data):
    config_file = get_config_path()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============ 全局状态 ============
CONFIG = load_config()
MAIN_WINDOW = None

# ============ 主窗口API ============
class MainApi:
    """主窗口的API，用于工具栏调用"""
    
    def open_settings(self):
        """打开设置窗口"""
        create_settings_window()
        return {'status': 'ok'}
    
    def reload_page(self):
        """刷新页面"""
        global CONFIG, MAIN_WINDOW
        CONFIG = load_config()
        if MAIN_WINDOW:
            MAIN_WINDOW.load_url(CONFIG['url'])
        return {'status': 'ok'}

# ============ 设置窗口API ============
class SettingsApi:
    """设置窗口的API"""
    
    def save_config(self, url, title):
        """保存配置并刷新主窗口"""
        global CONFIG, MAIN_WINDOW
        
        # 处理URL
        url = url.strip()
        if not url:
            url = 'https://www.baidu.com'
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        
        # 处理标题
        title = title.strip() or 'WebBox'
        
        # 保存配置
        CONFIG = {'url': url, 'title': title}
        save_config(CONFIG)
        
        # 刷新主窗口 - 这是关键！
        if MAIN_WINDOW:
            MAIN_WINDOW.title = title
            MAIN_WINDOW.load_url(url)
        
        return {'status': 'ok', 'url': url, 'title': title}
    
    def get_config(self):
        return CONFIG

# ============ 创建设置窗口 ============
def create_settings_window():
    global CONFIG
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>设置</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: "Microsoft YaHei", Arial, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{ 
            background: white; 
            padding: 32px; 
            border-radius: 16px; 
            width: 100%;
            max-width: 440px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h2 {{ 
            margin: 0 0 28px; 
            color: #333; 
            text-align: center; 
            font-size: 22px;
        }}
        .field {{ margin-bottom: 20px; }}
        label {{ 
            display: block; 
            margin-bottom: 8px; 
            color: #555; 
            font-size: 14px;
            font-weight: 500;
        }}
        input {{ 
            width: 100%; 
            padding: 12px 14px; 
            border: 2px solid #e0e0e0; 
            border-radius: 8px; 
            font-size: 15px;
            transition: border-color 0.2s;
        }}
        input:focus {{ 
            border-color: #667eea; 
            outline: none; 
        }}
        .buttons {{ 
            display: flex; 
            gap: 12px; 
            margin-top: 28px; 
        }}
        button {{ 
            flex: 1; 
            padding: 14px; 
            border: none; 
            border-radius: 8px; 
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s;
        }}
        button:active {{ transform: scale(0.98); }}
        .btn-save {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
        }}
        .btn-cancel {{ 
            background: #f0f0f0; 
            color: #666; 
        }}
        .tip {{ 
            margin-top: 20px; 
            padding: 12px; 
            background: #f8f9fa; 
            border-radius: 8px;
            font-size: 13px; 
            color: #666; 
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🌐 WebBox 设置</h2>
        <div class="field">
            <label>网页地址</label>
            <input type="text" id="urlInput" value="{CONFIG['url']}" placeholder="例如: www.baidu.com">
        </div>
        <div class="field">
            <label>窗口标题</label>
            <input type="text" id="titleInput" value="{CONFIG['title']}" placeholder="WebBox">
        </div>
        <div class="buttons">
            <button class="btn-save" onclick="saveSettings()">✓ 保存并刷新</button>
            <button class="btn-cancel" onclick="window.close()">取消</button>
        </div>
        <div class="tip">
            💡 网址可省略 https:// 前缀，保存后自动刷新
        </div>
    </div>
    <script>
        // 自动选中URL输入框
        var urlInput = document.getElementById('urlInput');
        urlInput.focus();
        urlInput.select();
        
        function saveSettings() {{
            var url = urlInput.value.trim();
            var title = document.getElementById('titleInput').value.trim();
            
            if (!url) {{
                alert('请输入网页地址');
                urlInput.focus();
                return;
            }}
            
            pywebview.api.save_config(url, title).then(function(result) {{
                // 保存成功，关闭设置窗口
                window.close();
            }});
        }}
        
        // 快捷键
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') saveSettings();
            if (e.key === 'Escape') window.close();
        }});
    </script>
</body>
</html>'''
    
    webview.create_window(
        'WebBox 设置',
        html=html,
        js_api=SettingsApi(),
        width=480,
        height=400,
        resizable=False,
        minimizable=False
    )

# ============ 创建工具栏 ============
def create_toolbar():
    toolbar_html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: rgba(40, 40, 50, 0.95); 
            font-family: Arial, sans-serif;
            overflow: hidden;
            user-select: none;
        }
        .toolbar {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            gap: 8px;
        }
        button {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            padding: 8px 14px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
            white-space: nowrap;
        }
        button:hover {
            background: rgba(255,255,255,0.2);
            border-color: rgba(255,255,255,0.3);
        }
        .label {
            color: rgba(255,255,255,0.5);
            font-size: 11px;
            margin-left: 8px;
        }
    </style>
</head>
<body>
    <div class="toolbar">
        <button onclick="openSettings()">⚙️ 设置</button>
        <button onclick="reloadPage()">🔄 刷新</button>
        <span class="label">WebBox 控制栏</span>
    </div>
    <script>
        function openSettings() {
            pywebview.api.open_settings();
        }
        function reloadPage() {
            pywebview.api.reload_page();
        }
    </script>
</body>
</html>'''
    
    webview.create_window(
        '',
        html=toolbar_html,
        js_api=MainApi(),
        width=220,
        height=40,
        frameless=True,
        always_on_top=True,
        x=10,
        y=10
    )

# ============ 主程序 ============
def main():
    global CONFIG, MAIN_WINDOW
    
    # 创建主窗口 - 直接加载网页
    MAIN_WINDOW = webview.create_window(
        title=CONFIG['title'],
        url=CONFIG['url'],
        fullscreen=True
    )
    
    # 创建悬浮工具栏
    create_toolbar()
    
    # 启动
    webview.start()

if __name__ == '__main__':
    main()
