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

if __name__ == '__main__':
    config = load_config()
    window = webview.create_window(
        title=config.get('title', 'WebBox'),
        url=config.get('url', 'https://www.baidu.com'),
        fullscreen=True
    )
    webview.start()