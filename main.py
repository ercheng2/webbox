import webview
import json
import sys
from pathlib import Path

def get_config_path():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / 'webbox_config.json'
    return Path(__file__).parent / 'webbox_config.json'

def load_config():
    config_file = get_config_path()
    default = {'url': 'https://www.baidu.com', 'title': 'WebBox'}
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                default.update(json.load(f))
        except:
            pass
    return default

def save_config(config):
    config_file = get_config_path()
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

class Api:
    def __init__(self):
        self.config = load_config()
    
    def save_config(self, url, title):
        self.config['url'] = url
        self.config['title'] = title
        save_config(self.config)
        return {'status': 'ok'}

def create_page(config):
    return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebBox</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ width: 100%; height: 100%; overflow: hidden; }}
        .bar {{ 
            position: fixed; top: 0; left: 0; right: 0; height: 36px; 
            background: #2d2d2d; display: flex; align-items: center; 
            padding: 0 10px; z-index: 99999; gap: 8px;
        }}
        .bar button {{ 
            background: #444; border: none; color: #fff; 
            padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px;
        }}
        .bar button:hover {{ background: #666; }}
        .bar span {{ color: #888; font-size: 11px; margin-left: auto; }}
        .frame {{ position: fixed; top: 36px; left: 0; right: 0; bottom: 0; }}
        iframe {{ width: 100%; height: 100%; border: none; }}
        .dlg {{ 
            display: none; position: fixed; inset: 0; 
            background: rgba(0,0,0,0.5); z-index: 999999; 
            align-items: center; justify-content: center;
        }}
        .dlg.show {{ display: flex; }}
        .dlg-box {{ 
            background: #fff; padding: 24px; border-radius: 8px; 
            width: 360px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        .dlg-box h3 {{ margin: 0 0 16px; color: #333; text-align: center; }}
        .dlg-box label {{ display: block; margin-bottom: 4px; color: #666; font-size: 13px; }}
        .dlg-box input {{ 
            width: 100%; padding: 8px; margin-bottom: 12px; 
            border: 1px solid #ddd; border-radius: 4px; font-size: 14px;
        }}
        .dlg-box .btns {{ display: flex; gap: 8px; margin-top: 16px; }}
        .dlg-box button {{ flex: 1; padding: 8px; border: none; border-radius: 4px; cursor: pointer; }}
        .dlg-box .ok {{ background: #4a9eff; color: #fff; }}
        .dlg-box .no {{ background: #eee; color: #666; }}
    </style>
</head>
<body>
    <div class="bar">
        <button onclick="openDlg()">设置</button>
        <button onclick="reload()">刷新</button>
        <span>WebBox</span>
    </div>
    <div class="frame">
        <iframe id="frm" src="{config['url']}"></iframe>
    </div>
    <div class="dlg" id="dlg">
        <div class="dlg-box">
            <h3>设置</h3>
            <label>网址</label>
            <input type="text" id="u" value="{config['url']}">
            <label>标题</label>
            <input type="text" id="t" value="{config['title']}">
            <div class="btns">
                <button class="ok" onclick="save()">保存</button>
                <button class="no" onclick="closeDlg()">取消</button>
            </div>
        </div>
    </div>
    <script>
        function openDlg() {{ document.getElementById('dlg').classList.add('show'); }}
        function closeDlg() {{ document.getElementById('dlg').classList.remove('show'); }}
        function save() {{
            pywebview.api.save_config(document.getElementById('u').value, document.getElementById('t').value)
                .then(function() {{ 
                    document.getElementById('frm').src = document.getElementById('u').value;
                    closeDlg(); 
                }});
        }}
        function reload() {{ var f = document.getElementById('frm'); f.src = f.src; }}
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
    webview.start()

if __name__ == '__main__':
    main()
