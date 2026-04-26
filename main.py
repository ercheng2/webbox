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
    
    def get_config(self):
        return self.config
    
    def save_config(self, url, title):
        self.config['url'] = url
        self.config['title'] = title
        save_config(self.config)
        return {'status': 'ok', 'url': url, 'title': title}

def create_main_html(config):
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <title>WebBox</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            html, body {{ 
                width: 100%; 
                height: 100%; 
                overflow: hidden;
                background: #1a1a2e;
            }}
            .settings-btn {{
                position: fixed;
                top: 15px;
                right: 15px;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: rgba(255,255,255,0.9);
                border: none;
                cursor: pointer;
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                transition: transform 0.2s;
            }}
            .settings-btn:hover {{
                transform: scale(1.1);
            }}
            .settings-btn svg {{
                width: 20px;
                height: 20px;
                fill: #333;
            }}
            .modal {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 100000;
                align-items: center;
                justify-content: center;
            }}
            .modal.show {{
                display: flex;
            }}
            .modal-content {{
                background: white;
                padding: 30px;
                border-radius: 12px;
                width: 400px;
                max-width: 90%;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }}
            .modal-content h2 {{
                margin: 0 0 20px 0;
                color: #333;
                text-align: center;
            }}
            .form-group {{
                margin-bottom: 15px;
            }}
            .form-group label {{
                display: block;
                margin-bottom: 5px;
                color: #666;
            }}
            .form-group input {{
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
            }}
            .form-group input:focus {{
                border-color: #4a9eff;
                outline: none;
            }}
            .buttons {{
                margin-top: 20px;
                display: flex;
                gap: 10px;
            }}
            .buttons button {{
                flex: 1;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
            }}
            .btn-save {{
                background: #4a9eff;
                color: white;
            }}
            .btn-save:hover {{
                background: #3a8eef;
            }}
            .btn-cancel {{
                background: #e0e0e0;
                color: #666;
            }}
            .btn-cancel:hover {{
                background: #d0d0d0;
            }}
            .tip {{
                margin-top: 15px;
                padding: 10px;
                background: #fffbe6;
                border-radius: 4px;
                font-size: 12px;
                color: #666;
            }}
            iframe {{
                width: 100%;
                height: 100%;
                border: none;
            }}
        </style>
    </head>
    <body>
        <button class="settings-btn" onclick="openSettings()" title="设置">
            <svg viewBox="0 0 24 24">
                <path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/>
            </svg>
        </button>
        
        <iframe id="webframe" src="{config['url']}"></iframe>
        
        <div class="modal" id="settingsModal">
            <div class="modal-content">
                <h2>WebBox 设置</h2>
                <div class="form-group">
                    <label>网页地址 (URL)</label>
                    <input type="text" id="urlInput" value="{config['url']}" placeholder="https://example.com">
                </div>
                <div class="form-group">
                    <label>窗口标题</label>
                    <input type="text" id="titleInput" value="{config['title']}" placeholder="WebBox">
                </div>
                <div class="buttons">
                    <button class="btn-save" onclick="saveSettings()">保存并刷新</button>
                    <button class="btn-cancel" onclick="closeSettings()">取消</button>
                </div>
                <div class="tip">
                    提示：保存后网页将自动刷新到新地址
                </div>
            </div>
        </div>
        
        <script>
            function openSettings() {{
                document.getElementById('settingsModal').classList.add('show');
            }}
            function closeSettings() {{
                document.getElementById('settingsModal').classList.remove('show');
            }}
            function saveSettings() {{
                var url = document.getElementById('urlInput').value;
                var title = document.getElementById('titleInput').value;
                pywebview.api.save_config(url, title).then(function(response) {{
                    document.getElementById('webframe').src = url;
                    closeSettings();
                }});
            }}
        </script>
    </body>
    </html>
    '''

def main():
    config = load_config()
    api = Api()
    
    # 创建主窗口，使用本地HTML
    html = create_main_html(config)
    
    window = webview.create_window(
        title=config.get('title', 'WebBox'),
        html=html,
        js_api=api,
        fullscreen=True
    )
    
    webview.start()

if __name__ == '__main__':
    main()
