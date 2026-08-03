import webview
import json
import sys
import os
import threading
import urllib.parse
import time
from pathlib import Path

# ===== 配置管理 =====
_custom_config_path = None  # 通过 --config 参数指定的配置文件路径

def get_default_config_path():
    """获取默认配置文件路径：exe 同目录下的 config.json（不受 _custom_config_path 影响）"""
    exe_dir = Path(sys.executable).parent
    return exe_dir / 'config.json'

def get_config_path():
    if _custom_config_path:
        p = Path(_custom_config_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return get_default_config_path()

def load_config():
    global _custom_config_path
    config_file = get_config_path()
    default = {'url': '', 'title': 'WebBox', 'fullscreen': True, 'download_dir': '', 'config_file': str(get_config_path())}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and data.get('url'):
                    if 'fullscreen' not in data:
                        data['fullscreen'] = True
                    # 如果默认配置中 config_file 指向其他文件，且 _custom_config_path 为空，自动跟随
                    cfg_file = data.get('config_file', '')
                    if cfg_file and not _custom_config_path and cfg_file != str(config_file):
                        alt_path = Path(cfg_file)
                        if alt_path.exists():
                            try:
                                with open(alt_path, 'r', encoding='utf-8') as af:
                                    alt_data = json.load(af)
                                    if isinstance(alt_data, dict) and alt_data.get('url'):
                                        _custom_config_path = cfg_file
                                        if 'fullscreen' not in alt_data:
                                            alt_data['fullscreen'] = True
                                        print(f"[WebBox] 配置跟随指针 → {cfg_file}")
                                        return alt_data
                            except Exception as e:
                                print(f"[WebBox] 指针目标文件读取失败: {cfg_file} - {e}")
                        else:
                            print(f"[WebBox] 指针目标文件不存在: {cfg_file}，使用默认配置")
                    print(f"[WebBox] 加载配置: {config_file}")
                    return data
        except Exception as e:
            print(f"[WebBox] 配置文件读取失败: {config_file} - {e}")
    print(f"[WebBox] 无配置，使用默认设置")
    return default

def save_config(data, target_path=None):
    """保存配置，target_path 可指定另存为的路径"""
    if target_path:
        config_file = Path(target_path)
    else:
        config_file = get_config_path()
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        # 记录当前配置文件路径（保留已有的 config_file 指针，避免覆盖）
        if not data.get('config_file'):
            data['config_file'] = str(config_file)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[WebBox] 配置已保存: {config_file}")
        return True
    except Exception as e:
        print(f"[WebBox] 配置保存失败: {config_file} - {e}")
        return False

# ===== JS代码：不拦截链接点击，让浏览器原生处理 =====
JS_CODE = '''
(function() {
    // ===== 显示通知 =====
    function showNotify(filename, status, filepath) {
        var box = document.getElementById('__webbox_notify');
        if (!box) {
            box = document.createElement('div');
            box.id = '__webbox_notify';
            box.style.cssText = 'position:fixed;top:16px;right:16px;z-index:999999;pointer-events:auto;';
            document.body.appendChild(box);
        }
        var clickAction = '';
        var cursorStyle = '';
        if (filepath) {
            clickAction = ' onclick="window.__webbox_open_folder()" style="cursor:pointer"';
        }
        box.innerHTML = '<div style="background:rgba(30,30,40,0.95);color:#fff;padding:14px 20px;border-radius:10px;font-size:14px;min-width:260px;box-shadow:0 4px 20px rgba(0,0,0,0.4);margin-bottom:8px"' + clickAction + '>' +
            '<div style="font-weight:600;margin-bottom:4px">' + status + '</div>' +
            '<div style="color:#aaa;font-size:12px;word-break:break-all">' + filename + '</div>' +
            (filepath ? '<div style="color:#6ca0dc;font-size:11px;margin-top:6px">📂 点击打开文件夹</div>' : '') +
            '</div>';
    }
    
    // ===== 打开文件夹 =====
    window.__webbox_open_folder = function() {
        if (window.pywebview && window.pywebview.api) {
            pywebview.api.open_download_folder();
        }
    };
    
    // ===== Python回调：下载状态 =====
    window.__webbox_download_start = function(filename) {
        showNotify(filename, '📥 正在下载...');
    };
    window.__webbox_download_done = function(filename, filepath) {
        showNotify(filename, '✅ 下载完成', filepath);
        setTimeout(function() {
            var box = document.getElementById('__webbox_notify');
            if (box) box.innerHTML = '';
        }, 8000);
    };
    
    // ===== 浮动按钮：打开EXE =====
    window.__webbox_setup_float_btn = function(cfg) {
        // 移除旧按钮
        var old = document.getElementById('__webbox_float_btn');
        if (old) old.remove();
        if (!cfg || !cfg.exe_path) return;
        
        var btn = document.createElement('div');
        btn.id = '__webbox_float_btn';
        btn.textContent = cfg.btn_text || '🔧';
        // 基础样式
        var css = 'position:fixed;z-index:999998;pointer-events:auto;cursor:pointer;' +
            'min-width:50px;height:50px;border-radius:6px;padding:0 16px;' +
            'background:rgba(102,126,234,0.9);color:#fff;' +
            'display:flex;align-items:center;justify-content:center;' +
            'font-size:18px;font-weight:bold;white-space:nowrap;' +
            'box-shadow:0 4px 16px rgba(0,0,0,0.3);' +
            'user-select:none;transition:transform 0.15s,box-shadow 0.15s;';
        // 位置：支持预设 + 自定义像素
        var pos = cfg.btn_position || '右下';
        if (pos === '自定义' && cfg.btn_custom_css) {
            css += cfg.btn_custom_css;
        } else {
            switch(pos) {
                case '左上': css += 'top:20px;left:20px;'; break;
                case '右上': css += 'top:20px;right:20px;'; break;
                case '左下': css += 'bottom:20px;left:20px;'; break;
                case '右下': default: css += 'bottom:20px;right:20px;'; break;
            }
        }
        btn.style.cssText = css;
        
        // 悬停效果
        btn.onmouseenter = function() { btn.style.transform='scale(1.1)'; btn.style.boxShadow='0 6px 24px rgba(0,0,0,0.4)'; };
        btn.onmouseleave = function() { btn.style.transform='scale(1)'; btn.style.boxShadow='0 4px 16px rgba(0,0,0,0.3)'; };
        
        // 点击打开EXE
        btn.onclick = function() {
            if (window.pywebview && window.pywebview.api) {
                pywebview.api.open_exe();
            }
        };
        
        // 拖拽移动
        var dragging = false, startX, startY, origLeft, origTop;
        btn.onmousedown = function(e) {
            if (e.button !== 0) return;
            dragging = true;
            startX = e.clientX;
            startY = e.clientY;
            var rect = btn.getBoundingClientRect();
            origLeft = rect.left;
            origTop = rect.top;
            btn.style.transition = 'none';
            e.preventDefault();
        };
        document.addEventListener('mousemove', function(e) {
            if (!dragging) return;
            var dx = e.clientX - startX;
            var dy = e.clientY - startY;
            btn.style.left = (origLeft + dx) + 'px';
            btn.style.top = (origTop + dy) + 'px';
            btn.style.right = 'auto';
            btn.style.bottom = 'auto';
        });
        document.addEventListener('mouseup', function() {
            if (dragging) {
                dragging = false;
                btn.style.transition = 'transform 0.15s,box-shadow 0.15s';
                // 保存拖拽后的位置
                var rect = btn.getBoundingClientRect();
                if (window.pywebview && window.pywebview.api) {
                    pywebview.api.save_float_btn_position(rect.top, rect.left);
                }
            }
        });
        
        document.body.appendChild(btn);
    };
    
    // ===== 拦截window.open：改为同窗口导航 =====
    window.open = function(url, target, features) {
        if (url && !url.startsWith('javascript:') && !url.startsWith('#')) {
            window.location.href = url;
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
    
    // ===== 拦截下载链接：交给Python端下载 =====
    document.addEventListener('click', function(e) {
        var target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (target && target.tagName === 'A' && target.href) {
            var href = target.href;
            var ext = href.split('?')[0].split('#')[0].split('.').pop().toLowerCase();
            var downloadExts = ['exe','zip','rar','7z','gz','tar','pdf','doc','docx','xls','xlsx','ppt','pptx','mp3','mp4','avi','mkv','wav','flac','iso','dmg','msi','apk','deb','rpm'];
            if (downloadExts.indexOf(ext) !== -1) {
                e.preventDefault();
                e.stopPropagation();
                if (window.pywebview && window.pywebview.api) {
                    pywebview.api.download_file(href);
                }
            }
        }
    }, true);
    
    // ===== 拦截右键：链接在当前窗口打开 =====
    document.addEventListener('contextmenu', function(e) {
        var target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (target && target.tagName === 'A') {
            target.target = '_self';
        }
    }, true);
    
    // ===== 动态监控DOM：链接在当前窗口打开 =====
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
    
    // ===== F5刷新拦截 =====
    document.addEventListener('keydown', function(e) {
        if (e.key === 'F5' || e.keyCode === 116) {
            e.preventDefault();
            e.stopPropagation();
            location.reload();
        }
    }, true);
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
.btn-clear { width: 100%; padding: 12px; border: 2px solid #e74c3c; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; background: white; color: #e74c3c; margin-top: 12px; }
.btn-clear:hover { background: #e74c3c; color: white; }
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
    <div class="field">
        <label>下载保存路径（留空则默认 Downloads/WebBox）</label>
        <input type="text" id="downloadDirInput" placeholder="如 D:\\Downloads 或留空">
    </div>
    <div class="field">
        <label>🖥 EXE路径（填写要启动的exe完整路径，留空则不显示浮动按钮）</label>
        <input type="text" id="exePathInput" placeholder="如 D:\\软件\\KZC-KeyGen.exe">
    </div>
    <div class="field">
        <label>按钮文字（可选）</label>
        <input type="text" id="btnTextInput" placeholder="如 🔧 或 打开工具">
    </div>
    <div class="field">
        <label>按钮位置</label>
        <select id="btnPositionSelect" style="width:100%;padding:14px 16px;border:2px solid #e0e0e0;border-radius:10px;font-size:16px;">
            <option value="右下">右下</option>
            <option value="左下">左下</option>
            <option value="右上">右上</option>
            <option value="左上">左上</option>
            <option value="自定义">自定义</option>
        </select>
    </div>
    <div class="field" id="customCssField" style="display:none;">
        <label>自定义位置CSS（如 top:100px;left:200px;）</label>
        <input type="text" id="btnCustomCssInput" placeholder="如 top:100px;left:200px;">
    </div>
    <div class="hint">💡 按 F1 可随时打开此设置窗口 | F5 刷新当前页面<br>📌 配置自动保存在 exe 同目录下，拷贝到其他电脑直接可用<br>🖱 浮动按钮拖拽后自动记住位置，下次打开不变</div>
    <button class="btn" onclick="saveAndReload()">保存</button>
    <button class="btn-clear" onclick="clearBrowsingData()">🗑 清除浏览记录（用户名、密码、缓存）</button>
</div>
<script>
var urlInput = document.getElementById('urlInput');
var titleInput = document.getElementById('titleInput');
var fullscreenCheck = document.getElementById('fullscreenCheck');
var downloadDirInput = document.getElementById('downloadDirInput');
var exePathInput = document.getElementById('exePathInput');
var btnTextInput = document.getElementById('btnTextInput');
var btnPositionSelect = document.getElementById('btnPositionSelect');
var btnCustomCssInput = document.getElementById('btnCustomCssInput');
var customCssField = document.getElementById('customCssField');

btnPositionSelect.onchange = function() {
    customCssField.style.display = (this.value === '自定义') ? 'block' : 'none';
};

function loadConfig() {
    if (window.pywebview && window.pywebview.api) {
        pywebview.api.get_config().then(function(c) {
            if (c.url) urlInput.value = c.url;
            if (c.title) titleInput.value = c.title;
            fullscreenCheck.checked = c.fullscreen !== false;
            if (c.download_dir) downloadDirInput.value = c.download_dir;
            if (c.exe_path) exePathInput.value = c.exe_path;
            if (c.btn_text) btnTextInput.value = c.btn_text;
            if (c.btn_position) btnPositionSelect.value = c.btn_position;
            if (c.btn_custom_css) btnCustomCssInput.value = c.btn_custom_css;
            customCssField.style.display = (btnPositionSelect.value === '自定义') ? 'block' : 'none';
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
    var btn = document.querySelector('.btn');
    btn.textContent = '保存中...';
    btn.disabled = true;
    pywebview.api.save_and_reload(
        url, titleInput.value.trim(), fullscreenCheck.checked,
        downloadDirInput.value.trim(), '',
        exePathInput.value.trim(), btnTextInput.value.trim() || '🔧',
        btnPositionSelect.value, btnCustomCssInput.value.trim()
    ).then(function(r) {
        if (r.full_ok === false) {
            btn.textContent = '❌ 保存失败，请检查路径';
            btn.style.background = '#e74c3c';
        } else if (r.ptr_ok === false) {
            btn.textContent = '⚠️ 已保存，但重启后可能丢失配置';
            btn.style.background = '#e67e22';
        } else {
            btn.textContent = '✅ 保存成功';
            btn.style.background = '#27ae60';
        }
        btn.disabled = false;
        setTimeout(function() {
            btn.textContent = '保存';
            btn.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        }, 2000);
    }).catch(function(err) {
        btn.textContent = '❌ 保存失败: ' + err;
        btn.style.background = '#e74c3c';
        btn.disabled = false;
    });
}

function clearBrowsingData() {
    pywebview.api.clear_browsing_data().then(function(result) {
        var btn = document.querySelector('.btn-clear');
        btn.textContent = '✅ 已标记清除，关闭软件后重新打开即可生效';
        btn.style.borderColor = '#27ae60';
        btn.style.color = '#27ae60';
    });
}

urlInput.onkeydown = function(e) { if (e.key === 'Enter') saveAndReload(); };
titleInput.onkeydown = function(e) { if (e.key === 'Enter') saveAndReload(); };
downloadDirInput.onkeydown = function(e) { if (e.key === 'Enter') saveAndReload(); };
window.addEventListener('keydown', function(e) {
    if (e.key === 'F5' || e.keyCode === 116) {
        e.preventDefault();
        pywebview.api.reload_page();
    }
});
</script>
</body>
</html>'''

# ===== 全局变量 =====
browse_window = None
current_fullscreen = True

# ===== 下载目录 =====
def get_download_dir():
    config = load_config()
    custom_dir = config.get('download_dir', '').strip()
    if custom_dir:
        d = Path(custom_dir)
        print(f"[WebBox] 使用自定义下载路径: {d}")
    elif sys.platform == 'win32':
        d = Path(os.environ.get('USERPROFILE', '.')) / 'Downloads' / 'WebBox'
    else:
        d = Path.home() / 'Downloads' / 'WebBox'
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[WebBox] 创建下载目录失败: {e}，使用默认路径")
        if sys.platform == 'win32':
            d = Path(os.environ.get('USERPROFILE', '.')) / 'Downloads' / 'WebBox'
        else:
            d = Path.home() / 'Downloads' / 'WebBox'
        d.mkdir(parents=True, exist_ok=True)
    return d

# ===== Hook浏览器下载：不弹对话框，直接下载到指定目录 =====
def patch_download_handler():
    """Hook pywebview的DownloadStarting事件，不弹保存对话框，直接下载到指定目录"""
    try:
        from webview.platforms import edgechromium
        
        # 兼容不同版本的pywebview类名
        BrowserClass = getattr(edgechromium, 'EdgeChrome', None) or getattr(edgechromium, 'Browser', None)
        if not BrowserClass:
            print("[WebBox] 找不到浏览器类，下载Hook失败")
            return
        
        original_on_download = getattr(BrowserClass, 'on_download_starting', None)
        
        def custom_on_download(self, sender, args):
            download_dir = get_download_dir()
            original_filename = os.path.basename(args.ResultFilePath)
            save_path = str(download_dir / original_filename)
            
            # 设置下载路径并抑制默认对话框
            args.ResultFilePath = save_path
            try:
                args.Handled = True
            except:
                pass
            
            print(f"[WebBox] 下载拦截: {original_filename} → {save_path}")
            
            filename = original_filename
            def notify_start():
                try:
                    browse_window.evaluate_js('window.__webbox_download_start({})'.format(
                        json.dumps(filename)
                    ))
                except:
                    pass
            
            def notify_done():
                try:
                    browse_window.evaluate_js('window.__webbox_download_done({}, {})'.format(
                        json.dumps(filename),
                        json.dumps(save_path)
                    ))
                except:
                    pass
            
            threading.Thread(target=notify_start, daemon=True).start()
            
            def wait_for_download():
                filepath = save_path
                last_size = 0
                same_count = 0
                for i in range(300):
                    time.sleep(1)
                    try:
                        if os.path.exists(filepath):
                            current_size = os.path.getsize(filepath)
                            if current_size == last_size and current_size > 0:
                                same_count += 1
                                if same_count >= 3:
                                    notify_done()
                                    return
                            else:
                                same_count = 0
                                last_size = current_size
                    except:
                        pass
                notify_done()
            
            threading.Thread(target=wait_for_download, daemon=True).start()
        
        BrowserClass.on_download_starting = custom_on_download
        print(f"[WebBox] 已Hook下载处理器({BrowserClass.__name__})：自动下载到指定目录")
    except Exception as e:
        print(f"[WebBox] Hook下载处理器失败: {e}")

# ===== API =====
class BrowseApi:
    def get_config(self):
        return load_config()
    
    def reload_page(self):
        if browse_window:
            try:
                browse_window.evaluate_js('location.reload()')
            except:
                pass
        return {'ok': True}
    
    def open_download_folder(self):
        """打开下载文件夹"""
        try:
            download_dir = str(get_download_dir())
            os.startfile(download_dir)
        except Exception as e:
            print(f"[WebBox] 打开文件夹失败: {e}")
        return {'ok': True}
    
    def open_exe(self):
        """打开配置的EXE文件"""
        try:
            config = load_config()
            exe_path = config.get('exe_path', '').strip()
            if not exe_path:
                return {'ok': False, 'error': '未配置EXE路径'}
            if not os.path.exists(exe_path):
                return {'ok': False, 'error': f'文件不存在: {exe_path}'}
            os.startfile(exe_path)
            print(f"[WebBox] 已启动: {exe_path}")
            return {'ok': True}
        except Exception as e:
            print(f"[WebBox] 打开EXE失败: {e}")
            return {'ok': False, 'error': str(e)}
    
    def save_float_btn_position(self, top, left):
        """保存浮动按钮拖拽后的位置"""
        try:
            config = load_config()
            config['btn_position'] = '自定义'
            config['btn_custom_css'] = f'top:{int(top)}px;left:{int(left)}px;'
            ok = save_config(config, target_path=get_config_path())
            print(f"[WebBox] 浮动按钮位置已保存: top={int(top)}px, left={int(left)}px")
            return {'ok': ok}
        except Exception as e:
            print(f"[WebBox] 保存按钮位置失败: {e}")
            return {'ok': False, 'error': str(e)}
    
    def clear_browsing_data(self):
        """清除浏览记录：标记清除标记，下次启动时删除WebView2数据"""
        try:
            # 写一个清除标记文件（exe同目录）
            marker_dir = Path(sys.executable).parent
            marker_file = marker_dir / '.clear_data'
            marker_file.write_text('1', encoding='utf-8')
            print("[WebBox] 已标记清除，重启后生效")
        except Exception as e:
            print(f"[WebBox] 标记清除失败: {e}")
        return {'ok': True, 'need_restart': True}
    
    def download_file(self, url):
        """Python端下载文件到指定目录"""
        def _download():
            try:
                import urllib.request
                download_dir = get_download_dir()
                filename = url.split('?')[0].split('#')[0].split('/')[-1]
                if not filename or '.' not in filename:
                    filename = 'download'
                save_path = download_dir / filename
                # 避免重名
                counter = 1
                while save_path.exists():
                    name, ext = os.path.splitext(filename)
                    save_path = download_dir / f"{name}_{counter}{ext}"
                    counter += 1
                # 通知开始下载
                browse_window.evaluate_js('window.__webbox_download_start({})'.format(
                    json.dumps(filename)
                ))
                # 下载
                urllib.request.urlretrieve(url, str(save_path))
                # 通知下载完成
                browse_window.evaluate_js('window.__webbox_download_done({}, {})'.format(
                    json.dumps(filename),
                    json.dumps(str(save_path))
                ))
                print(f"[WebBox] 下载完成: {save_path}")
            except Exception as e:
                print(f"[WebBox] 下载失败: {e}")
                try:
                    browse_window.evaluate_js('window.__webbox_download_start({})'.format(
                        json.dumps(f"下载失败: {str(e)}")
                    ))
                except:
                    pass
        threading.Thread(target=_download, daemon=True).start()
        return {'ok': True}
    
    def handle_link(self, href):
        """处理window.open拦截（简化版，链接点击不再走这里）"""
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
        
        # window.location.href 同窗口导航
        if browse_window:
            browse_window.evaluate_js('window.location.href = {};'.format(json.dumps(href)))
        return {'action': 'navigate'}
    
    def save_and_reload(self, url, title, fullscreen, download_dir='', config_file='', exe_path='', btn_text='', btn_position='右下', btn_custom_css=''):
        global browse_window, current_fullscreen, _custom_config_path
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        config = {
            'url': url, 
            'title': title.strip() or 'WebBox',
            'fullscreen': fullscreen,
            'download_dir': download_dir.strip(),
            'exe_path': exe_path.strip(),
            'btn_text': btn_text.strip() or '🔧',
            'btn_position': btn_position,
            'btn_custom_css': btn_custom_css.strip(),
        }
        # 更新全局配置路径，确保后续 load_config() 读取正确的文件
        if config_file.strip():
            # ⚠️ 指针必须存到默认路径，不能用 target_path=None（会被 _custom_config_path 劫持）
            ptr_ok = save_config({'url': config['url'], 'title': config['title'], 'fullscreen': config['fullscreen'], 'download_dir': '', 'exe_path': '', 'btn_text': '', 'btn_position': '右下', 'btn_custom_css': '', 'config_file': config_file.strip()}, target_path=str(get_default_config_path()))
            _custom_config_path = config_file.strip()
            if not ptr_ok:
                print(f"[WebBox] 指针保存失败！默认路径可能不可写")
        full_ok = save_config(config, target_path=config_file.strip() or None)
        if not full_ok:
            print(f"[WebBox] 完整配置保存失败！路径: {config_file.strip() or '默认'}")
        if browse_window:
            browse_window.load_url(url)
            if fullscreen != current_fullscreen:
                browse_window.toggle_fullscreen()
                current_fullscreen = fullscreen
        return {'ok': True, 'ptr_ok': ptr_ok if config_file.strip() else None, 'full_ok': full_ok}

class SettingsApi:
    def get_config(self):
        return load_config()
    
    def save_and_reload(self, url, title, fullscreen, download_dir='', config_file='', exe_path='', btn_text='', btn_position='右下', btn_custom_css=''):
        global _custom_config_path
        url = url.strip()
        if not url:
            return {'error': '请输入网址'}
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        config = {
            'url': url, 
            'title': title.strip() or 'WebBox',
            'fullscreen': fullscreen,
            'download_dir': download_dir.strip(),
            'exe_path': exe_path.strip(),
            'btn_text': btn_text.strip() or '🔧',
            'btn_position': btn_position,
            'btn_custom_css': btn_custom_css.strip(),
        }
        if config_file.strip():
            # ⚠️ 指针必须存到默认路径，不能用 target_path=None（会被 _custom_config_path 劫持）
            ptr_ok = save_config({'url': config['url'], 'title': config['title'], 'fullscreen': config['fullscreen'], 'download_dir': '', 'exe_path': '', 'btn_text': '', 'btn_position': '右下', 'btn_custom_css': '', 'config_file': config_file.strip()}, target_path=str(get_default_config_path()))
            _custom_config_path = config_file.strip()
            if not ptr_ok:
                print(f"[WebBox] 指针保存失败！默认路径可能不可写")
        full_ok = save_config(config, target_path=config_file.strip() or None)
        if not full_ok:
            print(f"[WebBox] 完整配置保存失败！路径: {config_file.strip() or '默认'}")
        return {'ok': True, 'ptr_ok': ptr_ok if config_file.strip() else None, 'full_ok': full_ok}

# ===== 全局快捷键监听 =====
def start_hotkey_listener():
    global browse_window
    try:
        import keyboard
        def open_settings():
            api = BrowseApi()
            webview.create_window('修改网址', html=SETTINGS_HTML, js_api=api, width=540, height=740, resizable=False)
        
        def reload_page():
            if browse_window:
                try:
                    browse_window.evaluate_js('location.reload()')
                    print("[WebBox] 已刷新页面")
                except Exception as e:
                    print(f"[WebBox] 刷新失败: {e}")
        
        keyboard.add_hotkey('f1', open_settings)
        keyboard.add_hotkey('f5', reload_page)
        print("[WebBox] F1=打开设置 F5=刷新页面")
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
    global current_fullscreen, browse_window, _custom_config_path
    
    # 解析 --config 命令行参数
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == '--config' and i + 1 < len(args):
            _custom_config_path = args[i + 1]
            print(f"[WebBox] 使用自定义配置文件: {_custom_config_path}")
            i += 2
        else:
            i += 1
    
    # 检查是否需要清除浏览数据（上次标记的）
    try:
        import shutil
        marker_dir = Path(sys.executable).parent
        app_data = os.environ.get('APPDATA', '')
        marker_file = marker_dir / '.clear_data'
        if marker_file.exists():
            print("[WebBox] 检测到清除标记，正在清除浏览数据...")
            marker_file.unlink(missing_ok=True)
            # 删除pywebview缓存目录（WebView2用户数据）
            # pywebview使用 %APPDATA%\pywebview 作为UserDataFolder
            if app_data:
                pywebview_cache = Path(app_data) / 'pywebview'
                if pywebview_cache.exists():
                    shutil.rmtree(pywebview_cache, ignore_errors=True)
                    print(f"[WebBox] 已清除: {pywebview_cache}")
            print("[WebBox] 浏览数据已清除，请重新打开软件")
    except Exception as e:
        print(f"[WebBox] 清除浏览数据失败: {e}")
    
    # Hook下载：不弹对话框，自动下载到WebBox目录
    patch_download_handler()
    
    # 允许下载（让DownloadStarting事件走我们的Hook）
    webview.settings['ALLOW_DOWNLOADS'] = True
    # 外链在当前窗口打开（不打开系统浏览器）
    webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = False
    
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
                browse_window.evaluate_js(JS_CODE)
                # 注入浮动按钮配置（重新加载配置，避免使用启动时的旧值）
                latest_config = load_config()
                float_cfg = {
                    'exe_path': latest_config.get('exe_path', ''),
                    'btn_text': latest_config.get('btn_text', '🔧'),
                    'btn_position': latest_config.get('btn_position', '右下'),
                    'btn_custom_css': latest_config.get('btn_custom_css', ''),
                }
                if float_cfg['exe_path']:
                    browse_window.evaluate_js('window.__webbox_setup_float_btn(' + json.dumps(float_cfg) + ')')
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
        webview.create_window('WebBox 设置', html=SETTINGS_HTML, js_api=api, width=540, height=740, resizable=False)
    
    webview.start(private_mode=False)

if __name__ == '__main__':
    main()
