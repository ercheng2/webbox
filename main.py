import webview
import json
import sys
import os
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

# ===== 悬浮按钮JS =====
FLOATING_BTN_JS = '''
(function() {
    if (document.getElementById('webbox_settings_btn')) return;
    var btn = document.createElement('div');
    btn.id = 'webbox_settings_btn';
    btn.innerHTML = '⚙️';
    btn.style.cssText = 'position:fixed;right:20px;bottom:20px;width:50px;height:50px;border-radius:50%;background:rgba(102,126,234,0.9);color:white;font-size:24px;display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:2147483647;box-shadow:0 4px 15px rgba(0,0,0,0.3);transition:transform 0.2s;';
    btn.onmouseenter = function() { this.style.transform = 'scale(1.1)'; };
    btn.onmouseleave = function() { this.style.transform = 'scale(1)'; };
    btn.onclick = function() { pywebview.api.open_settings(); };
    document.body.appendChild(btn);
})();
'''

# ===== 设置页面HTML =====
SETTINGS_HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: "Microsoft YaHei", Arial, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
}
.container {
    background: white;
    padding: 40px;
    border-radius: 20px;
    width: 100%;
    max-width: 500px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
h2 {
    margin: 0 0 30px;
    color: #333;
    text-align: center;
    font-size: 24px;
}
.field { margin-bottom: 24px; }
label {
    display: block;
    margin-bottom: 8px;
    color: #555;
    font-size: 14px;
    font-weight: 500;
}
input {
    width: 100%;
    padding: 14px 16px;
    border: 2px solid #e0e0e0;
    border-radius: 10px;
    font-size: 16px;
    transition: border-color 0.2s;
}
input:focus {
    border-color: #667eea;
    outline: none;
}
.hint {
    margin: 24px 0;
    padding: 14px 16px;
    background: #f8f9fa;
    border-radius: 10px;
    font-size: 14px;
    color: #666;
    line-height: 1.6;
}
.btn {
    width: 100%;
    padding: 16px;
    border: none;
    border-radius: 10px;
    font-size: 17px;
    font-weight: 600;
    cursor: pointer;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    transition: transform 0.1s, box-shadow 0.2s;
}
.btn:hover {
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}
.btn:active {
    transform: scale(0.98);
}
</style>
</head>
<body>
<div class="container">
    <h2>🌐 WebBox 设置</h2>
    <div class="field">
        <label>网页地址</label>
        <input type="text" id="urlInput" placeholder="请输入网址，如 www.baidu.com">
    </div>
    <div class="field">
        <label>窗口标题（可选）</label>
        <input type="text" id="titleInput" placeholder="WebBox">
    </div>
    <div class="hint">
        💡 提示：修改后点击"保存"即可刷新网页
    </div>
    <button class="btn" onclick="saveAndReload()">保存</button>
</div>
<script>
var urlInput = document.getElementById('urlInput');
var titleInput = document.getElementById('titleInput');

pywebview.api.get_config().then(function(config) {
    if (config.url) urlInput.value = config.url;
    if (config.title) titleInput.value = config.title;
    urlInput.focus();
    urlInput.select();
});

function saveAndReload() {
    var url = urlInput.value.trim();
    var title = titleInput.value.trim();
    
    if (!url) {
        alert('请输入网页地址');
        urlInput.focus();
        return;
    }
    
    pywebview.api.save_and_reload(url, title);
}

urlInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') saveAndReload();
});
titleInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') saveAndReload();
});
</script>
</body>
</html>'''

# ===== 浏览窗口API =====
class BrowseApi:
    def __init__(self):
        self.browse_window = None
    
    def set_window(self, win):
        self.browse_window = win
    
    def open_settings(self):
        api = SettingsApi()
        api.browse_window = self.browse_window
        settings_win = webview.create_window(
            '修改网址',
            html=SETTINGS_HTML,
            js_api=api,
            width=540,
            height=480,
            resizable=False
        )
        api.settings_window = settings_win

# ===== 设置窗口API =====
class SettingsApi:
    def __init__(self):
        self.settings_window = None
        self.browse_window = None
    
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
        
        # 关闭设置窗口
        if self.settings_window:
            self.settings_window.destroy()
        
        # 刷新浏览窗口
        if self.browse_window:
            self.browse_window.load_url(url)
        
        return {'ok': True}

# ===== 主程序 =====
def main():
    config = load_config()
    
    if config.get('url'):
        api = BrowseApi()
        browse_win = webview.create_window(
            config.get('title', 'WebBox'),
            config['url'],
            fullscreen=True,
            js_api=api
        )
        api.set_window(browse_win)
        # 页面加载完成后注入悬浮按钮
        def on_loaded():
            try:
                browse_win.evaluate_js(FLOATING_BTN_JS)
            except:
                pass
        browse_win.events.loaded += on_loaded
    else:
        api = SettingsApi()
        settings_win = webview.create_window(
            'WebBox 设置',
            html=SETTINGS_HTML,
            js_api=api,
            width=540,
            height=480,
            resizable=False
        )
        api.settings_window = settings_win
    
    webview.start()

if __name__ == '__main__':
    main()
