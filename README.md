# WebBox - 网页全屏盒子

一个使用PyQt5 QWebEngineView开发的全屏网页展示工具，无地址栏、无边框，专注于纯净的网页展示体验。

## 功能特性

- 🚀 全屏网页展示 - 无地址栏、无边框、无标题栏
- ⚙️ 配置文件管理 - JSON配置网址列表
- ⌨️ 快捷键支持 - ESC/Ctrl+Q退出，Ctrl+Left/Right切换网页
- 🖱️ 完整交互支持 - 触摸、鼠标点击、滚动
- 🔄 页面刷新 - F5/Ctrl+R
- 🛠️ 开发者工具 - F12开关

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| ESC / Ctrl+Q | 退出程序 |
| Ctrl+Left | 上一个网页 |
| Ctrl+Right | 下一个网页 |
| F5 / Ctrl+R | 刷新页面 |
| F12 | 切换开发者工具 |

## 配置文件

编辑 `webbox_config.json` 自定义网址和设置：

```json
{
    "websites": [
        {"name": "百度", "url": "https://www.baidu.com"},
        {"name": "Google", "url": "https://www.google.com"}
    ],
    "default_index": 0,
    "hotkeys": {
        "quit": ["Escape", "Ctrl+Q"]
    }
}
```

## 依赖

- Python 3.8+
- PyQt5 5.15+
- PyQtWebEngine 5.15+

## 安装运行

```bash
pip install -r requirements.txt
python main.py
```

## Windows打包版

从 [Releases](https://github.com/YOUR_USERNAME/webbox/releases) 下载 `WebBox.exe`

## 许可证

MIT License
