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

# ===== 拦截外链的JS代码 =====
INTERCEPT_LINKS_JS = '''
(function() {
    // 拦截所有点击事件，防止跳转到外部浏览器
    document.addEventListener('click', function(e) {
        var target = e.target;
        // 向上查找A标签
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (target && target.tagName === 'A') {
            var href = target.getAttribute('href');
            if (href && !href.startsWith('javascript:') && !href.startsWith('#') && !href.startsWith('mailto:')) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                // 强制在当前窗口打开
                target.target = '_self';
                window.location.href = href;
                return false;
            }
        }
    }, true);
    
    // 拦截window.open
    var originalOpen = window.open;
    window.open = function(url, target, features) {
        // 强制在当前窗口打开
        window.location.href = url;
        return null;
    };
    
    // 拦截表单提交
    document.addEventListener('submit', function(e) {
        var form = e.target;
        if (form.tagName === 'FORM') {
            form.target = '_self';
        }
    }, true);
    
    // 拦截右键菜单中的"在新窗口打开"
    document.addEventListener('contextmenu', function(e) {
        var target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (target && target.tagName === 'A') {
            target.target = '_self';
        }
    }, true);
    
    // 动态监控DOM，处理后来添加的链接
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.tagName === 'A') {
                    node.target = '_self';
                }
                if (node.querySelectorAll) {
                    var links = node.querySelectorAll('a');
                    links.forEach(function(link) {
                        link.target = '_self';
                    });
                }
            });
        });
    });
    observer.observe(document.body || document.documentElement, { childList: true, subtree: true });
    
    // 处理所有现有链接
    document.querySelectorAll('a').forEach(function(link) {
        link.target = '_self';
    });
})();
'''

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
        <label for="fullscreenCheck">全屏模式</label>
    </div>
    <div class="hint">💡 按 F1 可随时打开此设置窗口</div>
    <button class="btn" onclick="saveAndReload()">保存</button>
</div>
<script>
var urlInput = document.getElementById('urlInput');
var titleInput = document.getElementById('titleInput');
var fullscreenCheck = document.getElementById('fullscreenCheck');

// 等待API准备好再加载配置
function loadConfig() {
    if (window.pywebview && window.pywebview.api) {
        pywebview.api.get_config().then(function(c) {
            if (c.url) urlInput.value = c.url;
            if (c.title) titleInput.value = c.title;
            fullscreenCheck.checked = c.fullscreen !== false;
            urlInput.focus();
        }).catch(function(err) {
            console.log('加载配置失败，重试...');
            setTimeout(loadConfig, 100);
        });
    } else {
        setTimeout(loadConfig, 100);
    }
}

// 监听pywebview ready事件
window.addEventListener('pywebviewready', loadConfig);
// 备用：延迟加载
setTimeout(loadConfig, 300);

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
current_fullscreen = True  # 记录当前全屏状态

# ===== API =====
class BrowseApi:
    def get_config(self):
        return load_config()
    
    def save_and_reload(self, url, title, fullscreen):
        global browse_window, current_fullscreen
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
            # 实时切换全屏模式
            if fullscreen != current_fullscreen:
                browse_window.toggle_fullscreen()
                current_fullscreen = fullscreen
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
            webview.create_window('修改网址', html=SETTINGS_HTML, js_api=api, width=540, height=500, resizable=False)
        keyboard.add_hotkey('f1', open_settings)
        keyboard.wait()
    except Exception as e:
        print(f"快捷键监听失败: {e}")

# ===== 获取屏幕尺寸 =====
def get_screen_size():
    try:
        import tkinter as tk
        root = tk.Tk()
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
    except:
        return 1920, 1080

# ===== 主程序 =====
def main():
    global current_fullscreen
    config = load_config()
    screen_width, screen_height = get_screen_size()
    current_fullscreen = config.get('fullscreen', True)  # 初始化全屏状态
    
    # 启动全局快捷键监听
    hotkey_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    hotkey_thread.start()
    
    if config.get('url'):
        api = BrowseApi()
        global browse_window
        fullscreen = config.get('fullscreen', True)
        
        # 窗口参数
        window_args = {
            'title': config.get('title', 'WebBox'),
            'url': config['url'],
            'js_api': api
        }
        
        if fullscreen:
            # 全屏模式：创建后再切换
            pass
        else:
            # 非全屏模式：最大化窗口，定位到(0,0)
            window_args['width'] = screen_width
            window_args['height'] = screen_height
            window_args['x'] = 0
            window_args['y'] = 0
        
        browse_window = webview.create_window(**window_args)
        
        # 页面加载完成后注入拦截脚本并设置全屏
        def on_loaded():
            try:
                # 注入允许选择的CSS
                browse_window.evaluate_js('''
                    (function() {
                        var style = document.createElement('style');
                        style.innerHTML = '* { user-select: text !important; -webkit-user-select: text !important; }';
                        document.head.appendChild(style);
                    })();
                ''')
                browse_window.evaluate_js(INTERCEPT_LINKS_JS)
                # 在窗口显示后切换全屏模式
                if fullscreen:
                    browse_window.toggle_fullscreen()
            except:
                pass
        
        browse_window.events.loaded += on_loaded
    else:
        api = SettingsApi()
        webview.create_window('WebBox 设置', html=SETTINGS_HTML, js_api=api, width=540, height=500, resizable=False)
    
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
