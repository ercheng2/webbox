import webview
import json
import sys
import os
import threading
from pathlib import Path

# ===== 配置管理 =====
def get_config_path():
    if sys.platform == 'win32':
        config_dir = Path(os.environ.get('APPDATA', '.')) / 'WebBox'
    else:
        config_dir = Path.home() / '.webbox'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / 'config.json'

def load_config():
    config_file = get_config_path()
    default = {'url': '', 'title': 'WebBox', 'fullscreen': True}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get('url'):
                    if 'fullscreen' not in data:
                        data['fullscreen'] = True
                    return data
        except:
            pass
    return default

def save_config(data):
    config_file = get_config_path()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== 设置页面HTML =====
SETTINGS_HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: "Microsoft YaHei", Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
.container { background: white; padding: 40px; border-radius: 20px; width: 100%; max-width: 500px; box-shadow: 0 20px 60px rgba(0,0,0,0.2); }
h2 { margin: 0 0 30px; color: #333; text-align: center; font-size: 24px; }
.field { margin-bottom: 24px; }
label { display: block; margin-bottom: 8px; color: #555; font-size: 14px; font-weight: 500; }
input[type="text"] { width: 100%; padding: 14px 16px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; }
input[type="text"]:focus { border-color: #667eea; outline: none; }
.checkbox-field { display: flex; align-items: center; gap: 10px; }
.checkbox-field input[type="checkbox"] { width: 20px; height: 20px; cursor: pointer; }
.checkbox-field label { margin: 0; cursor: pointer; font-size: 15px; }
.hint { margin: 24px 0; padding: 14px 16px; background: #f8f9fa; border-radius: 10px; font-size: 14px; color: #666; }
.btn { width: 100%; padding: 16px; border: none; border-radius: 10px; font-size: 17px; font-weight: 600; cursor: pointer; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.btn:hover { box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }
</style>
</head>
<body>
<div class="container">
    <h2>🌐 WebBox 设置</h2>
    <div class="field">
        <label>网页地址</label>
        <input type="text" id="urlInput" placeholder="请输入网址">
    </div>
    <div class="field">
        <label>窗口标题（可选）</label>
        <input type="text" id="titleInput" placeholder="WebBox">
    </div>
    <div class="field checkbox-field">
        <input type="checkbox" id="fullscreenCheck" checked>
        <label for="fullscreenCheck">全屏模式（盖住任务栏）</label>
    </div>
    <div class="hint">
        💡 按 F1 可随时打开此设置窗口<br>
        • 全屏模式：窗口覆盖整个屏幕，包括任务栏<br>
        • 窗口模式：显示任务栏，方便切换应用
    </div>
    <button class="btn" onclick="saveAndReload()">保存</button>
</div>
<script>
var urlInput = document.getElementById('urlInput');
var titleInput = document.getElementById('titleInput');
var fullscreenCheck = document.getElementById('fullscreenCheck');

pywebview.api.get_config().then(function(c) {
    if (c.url) urlInput.value = c.url;
    if (c.title) titleInput.value = c.title;
    fullscreenCheck.checked = c.fullscreen !== false;
    urlInput.focus();
});

function saveAndReload() {
    var url = urlInput.value.trim();
    if (!url) { alert('请输入网址'); return; }
    pywebview.api.save_and_reload(url, titleInput.value.trim(), fullscreenCheck.checked);
}

urlInput.onkeydown = function(e) { if (e.key === 'Enter') saveAndReload(); };
titleInput.onkeydown = function(e) { if (e.key === 'Enter') saveAndReload(); };
</script>
</body>
</html>'''

# ===== 全局变量 =====
browse_window = None

# ===== API =====
class BrowseApi:
    def get_config(self):
        return load_config()
    
    def save_and_reload(self, url, title, fullscreen):
        global browse_window
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        config = {
            'url': url, 
            'title': title.strip() or 'WebBox',
            'fullscreen': fullscreen
        }
        save_config(config)
        if browse_window:
            browse_window.load_url(url)
            if fullscreen:
                browse_window.toggle_fullscreen()
        return {'ok': True}

class SettingsApi:
    def get_config(self):
        return load_config()
    
    def save_and_reload(self, url, title, fullscreen):
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        config = {
            'url': url, 
            'title': title.strip() or 'WebBox',
            'fullscreen': fullscreen
        }
        save_config(config)
        return {'ok': True}

# ===== 全局快捷键监听 =====
def start_hotkey_listener():
    try:
        import keyboard
        def open_settings():
            api = BrowseApi()
            webview.create_window('修改网址', html=SETTINGS_HTML, js_api=api, width=540, height=560, resizable=False)
        keyboard.add_hotkey('f1', open_settings)
        keyboard.wait()
    except Exception as e:
        print(f"快捷键监听失败: {e}")

# ===== 主程序 =====
def main():
    config = load_config()
    
    # 启动全局快捷键监听
    hotkey_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    hotkey_thread.start()
    
    if config.get('url'):
        api = BrowseApi()
        global browse_window
        fullscreen = config.get('fullscreen', True)
        browse_window = webview.create_window(
            config.get('title', 'WebBox'),
            config['url'],
            fullscreen=fullscreen,
            js_api=api
        )
        
        if not fullscreen:
            import ctypes
            user32 = ctypes.windll.user32
            screen_width = user32.GetSystemMetrics(0)
            screen_height = user32.GetSystemMetrics(1)
            browse_window.resize(screen_width, screen_height - 40)
            browse_window.move(0, 0)
    else:
        api = SettingsApi()
        webview.create_window('WebBox 设置', html=SETTINGS_HTML, js_api=api, width=540, height=560, resizable=False)
    
    webview.start()

if __name__ == '__main__':
    main()
