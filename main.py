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

# ===== API =====
class SettingsApi:
    def __init__(self):
        self.settings_window = None
    
    def set_window(self, win):
        self.settings_window = win
    
    def get_config(self):
        return load_config()
    
    def start_browse(self, url, title):
        """保存配置并打开网页"""
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        
        # 自动添加https
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        
        # 保存配置
        config = {
            'url': url,
            'title': title.strip() or 'WebBox'
        }
        save_config(config)
        
        # 隐藏设置窗口
        if self.settings_window:
            self.settings_window.hide()
        
        # 打开全屏网页
        webview.create_window(config['title'], url, fullscreen=True)
        
        return {'ok': True}

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
    <h2>🌐 WebBox 网页盒子</h2>
    <div class="field">
        <label>网页地址</label>
        <input type="text" id="urlInput" placeholder="请输入网址，如 www.baidu.com">
    </div>
    <div class="field">
        <label>窗口标题（可选）</label>
        <input type="text" id="titleInput" placeholder="WebBox">
    </div>
    <div class="hint">
        💡 提示：<br>
        • 网址可省略 https:// 前缀<br>
        • 点击"开始浏览"后会全屏显示网页<br>
        • 网址会自动保存，下次启动直接打开
    </div>
    <button class="btn" onclick="startBrowse()">开始浏览</button>
</div>
<script>
var urlInput = document.getElementById('urlInput');
var titleInput = document.getElementById('titleInput');

// 加载已保存的配置
pywebview.api.get_config().then(function(config) {
    if (config.url) urlInput.value = config.url;
    if (config.title) titleInput.value = config.title;
    urlInput.focus();
    urlInput.select();
});

function startBrowse() {
    var url = urlInput.value.trim();
    var title = titleInput.value.trim();
    
    if (!url) {
        alert('请输入网页地址');
        urlInput.focus();
        return;
    }
    
    pywebview.api.start_browse(url, title);
}

// 回车键提交
urlInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') startBrowse();
});
titleInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') startBrowse();
});
</script>
</body>
</html>'''

# ===== 主程序 =====
def main():
    config = load_config()
    
    # 有配置，直接打开全屏网页
    if config.get('url'):
        webview.create_window(config.get('title', 'WebBox'), config['url'], fullscreen=True)
    else:
        # 没配置，显示设置窗口
        api = SettingsApi()
        settings_win = webview.create_window(
            'WebBox 设置',
            html=SETTINGS_HTML,
            js_api=api,
            width=540,
            height=480,
            resizable=False
        )
        api.set_window(settings_win)
    
    webview.start()

if __name__ == '__main__':
    main()
