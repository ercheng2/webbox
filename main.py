import webview
import json
import sys
import os
from pathlib import Path

def get_config_path():
    # 使用 AppData 目录，确保可写
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
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    default.update(loaded)
        except Exception as e:
            print(f"加载配置失败: {e}")
    return default

def save_to_file(config):
    config_file = get_config_path()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print(f"配置已保存到: {config_file}")
        return True
    except Exception as e:
        print(f"保存配置失败: {e}")
        return False

class Api:
    def __init__(self):
        self.config = load_config()
        self.window = None
    
    def set_window(self, window):
        self.window = window
    
    def save_config(self, url, title):
        self.config['url'] = url
        self.config['title'] = title
        result = save_to_file(self.config)
        # 更新窗口标题
        if self.window:
            self.window.title = title
        return {'status': 'ok', 'saved': result}
    
    def get_config(self):
        return self.config

def create_page(config):
    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebBox</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ width: 100%; height: 100%; overflow: hidden; font-family: Arial, sans-serif; }}
        .bar {{ 
            position: fixed; top: 0; left: 0; right: 0; height: 40px; 
            background: linear-gradient(180deg, #3a3a3a, #2d2d2d); 
            display: flex; align-items: center; 
            padding: 0 12px; z-index: 99999; gap: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        .bar button {{ 
            background: #555; border: 1px solid #666; color: #fff; 
            padding: 8px 16px; border-radius: 4px; cursor: pointer; 
            font-size: 13px; transition: all 0.2s;
        }}
        .bar button:hover {{ background: #666; border-color: #888; }}
        .bar .title {{ 
            color: #aaa; font-size: 12px; margin-left: auto; 
            max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }}
        .frame {{ position: fixed; top: 40px; left: 0; right: 0; bottom: 0; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        .dlg {{ 
            display: none; position: fixed; inset: 0; 
            background: rgba(0,0,0,0.6); z-index: 999999; 
            align-items: center; justify-content: center;
        }}
        .dlg.show {{ display: flex; }}
        .dlg-box {{ 
            background: #fff; padding: 28px; border-radius: 12px; 
            width: 420px; max-width: 90%; 
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }}
        .dlg-box h3 {{ margin: 0 0 20px; color: #333; text-align: center; font-size: 18px; }}
        .dlg-box label {{ display: block; margin-bottom: 6px; color: #555; font-size: 14px; }}
        .dlg-box input {{ 
            width: 100%; padding: 10px 12px; margin-bottom: 16px; 
            border: 1px solid #ddd; border-radius: 6px; font-size: 14px;
            transition: border-color 0.2s;
        }}
        .dlg-box input:focus {{ border-color: #4a9eff; outline: none; }}
        .dlg-box .btns {{ display: flex; gap: 12px; margin-top: 24px; }}
        .dlg-box button {{ 
            flex: 1; padding: 12px; border: none; border-radius: 6px; 
            cursor: pointer; font-size: 14px; font-weight: 500;
        }}
        .dlg-box .ok {{ background: #4a9eff; color: #fff; }}
        .dlg-box .ok:hover {{ background: #3a8eef; }}
        .dlg-box .no {{ background: #f0f0f0; color: #666; }}
        .dlg-box .no:hover {{ background: #e0e0e0; }}
        .hint {{ font-size: 12px; color: #888; margin-top: 12px; text-align: center; }}
    </style>
</head>
<body>
    <div class="bar">
        <button onclick="openDlg()">⚙️ 设置</button>
        <button onclick="reload()">🔄 刷新</button>
        <span class="title" id="titleDisplay">{config['title']}</span>
    </div>
    <div class="frame">
        <iframe id="frm" src="{config['url']}"></iframe>
    </div>
    <div class="dlg" id="dlg">
        <div class="dlg-box">
            <h3>WebBox 设置</h3>
            <label>网页地址</label>
            <input type="text" id="urlInput" value="{config['url']}" placeholder="https://example.com">
            <label>窗口标题</label>
            <input type="text" id="titleInput" value="{config['title']}" placeholder="WebBox">
            <div class="btns">
                <button class="ok" onclick="save()">保存</button>
                <button class="no" onclick="closeDlg()">取消</button>
            </div>
            <div class="hint">保存后自动刷新页面，配置会记住</div>
        </div>
    </div>
    <script>
        function openDlg() {{ 
            document.getElementById('dlg').classList.add('show');
            document.getElementById('urlInput').focus();
        }}
        function closeDlg() {{ 
            document.getElementById('dlg').classList.remove('show');
        }}
        function save() {{
            var url = document.getElementById('urlInput').value.trim();
            var title = document.getElementById('titleInput').value.trim();
            if (!url) {{
                alert('请输入网址');
                return;
            }}
            pywebview.api.save_config(url, title).then(function(result) {{
                document.getElementById('frm').src = url;
                document.getElementById('titleDisplay').textContent = title || 'WebBox';
                closeDlg();
            }});
        }}
        function reload() {{ 
            var f = document.getElementById('frm');
            f.src = f.src;
        }}
        // ESC 关闭对话框
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') closeDlg();
        }});
    </script>
</body>
</html>
'''

def main():
    config = load_config()
    api = Api()
    
    window = webview.create_window(
        title=config.get('title', 'WebBox'),
        html=create_page(config),
        js_api=api,
        fullscreen=True
    )
    api.set_window(window)
    webview.start()

if __name__ == '__main__':
    main()
