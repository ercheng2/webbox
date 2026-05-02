import webview
import json
import sys
import os
import threading
import urllib.request
import urllib.parse
import time
import re
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
            box.style.cssText = 'position:fixed;top:16px;right:16px;z-index:999999;pointer-events:none;';
            document.body.appendChild(box);
        }
        box.innerHTML = '<div style="background:rgba(30,30,40,0.95);color:#fff;padding:14px 20px;border-radius:10px;font-size:14px;min-width:220px;box-shadow:0 4px 20px rgba(0,0,0,0.4);margin-bottom:8px">' +
            '<div style="font-weight:600;margin-bottom:4px">' + status + '</div>' +
            '<div style="color:#aaa;font-size:12px;word-break:break-all">' + filename + '</div>' +
            '</div>';
    }
    
    // ===== Python回调：下载状态 =====
    window.__webbox_download_result = function(filename, status) {
        showNotify(filename, status);
        setTimeout(function() {
            var box = document.getElementById('__webbox_notify');
            if (box) box.innerHTML = '';
        }, 5000);
    };
    
    // ===== 点击拦截：所有链接交给Python =====
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
    
    // ===== 拦截右键"在新窗口打开" =====
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
_last_url = ''  # 记录上一个正常页面URL

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

def check_url_is_download(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        resp = urllib.request.urlopen(req, timeout=8)
        content_type = resp.headers.get('Content-Type', '')
        content_disp = resp.headers.get('Content-Disposition', '')
        
        if 'attachment' in content_disp.lower():
            return True
        
        download_types = [
            'application/octet-stream', 'application/x-msdownload',
            'application/x-msdos-program', 'application/zip',
            'application/x-rar-compressed', 'application/x-7z-compressed',
            'application/x-tar', 'application/gzip', 'application/pdf',
            'application/msword', 'application/vnd.ms-excel',
            'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats',
        ]
        for dt in download_types:
            if dt in content_type.lower():
                return True
        return False
    except:
        return False

# ===== 下载逻辑 =====
def do_download(url, go_back=False):
    """执行下载"""
    import json as _json
    global browse_window
    
    def _download():
        try:
            # 解析相对URL
            if not url.startswith('http'):
                try:
                    current_url = browse_window.get_current_url() if browse_window else ''
                    if current_url:
                        url_full = urllib.parse.urljoin(current_url, url)
                    else:
                        url_full = 'https://' + url
                except:
                    url_full = 'https://' + url
            else:
                url_full = url
            
            # 下载目录
            if sys.platform == 'win32':
                download_dir = Path(os.environ.get('USERPROFILE', '.')) / 'Downloads' / 'WebBox'
            else:
                download_dir = Path.home() / 'Downloads' / 'WebBox'
            download_dir.mkdir(parents=True, exist_ok=True)
            
            # 先用HEAD获取真实文件名
            filename = 'download'
            try:
                req = urllib.request.Request(url_full, method='HEAD')
                req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                resp = urllib.request.urlopen(req, timeout=10)
                disp = resp.headers.get('Content-Disposition', '')
                if 'filename' in disp:
                    m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^;"\']+)["\']?', disp)
                    if m:
                        filename = urllib.parse.unquote(m.group(1))
            except:
                pass
            
            if filename == 'download':
                filename = url_full.split('/')[-1].split('?')[0] or 'download'
            
            filepath = download_dir / filename
            
            # 通知：正在下载
            notify_js = 'window.__webbox_download_result({}, {})'.format(
                _json.dumps(filename),
                _json.dumps('📥 正在下载...')
            )
            try:
                browse_window.evaluate_js(notify_js)
            except:
                pass
            
            # 下载文件
            req = urllib.request.Request(url_full)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            resp = urllib.request.urlopen(req, timeout=120)
            
            with open(str(filepath), 'wb') as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            
            # 通知：下载完成
            notify_js = 'window.__webbox_download_result({}, {})'.format(
                _json.dumps(filename),
                _json.dumps('✅ 下载完成: ' + str(filepath))
            )
            try:
                browse_window.evaluate_js(notify_js)
            except:
                pass
            
            # 下载完成后回到上一页
            if go_back:
                try:
                    time.sleep(1)
                    browse_window.evaluate_js('window.history.back();')
                except:
                    pass
                
        except Exception as e:
            notify_js = 'window.__webbox_download_result({}, {})'.format(
                _json.dumps('download'),
                _json.dumps('❌ 下载失败: ' + str(e))
            )
            try:
                browse_window.evaluate_js(notify_js)
            except:
                pass
            if go_back:
                try:
                    time.sleep(2)
                    browse_window.evaluate_js('window.history.back();')
                except:
                    pass
    
    t = threading.Thread(target=_download, daemon=True)
    t.start()

# ===== API =====
class BrowseApi:
    def get_config(self):
        return load_config()
    
    def handle_link(self, href):
        """处理所有链接点击：判断是下载还是导航"""
        global browse_window, _last_url
        
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
        
        # 快速检查：URL扩展名是下载文件
        if is_download_by_ext(href):
            do_download(href, go_back=True)
            return {'action': 'download'}
        
        # 后台检查：HEAD请求判断是否为下载
        def check_and_handle():
            try:
                if check_url_is_download(href):
                    do_download(href, go_back=True)
                else:
                    # 不是下载，正常导航
                    if browse_window:
                        browse_window.load_url(href)
            except:
                if browse_window:
                    browse_window.load_url(href)
        
        t = threading.Thread(target=check_and_handle, daemon=True)
        t.start()
        return {'action': 'checking'}
    
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

# ===== Hook浏览器下载+导航拦截 =====
def patch_edgechromium():
    """Hook WebView2的下载和导航，从底层拦截"""
    try:
        from webview.platforms import edgechromium
        
        # 1. Hook下载事件：取消浏览器原生下载，改用自己下载
        original_on_download = edgechromium.Browser.on_download_starting
        
        def custom_on_download(self, sender, args):
            global browse_window
            args.Cancel = True  # 取消浏览器原生下载弹窗
            download_url = ''
            try:
                download_url = str(args.ContentUri)
            except:
                pass
            if not download_url:
                try:
                    download_url = str(args.ResultFilePath)
                except:
                    pass
            print(f"[WebBox] 拦截下载: {download_url}")
            if download_url and browse_window:
                do_download(download_url, go_back=True)
        
        edgechromium.Browser.on_download_starting = custom_on_download
        
        # 2. Hook导航事件：检测到导航到下载URL时取消导航
        original_on_navigation = edgechromium.Browser.on_navigation_starting if hasattr(edgechromium.Browser, 'on_navigation_starting') else None
        
        print("[WebBox] 已Hook下载处理器")
    except Exception as e:
        print(f"[WebBox] Hook下载处理器失败: {e}")

# ===== 主程序 =====
def main():
    global current_fullscreen, browse_window, _last_url
    
    # Hook底层
    patch_edgechromium()
    
    # 禁止pywebview原生下载弹窗
    webview.settings['ALLOW_DOWNLOADS'] = False
    
    config = load_config()
    screen_width, screen_height = get_screen_size()
    current_fullscreen = config.get('fullscreen', True)
    
    hotkey_thread = threading.Thread(target=start_hotkey_listener, daemon=True)
    hotkey_thread.start()
    
    if config.get('url'):
        api = BrowseApi()
        fullscreen = config.get('fullscreen', True)
        _last_url = config['url']
        
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
            global _last_url
            try:
                # 记录当前URL
                try:
                    _last_url = browse_window.get_current_url()
                except:
                    pass
                
                # 注入CSS
                browse_window.evaluate_js('''
                    (function() {
                        var style = document.createElement('style');
                        style.innerHTML = '* { user-select: text !important; -webkit-user-select: text !important; }';
                        document.head.appendChild(style);
                    })();
                ''')
                # 注入链接拦截JS
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
        
        def on_before_load(url):
            """导航前拦截：检测下载URL则取消导航"""
            global _last_url
            try:
                if is_download_by_ext(url):
                    print(f"[WebBox] 导航拦截(扩展名): {url}")
                    do_download(url, go_back=True)
                    return False  # 取消导航
                
                # 对非本地URL做HEAD检测
                if url.startswith('http://') or url.startswith('https://'):
                    if check_url_is_download(url):
                        print(f"[WebBox] 导航拦截(HEAD检测): {url}")
                        do_download(url, go_back=True)
                        return False  # 取消导航
                
                # 正常导航，记录URL
                _last_url = url
            except:
                pass
            return True  # 允许导航
        
        browse_window.events.loaded += on_loaded
        browse_window.events.before_load += on_before_load
    else:
        api = SettingsApi()
        webview.create_window('WebBox 设置', html=SETTINGS_HTML, js_api=api, width=540, height=500, resizable=False)
    
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
