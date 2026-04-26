import webview
import json
import sys
import os
from pathlib import Path

def get_config_path():
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
        except:
            pass
    return default

def save_to_file(config):
    config_file = get_config_path()
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

class Api:
    def __init__(self, main_window=None):
        self.config = load_config()
        self.main_window = main_window
    
    def save_config(self, url, title):
        url = url.strip()
        if not url:
            url = 'https://www.baidu.com'
        if not url.startswith('http://') and not url.startswith('https://'):
            url = 'https://' + url
        
        self.config['url'] = url
        self.config['title'] = title.strip() or 'WebBox'
        save_to_file(self.config)
        
        # 重新加载主窗口
        if self.main_window:
            self.main_window.title = self.config['title']
            self.main_window.load_url(url)
        
        return {'status': 'ok', 'url': url}

def show_settings(api):
    """显示设置窗口"""
    config = api.config
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>设置</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ 
                font-family: "Microsoft YaHei", Arial, sans-serif; 
                padding: 30px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .box {{ 
                background: #fff; 
                padding: 40px; 
                border-radius: 16px; 
                width: 100%;
                max-width: 420px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            }}
            h3 {{ margin: 0 0 30px; color: #333; text-align: center; font-size: 22px; }}
            label {{ display: block; margin-bottom: 8px; color: #555; font-size: 14px; font-weight: 500; }}
            input {{ 
                width: 100%; padding: 14px 16px; margin-bottom: 24px; 
                border: 2px solid #e0e0e0; border-radius: 8px; font-size: 15px;
                transition: border-color 0.2s;
            }}
            input:focus {{ border-color: #667eea; outline: none; }}
            .btns {{ display: flex; gap: 14px; margin-top: 10px; }}
            button {{ 
                flex: 1; padding: 14px; border: none; border-radius: 8px; 
                cursor: pointer; font-size: 15px; font-weight: 600;
                transition: transform 0.1s;
            }}
            button:active {{ transform: scale(0.98); }}
            .ok {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; }}
            .no {{ background: #f0f0f0; color: #666; }}
            .hint {{ font-size: 13px; color: #888; margin-top: 20px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="box">
            <h3>🌐 WebBox 设置</h3>
            <label>网页地址</label>
            <input type="text" id="urlInput" value="{config['url']}" placeholder="https://example.com">
            <label>窗口标题</label>
            <input type="text" id="titleInput" value="{config['title']}" placeholder="WebBox">
            <div class="btns">
                <button class="ok" onclick="save()">✓ 保存并刷新</button>
                <button class="no" onclick="window.close()">取消</button>
            </div>
            <div class="hint">提示：网址可省略 https:// 前缀</div>
        </div>
        <script>
            document.getElementById('urlInput').focus();
            document.getElementById('urlInput').select();
            
            function save() {{
                var url = document.getElementById('urlInput').value.trim();
                var title = document.getElementById('titleInput').value.trim();
                if (!url) {{
                    alert('请输入网址');
                    return;
                }}
                pywebview.api.save_config(url, title).then(function() {{
                    window.close();
                }});
            }}
            
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') save();
                if (e.key === 'Escape') window.close();
            }});
        </script>
    </body>
    </html>
    '''
    
    settings = webview.create_window(
        'WebBox 设置',
        html=html,
        js_api=api,
        width=480,
        height=420,
        resizable=False,
        minimizable=False
    )

def main():
    config = load_config()
    
    # 创建主窗口 - 直接加载网页（不用iframe，解决跨域问题）
    main_window = webview.create_window(
        title=config.get('title', 'WebBox'),
        url=config.get('url', 'https://www.baidu.com'),
        fullscreen=True
    )
    
    api = Api(main_window)
    
    # 启动时先显示设置窗口
    def on_loaded():
        show_settings(api)
    
    # 延迟显示设置窗口
    import threading
    def show_settings_delayed():
        import time
        time.sleep(0.5)
        show_settings(api)
    
    t = threading.Thread(target=show_settings_delayed, daemon=True)
    t.start()
    
    webview.start()

if __name__ == '__main__':
    main()
