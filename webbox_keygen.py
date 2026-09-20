# -*- coding: utf-8 -*-
"""
WebBox 注册机 — 输入机器码，生成激活码
独立工具，带 GUI 界面
依赖：仅 Python 标准库（tkinter）
"""

import sys
import hashlib
import hmac

# ===== 密钥（必须与 license_core.py 中的 _SECRET 一致） =====
_SECRET = b"YDC-WebBox-Licensed-2026!@#"


def generate_activation_key(machine_code):
    """根据机器码生成激活码"""
    payload = machine_code.upper().replace('-', '')
    key = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:24].upper()
    return f"{key[:6]}-{key[6:12]}-{key[12:18]}-{key[18:24]}"


def generate_key_cli(machine_code):
    """命令行模式生成激活码"""
    return generate_activation_key(machine_code)


# ===== GUI =====
def run_gui():
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("WebBox 注册机 v1.0")
    root.geometry("480x280")
    root.resizable(False, False)

    # 标题
    title = tk.Label(root, text="WebBox 注册机", font=("Microsoft YaHei", 16, "bold"))
    title.pack(pady=15)

    # 输入区域
    frame1 = tk.Frame(root)
    frame1.pack(fill=tk.X, padx=20, pady=5)
    tk.Label(frame1, text="机器码：", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
    machine_entry = tk.Entry(frame1, font=("Consolas", 11), width=38)
    machine_entry.pack(side=tk.LEFT, padx=5)

    # 生成按钮
    def on_generate():
        code = machine_entry.get().strip()
        if not code:
            messagebox.showwarning("提示", "请输入机器码")
            return
        try:
            key = generate_activation_key(code)
            result_entry.delete(0, tk.END)
            result_entry.insert(0, key)
        except Exception as e:
            messagebox.showerror("错误", f"生成失败：{e}")

    btn = tk.Button(root, text="生成激活码", font=("Microsoft YaHei", 11, "bold"),
                    command=on_generate, bg="#667eea", fg="white",
                    activebackground="#764ba2", width=15, height=1)
    btn.pack(pady=10)

    # 结果区域
    frame2 = tk.Frame(root)
    frame2.pack(fill=tk.X, padx=20, pady=5)
    tk.Label(frame2, text="激活码：", font=("Microsoft YaHei", 10)).pack(side=tk.LEFT)
    result_entry = tk.Entry(frame2, font=("Consolas", 11), width=38)
    result_entry.pack(side=tk.LEFT, padx=5)

    # 复制按钮
    def on_copy():
        key = result_entry.get().strip()
        if key:
            root.clipboard_clear()
            root.clipboard_append(key)
            messagebox.showinfo("提示", "激活码已复制到剪贴板")

    copy_btn = tk.Button(root, text="复制激活码", font=("Microsoft YaHei", 9),
                         command=on_copy, width=15)
    copy_btn.pack(pady=5)

    # 说明
    info = tk.Label(root, text="提示：机器码来自 WebBox 设置页面\n激活码生成后请发给客户输入激活",
                    font=("Microsoft YaHei", 8), fg="gray")
    info.pack(pady=10)

    # 开机时聚焦到输入框
    machine_entry.focus_set()

    # 回车触发
    machine_entry.bind('<Return>', lambda e: on_generate())

    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 命令行模式：直接传入机器码
        code = sys.argv[1]
        key = generate_key_cli(code)
        print(f"机器码: {code}")
        print(f"激活码: {key}")
    else:
        # GUI 模式
        run_gui()
