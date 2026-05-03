#!/usr/bin/env python3
"""
将 spdlog 头文件安装到 teamtalk/.sdk/spdlog/（纯头文件库，无需编译）。

与 teamtalk-imcore 的 CMake 一致：
  include_directories(\${SDK_DIR}/spdlog/include)
  #include <spdlog/spdlog.h>

使用方法:
    python3 build_spdlog.py install   # 拷贝头文件到 .sdk/spdlog/include/
    python3 build_spdlog.py clean     # 删除 .sdk/spdlog/
    python3 build_spdlog.py all       # clean + install（默认）
"""

import argparse
import shutil
import sys
from pathlib import Path


def banner(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


class SpdlogInstaller:
    def __init__(self):
        self.script_dir = Path(__file__).resolve().parent
        self.src_include = self.script_dir / "spdlog" / "include"
        self.install_root = self.script_dir.parent / ".sdk" / "spdlog"
        self.dest_include = self.install_root / "include"

    def check_source(self):
        if not self.src_include.is_dir():
            print(f"错误: 未找到 spdlog 头文件目录: {self.src_include}")
            sys.exit(1)
        marker = self.src_include / "spdlog" / "spdlog.h"
        if not marker.is_file():
            print(f"错误: 未找到 {marker}，请确认 spdlog 源码完整")
            sys.exit(1)

    def clean(self):
        banner("清理 .sdk/spdlog")
        if self.install_root.exists():
            shutil.rmtree(self.install_root)
            print(f"已删除: {self.install_root}")
        else:
            print("目录不存在，跳过")
        print("✓ 清理完成")

    def install(self):
        banner("安装 spdlog 头文件")
        self.check_source()

        if self.dest_include.exists():
            shutil.rmtree(self.dest_include)

        self.install_root.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.src_include, self.dest_include)

        ver_h = self.dest_include / "spdlog" / "version.h"
        ver = ""
        if ver_h.is_file():
            text = ver_h.read_text(encoding="utf-8", errors="replace")
            for line in text.splitlines():
                if line.startswith("#define SPDLOG_VER_MAJOR"):
                    ver = line
                    break

        print(f"源目录: {self.src_include}")
        print(f"目标:   {self.dest_include}")
        if ver:
            print(f"版本:   {ver.strip()}")
        print("✓ 安装完成")
        print("\nCMake 中使用: include_directories(${SDK_DIR}/spdlog/include)")
        print("代码中:       #include <spdlog/spdlog.h>")


def main():
    parser = argparse.ArgumentParser(
        description="将 spdlog 头文件复制到 teamtalk/.sdk/spdlog/（无需编译）"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["install", "clean", "all"],
        help="install / clean / all（默认 all）",
    )
    args = parser.parse_args()

    try:
        app = SpdlogInstaller()
        if args.command == "clean":
            app.clean()
        elif args.command == "install":
            app.install()
        else:
            banner("spdlog 完整安装流程")
            app.clean()
            app.install()
            print("\n✓ 全部完成")
        return 0
    except KeyboardInterrupt:
        print("\n已中断")
        return 1


if __name__ == "__main__":
    sys.exit(main())
