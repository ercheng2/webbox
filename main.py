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
    default = {'url': '', 'title': 'WebBox'}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get('url'):
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
input { width: 100%; padding: 14px 16px; border: 2px solid #e0e0e0; border-radius: 10px; font-size: 16px; }
input:focus { border-color: #667eea; outline: none; }
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
    <div class="hint">💡 按 F1 可随时打开此设置窗口</div>
    <button class="btn" onclick="saveAndReload()">保存</button>
</div>
<script>
var urlInput = document.getElementById('urlInput');
var titleInput = document.getElementById('titleInput');
pywebview.api.get_config().then(function(c) {
    if (c.url) urlInput.value = c.url;
    if (c.title) titleInput.value = c.title;
    urlInput.focus();
});
function saveAndReload() {
    var url = urlInput.value.trim();
    if (!url) { alert('请输入网址'); return; }
    pywebview.api.save_and_reload(url, titleInput.value.trim());
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
    
    def save_and_reload(self, url, title):
        global browse_window
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        config = {'url': url, 'title': title.strip() or 'WebBox'}
        save_config(config)
        if browse_window:
            browse_window.load_url(url)
        return {'ok': True}

class SettingsApi:
    def get_config(self):
        return load_config()
    
    def save_and_reload(self, url, title):
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        config = {'url': url, 'title': title.strip() or 'WebBox'}
        save_config(config)
        return {'ok': True}

# ===== 全局快捷键监听 =====
def start_hotkey_listener():
    try:
        import keyboard
        def open_settings():
            api = BrowseApi()
            webview.create_window('修改网址', html=SETTINGS_HTML, js_api=api, width=540, height=480, resizable=False)
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
        browse_window = webview.create_window(
            config.get('title', 'WebBox'),
            config['url'],
            fullscreen=True,
            js_api=api
        )
    else:
        api = SettingsApi()
        webview.create_window('WebBox 设置', html=SETTINGS_HTML, js_api=api, width=540, height=480, resizable=False)
    
    webview.start()

if __name__ == '__main__':
    main()
