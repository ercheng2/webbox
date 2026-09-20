# -*- coding: utf-8 -*-
"""
WebBox 授权管理核心模块
功能：机器码生成、试用期校验、防时间篡改、激活码验证
依赖：仅 Python 标准库
"""

import os
import sys
import json
import hashlib
import hmac
import time
import struct
from datetime import datetime, timedelta
from pathlib import Path

# ===== 密钥（发布前可修改，keygen 必须用同一个） =====
_SECRET = b"YDC-WebBox-Licensed-2026!@#"
_TRIAL_DAYS = 30

# ===== 授权文件路径 =====
def _license_dir():
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', '.')) / 'WebBox'
    return Path.home() / '.webbox'

def _get_license_path():
    d = _license_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / '.wbx_license'


# ===== 机器码生成 =====
def get_machine_id():
    """采集硬件信息，返回 (显示用机器码, 原始硬件串)"""
    parts = []

    # CPU 序列号
    try:
        import subprocess
        r = subprocess.run(['wmic', 'cpu', 'get', 'ProcessorId'],
                           capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().split('\n')
        if len(lines) >= 2:
            v = lines[1].strip()
            if v:
                parts.append('CPU:' + v)
    except Exception:
        pass

    # 主板序列号
    try:
        import subprocess
        r = subprocess.run(['wmic', 'baseboard', 'get', 'SerialNumber'],
                           capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().split('\n')
        if len(lines) >= 2:
            v = lines[1].strip()
            if v and v.lower() not in ('', 'to be filled by o.e.m.', 'default string'):
                parts.append('MB:' + v)
    except Exception:
        pass

    # 硬盘序列号
    try:
        import subprocess
        r = subprocess.run(['wmic', 'diskdrive', 'get', 'SerialNumber'],
                           capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().split('\n')
        if len(lines) >= 2:
            v = lines[1].strip()
            if v:
                parts.append('HD:' + v)
    except Exception:
        pass

    # 兜底
    if not parts:
        try:
            import socket, getpass
            parts.append(f"HOST:{socket.gethostname()}-{getpass.getuser()}")
        except Exception:
            parts.append("FALLBACK:UNKNOWN")

    raw = "|".join(parts)
    h = hashlib.sha256((raw + _SECRET.decode()).encode()).hexdigest()[:32].upper()
    formatted = f"{h[:8]}-{h[8:16]}-{h[16:24]}-{h[24:32]}"
    return formatted, raw


# ===== 激活码生成与验证 =====
def generate_activation_key(machine_code):
    """注册机调用：根据机器码生成激活码"""
    payload = machine_code.upper().replace('-', '')
    key = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:24].upper()
    return f"{key[:6]}-{key[6:12]}-{key[12:18]}-{key[18:24]}"


def verify_activation_key(machine_code, activation_key):
    """WebBox 调用：验证激活码"""
    expected = generate_activation_key(machine_code)
    return activation_key.upper().replace('-', '') == expected.upper().replace('-', '')


# ===== 加密/解密 =====
def _derive_key(machine_code):
    """基于机器码派生加密密钥"""
    return hashlib.sha256((machine_code + _SECRET.decode()).encode()).digest()


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    for i in range(len(data)):
        out[i] = data[i] ^ key[i % len(key)]
    return bytes(out)


def _save_state(machine_code, state):
    """加密保存完整授权状态（单文件，含时间戳和激活信息）"""
    raw = json.dumps(state).encode()
    key = _derive_key(machine_code)
    enc = _xor_encrypt(raw, key)
    mac = hmac.new(key, enc, hashlib.sha256).digest()
    with open(_get_license_path(), 'wb') as f:
        f.write(mac[:16] + enc)


def _load_state(machine_code):
    """读取并解密完整授权状态；文件不存在或已被篡改返回 None"""
    path = _get_license_path()
    if not path.exists():
        return None
    try:
        key = _derive_key(machine_code)
        raw = path.read_bytes()
        if len(raw) < 20:
            return None
        stored_mac = raw[:16]
        enc = raw[16:]
        expected_mac = hmac.new(key, enc, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(stored_mac, expected_mac):
            return None  # 被篡改
        dec = _xor_encrypt(enc, key)
        return json.loads(dec)
    except Exception:
        return None


# ===== 网络时间获取 =====
_NTP_TO_UNIX = 2208988800  # NTP epoch(1900) 到 Unix epoch(1970) 的秒数

def _get_ntp_time():
    """尝试获取 NTP 网络时间，失败返回 None"""
    servers = [('ntp.aliyun.com', 'ntp1.aliyun.com'), ('ntp.tencent.com', 'ntp.ntsc.ac.cn')]
    for primary, backup in servers:
        for host in (primary, backup):
            try:
                import socket
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client.settimeout(4)
                data = b'\x1b' + 47 * b'\0'
                client.sendto(data, (host, 123))
                msg, _ = client.recvfrom(1024)
                client.close()
                t = struct.unpack('!12I', msg)
                secs = t[10]
                frac = t[11]
                return secs - _NTP_TO_UNIX + frac / 2**32
            except Exception:
                continue
    return None


# ===== 核心：检查授权状态 =====
def check_license():
    """
    检查授权状态，返回结果字典：
    {
        'status': 'ok' | 'trial' | 'expired' | 'tampered',
        'machine_code': str,
        'days_left': int,
        'activated': bool,
        'activated_at': str,
        'message': str,
    }
    """
    machine_code, _ = get_machine_id()
    now = time.time()
    state = _load_state(machine_code)

    # 首次运行：初始化
    if state is None:
        state = {
            'v': 1,
            'first_run': now,
            'last_ts': now,
            'activated': False,
            'activation_key': '',
            'activated_at': '',
        }
        _save_state(machine_code, state)

    last_ts = state.get('last_ts', now)

    # 2. 防篡改：时间倒退（允许 1 小时误差应对时区/夏令时）
    if now < last_ts - 3600:
        return {
            'status': 'tampered',
            'machine_code': machine_code,
            'days_left': 0,
            'activated': False,
            'activated_at': '',
            'message': '检测到系统时间被回拨，请恢复正确时间后重试。',
        }

    # 3. 防篡改：时间大幅前跳（超 1 年），用 NTP 交叉校验
    if now > last_ts + 365 * 86400:
        ntp = _get_ntp_time()
        if ntp and abs(now - ntp) > 86400:
            return {
                'status': 'tampered',
                'machine_code': machine_code,
                'days_left': 0,
                'activated': False,
                'activated_at': '',
                'message': '检测到系统时间与网络时间偏差过大，请同步正确时间后重试。',
            }

    # 更新最后运行时间戳（单调递增）
    state['last_ts'] = now

    # 4. 检查激活状态
    if state.get('activated'):
        if verify_activation_key(machine_code, state.get('activation_key', '')):
            _save_state(machine_code, state)
            return {
                'status': 'ok',
                'machine_code': machine_code,
                'days_left': -1,
                'activated': True,
                'activated_at': state.get('activated_at', ''),
                'message': '',
            }

    # 5. 试用期检查
    first_ts = state.get('first_run', now)
    elapsed_days = int((now - first_ts) / 86400)
    days_left = max(0, _TRIAL_DAYS - elapsed_days)

    _save_state(machine_code, state)

    if days_left <= 0:
        return {
            'status': 'expired',
            'machine_code': machine_code,
            'days_left': 0,
            'activated': False,
            'activated_at': '',
            'message': f'试用期已结束（{_TRIAL_DAYS}天），请联系软件提供方获取激活码。',
        }

    return {
        'status': 'trial',
        'machine_code': machine_code,
        'days_left': days_left,
        'activated': False,
        'activated_at': '',
        'message': f'试用期剩余 {days_left} 天',
    }


def activate(machine_code, activation_key):
    """
    执行激活，返回结果：{'success': bool, 'message': str}
    """
    activation_key = (activation_key or '').strip().upper().replace('-', '')
    if not verify_activation_key(machine_code, activation_key):
        return {'success': False, 'message': '激活码无效，请检查后重试。'}

    state = _load_state(machine_code) or {
        'v': 1,
        'first_run': time.time(),
        'last_ts': time.time(),
    }
    state['activated'] = True
    state['activation_key'] = activation_key
    state['activated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    state['last_ts'] = time.time()
    _save_state(machine_code, state)

    return {
        'success': True,
        'message': '激活成功！已永久授权本机使用。',
    }


def get_machine_code_display():
    """获取用于显示的机器码"""
    code, _ = get_machine_id()
    return code