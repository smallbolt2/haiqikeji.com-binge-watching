# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_all

# 分析主程序
a = Analysis(
    ['app.py'],                     # 主入口脚本
    pathex=[],                      # 额外模块搜索路径（通常留空）
    binaries=[],                    # 二进制依赖（如 .dll/.so）
    datas=[
        # 将这三个文件夹打包进 exe，运行时解压到临时目录
        ('templates', 'templates'),
        ('static', 'static'),
        ('mooc', 'mooc'),
        # 注意：config.json 不在这里，所以不会打包进 exe
    ],
    hiddenimports=[        # 关键：强制包含异步服务器依赖
        'gevent',
        'gevent.monkey',
        'gevent.websocket',
        'engineio.async_drivers.gevent',
        'engineio.async_drivers.threading',
        'socketio',
        'engineio',
        'simple_websocket',   # 某些版本需要
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# 打包为 PYZ（加密Python字节码）
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 生成可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='smallbolt2',                     # 输出的 exe 名称（不含 .exe）
    debug=False,
    strip=False,
    upx=True,                       # 使用 UPX 压缩（需安装 upx）
    console=True,                   # 显示控制台窗口（命令行程序或调试用）
    icon='icon.ico',                # 设置 exe 图标
    # version='version.txt',        # 可选：版本信息文件
    # uac_admin=False,              # 可选：是否需要管理员权限
)

# 如果希望生成多文件模式（非单文件），可以使用 COLLECT
# 单文件模式下不需要 COLLECT，上面 EXE 已经生成最终 exe