import webview
import json
import sys
import os
import threading
import urllib.parse
import time
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
    // ===== 显示通知 =====
    function showNotify(filename, status) {
        var box = document.getElementById('__webbox_notify');
        if (!box) {
            box = document.createElement('div');
            box.id = '__webbox_notify';
            box.style.cssText = 'position:fixed;top:16px;right:16px;z-index:999999;pointer-events:auto;';
            document.body.appendChild(box);
        }
        box.innerHTML = '<div style="background:rgba(30,30,40,0.95);color:#fff;padding:14px 20px;border-radius:10px;font-size:14px;min-width:260px;box-shadow:0 4px 20px rgba(0,0,0,0.4);margin-bottom:8px">' +
            '<div style="font-weight:600;margin-bottom:4px">' + status + '</div>' +
            '<div style="color:#aaa;font-size:12px;word-break:break-all">' + filename + '</div>' +
            '</div>';
    }
    
    // ===== Python回调：下载状态 =====
    window.__webbox_download_start = function(filename) {
        showNotify(filename, '📥 正在下载...');
    };
    window.__webbox_download_done = function(filename, filepath) {
        showNotify(filename, '✅ 下载完成');
        setTimeout(function() {
            var box = document.getElementById('__webbox_notify');
            if (box) box.innerHTML = '';
        }, 5000);
    };
    
    // ===== 点击拦截：链接交给Python =====
    document.addEventListener('click', function(e) {
        var target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (target && target.tagName === 'A') {
            var href = target.getAttribute('href');
            if (href && !href.startsWith('javascript:') && !href.startsWith('#') && !href.startsWith('mailto:')) {
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                if (window.pywebview && window.pywebview.api) {
                    pywebview.api.handle_link(href);
                }
                return false;
            }
        }
    }, true);
    
    // ===== 拦截window.open =====
    window.open = function(url, target, features) {
        if (url && !url.startsWith('javascript:') && !url.startsWith('#')) {
            if (window.pywebview && window.pywebview.api) {
                pywebview.api.handle_link(url);
            }
        }
        return null;
    };
    
    // ===== 拦截表单提交 =====
    document.addEventListener('submit', function(e) {
        var form = e.target;
        if (form.tagName === 'FORM') {
            form.target = '_self';
        }
    }, true);
    
    // ===== 拦截右键 =====
    document.addEventListener('contextmenu', function(e) {
        var target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (target && target.tagName === 'A') {
            target.target = '_self';
        }
    }, true);
    
    // ===== 动态监控DOM =====
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

function loadConfig() {
    if (window.pywebview && window.pywebview.api) {
        pywebview.api.get_config().then(function(c) {
            if (c.url) urlInput.value = c.url;
            if (c.title) titleInput.value = c.title;
            fullscreenCheck.checked = c.fullscreen !== false;
            urlInput.focus();
        }).catch(function(err) {
            setTimeout(loadConfig, 100);
        });
    } else {
        setTimeout(loadConfig, 100);
    }
}

window.addEventListener('pywebviewready', loadConfig);
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
current_fullscreen = True

# ===== 下载目录 =====
def get_download_dir():
    if sys.platform == 'win32':
        d = Path(os.environ.get('USERPROFILE', '.')) / 'Downloads' / 'WebBox'
    else:
        d = Path.home() / 'Downloads' / 'WebBox'
    d.mkdir(parents=True, exist_ok=True)
    return d

# ===== 判断URL是否为文件下载 =====
DOWNLOAD_EXTS = ['.exe', '.msi', '.zip', '.rar', '.7z', '.tar', '.gz',
                 '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                 '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv',
                 '.iso', '.dmg', '.deb', '.rpm', '.apk']

def is_download_by_ext(url):
    lower = url.lower().split('?')[0].split('#')[0]
    for ext in DOWNLOAD_EXTS:
        if lower.endswith(ext):
            return True
    return False

# ===== Hook浏览器下载：不弹对话框，直接下载到WebBox目录 =====
def patch_download_handler():
    """Hook pywebview的DownloadStarting事件，不弹保存对话框，直接下载到指定目录"""
    try:
        from webview.platforms import edgechromium
        
        def custom_on_download(self, sender, args):
            # 不取消下载！让浏览器正常下载
            # 但把保存路径改到 Downloads/WebBox/，不弹对话框
            download_dir = get_download_dir()
            original_filename = os.path.basename(args.ResultFilePath)
            save_path = str(download_dir / original_filename)
            
            # 设置下载路径
            args.ResultFilePath = save_path
            
            # 通知页面：开始下载
            filename = original_filename
            def notify_start():
                try:
                    import json as _json
                    browse_window.evaluate_js('window.__webbox_download_start({})'.format(
                        _json.dumps(filename)
                    ))
                except:
                    pass
            
            def notify_done():
                try:
                    import json as _json
                    browse_window.evaluate_js('window.__webbox_download_done({}, {})'.format(
                        _json.dumps(filename),
                        _json.dumps(save_path)
                    ))
                except:
                    pass
                # 下载完成后回到上一页
                try:
                    time.sleep(1)
                    browse_window.evaluate_js('window.history.back();')
                except:
                    pass
            
            # 通知开始下载
            threading.Thread(target=notify_start, daemon=True).start()
            
            # 监控下载完成：等文件出现且不再增长
            def wait_for_download():
                filepath = save_path
                last_size = 0
                same_count = 0
                # 最多等5分钟
                for i in range(300):
                    time.sleep(1)
                    try:
                        if os.path.exists(filepath):
                            current_size = os.path.getsize(filepath)
                            if current_size == last_size and current_size > 0:
                                same_count += 1
                                if same_count >= 3:
                                    # 文件大小3秒没变，认为下载完成
                                    notify_done()
                                    return
                            else:
                                same_count = 0
                                last_size = current_size
                    except:
                        pass
                # 超时也通知
                notify_done()
            
            threading.Thread(target=wait_for_download, daemon=True).start()
        
        edgechromium.Browser.on_download_starting = custom_on_download
        print("[WebBox] 已Hook下载处理器：自动下载到WebBox目录")
    except Exception as e:
        print(f"[WebBox] Hook下载处理器失败: {e}")

# ===== API =====
class BrowseApi:
    def get_config(self):
        return load_config()
    
    def handle_link(self, href):
        """处理链接点击"""
        global browse_window
        
        # 解析相对URL
        if not href.startswith('http://') and not href.startswith('https://'):
            try:
                current_url = browse_window.get_current_url() if browse_window else ''
                if current_url:
                    href = urllib.parse.urljoin(current_url, href)
                else:
                    href = 'https://' + href
            except:
                href = 'https://' + href
        
        # 所有链接都正常导航，下载的会被DownloadStarting拦截
        if browse_window:
            browse_window.load_url(href)
        return {'action': 'navigate'}
    
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

# ===== 获取屏幕工作区尺寸 =====
def get_screen_size():
    try:
        import ctypes
        class RECT(ctypes.Structure):
            _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                       ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
        rect = RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        return width, height
    except:
        return 1920, 1040

# ===== 主程序 =====
def main():
    global current_fullscreen, browse_window
    
    # Hook下载：不弹对话框，自动下载到WebBox目录
    patch_download_handler()
    # 允许下载（让DownloadStarting事件走我们的Hook）
    webview.settings['ALLOW_DOWNLOADS'] = True
    
    config = load_config()
    screen_width, screen_height = get_screen_size()
    current_fullscreen = config.get('fullscreen', True)
    
    hotkey_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    hotkey_thread.start()
    
    if config.get('url'):
        api = BrowseApi()
        fullscreen = config.get('fullscreen', True)
        
        window_args = {
            'title': config.get('title', 'WebBox'),
            'url': config['url'],
            'js_api': api
        }
        
        if not fullscreen:
            window_args['width'] = screen_width
            window_args['height'] = screen_height
            window_args['x'] = 0
            window_args['y'] = 0
        
        browse_window = webview.create_window(**window_args)
        
        def on_loaded():
            try:
                browse_window.evaluate_js('''
                    (function() {
                        var style = document.createElement('style');
                        style.innerHTML = '* { user-select: text !important; -webkit-user-select: text !important; }';
                        document.head.appendChild(style);
                    })();
                ''')
                browse_window.evaluate_js(INTERCEPT_LINKS_JS)
                if fullscreen:
                    browse_window.toggle_fullscreen()
                else:
                    try:
                        import ctypes
                        time.sleep(0.1)
                        hwnd = ctypes.windll.user32.FindWindowW(None, config.get('title', 'WebBox'))
                        if hwnd:
                            ctypes.windll.user32.ShowWindow(hwnd, 3)
                    except:
                        pass
            except:
                pass
        
        browse_window.events.loaded += on_loaded
    else:
        api = SettingsApi()
        webview.create_window('WebBox 设置', html=SETTINGS_HTML, js_api=api, width=540, height=500, resizable=False)
    
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
