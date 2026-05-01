#!/usr/bin/env python3
"""
编译并安装 protobuf 到 teamtalk/.sdk/protobuf/ 目录
支持 Windows(MinGW/MSYS2), Linux, macOS
统一使用 g++ 编译器和 make 构建系统

使用方法:
    python3 build_protobuf.py build     # 配置并编译（不安装）
    python3 build_protobuf.py install   # 编译并安装
    python3 build_protobuf.py clean     # 清理构建结果
    python3 build_protobuf.py all       # 完整流程：清理+编译+安装（默认）
"""

import os
import sys
import subprocess
import multiprocessing
import platform
import shutil
import argparse
from pathlib import Path


class ProtobufBuilder:
    """Protobuf 构建器 - 跨平台统一构建"""
    
    def __init__(self):
        # 获取脚本所在目录 (teamtalk-third)
        self.script_dir = Path(__file__).resolve().parent
        
        # .sdk 目录在脚本所在目录的父目录下
        self.install_dir = self.script_dir.parent / ".sdk" / "protobuf"
        
        # 设置源码目录
        self.protobuf_source_dir = self.script_dir / "protobuf-2.6.1"
        
        # 设置构建目录（统一在 build 目录下）
        self.build_dir = self.script_dir / "build" / "protobuf"
        
        # 获取CPU核心数
        self.cpu_count = multiprocessing.cpu_count()
        
        # 检测操作系统
        self.platform_name = platform.system()
        self.is_windows = self.platform_name == 'Windows'
    
    def run_command(self, cmd, shell=False, description=None):
        """执行命令并处理错误"""
        if description:
            print(f"\n{description}")
        
        print(f"执行命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        
        result = subprocess.run(cmd, shell=shell)
        
        if result.returncode != 0:
            print(f"错误: 命令执行失败 (退出码: {result.returncode})")
            sys.exit(1)
        
        return result
    
    def check_tool(self, tool):
        """检查工具是否存在"""
        return shutil.which(tool) is not None
    
    def is_configured(self):
        """检查是否已经配置过"""
        makefile = self.build_dir / "Makefile"
        return makefile.exists()
    
    def is_built(self):
        """检查是否已经编译过"""
        # 检查编译产物是否存在
        lib_file = self.build_dir / "src" / ".libs" / "libprotobuf.so"
        if not lib_file.exists():
            # 尝试其他可能的文件名
            lib_file = self.build_dir / "src" / ".libs" / "libprotobuf.dylib"
        if not lib_file.exists():
            lib_file = self.build_dir / "src" / ".libs" / "libprotobuf.a"
        return lib_file.exists()
    
    def clean(self):
        """清理之前的编译结果"""
        print("\n" + "="*60)
        print("清理编译结果")
        print("="*60)
        
        # 检查构建目录是否存在
        if self.build_dir.exists():
            print(f"删除构建目录: {self.build_dir}")
            try:
                shutil.rmtree(self.build_dir)
                print("✓ 清理完成!")
            except Exception as e:
                print(f"错误: 清理失败 - {e}")
                print(f"请手动删除: rm -rf {self.build_dir}")
                sys.exit(1)
        else:
            print("构建目录不存在，无需清理")
            print("✓ 已经是干净状态!")
    
    def check_environment(self):
        """检查编译环境"""
        print("\n" + "="*60)
        print("检查编译环境")
        print("="*60)
        print(f"操作系统: {self.platform_name}")
        print(f"Python版本: {sys.version.split()[0]}")
        print(f"CPU核心数: {self.cpu_count}")
        print(f"源码目录: {self.protobuf_source_dir}")
        print(f"构建目录: {self.build_dir}")
        print(f"安装目录: {self.install_dir}")
        
        # 检查源码目录
        if not self.protobuf_source_dir.exists():
            print(f"\n错误: protobuf源码目录不存在: {self.protobuf_source_dir}")
            sys.exit(1)
        
        # 检查必要工具
        required_tools = {
            'make': 'GNU Make 构建工具',
            'g++': 'C++ 编译器',
            'gcc': 'C 编译器'
        }
        
        print("\n检查必要工具:")
        missing_tools = []
        
        for tool, desc in required_tools.items():
            if self.check_tool(tool):
                print(f"  ✓ {tool} - {desc}")
            else:
                print(f"  ✗ {tool} - {desc} (未找到)")
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"\n错误: 缺少必要工具: {', '.join(missing_tools)}")
            self.print_install_instructions()
            sys.exit(1)
        
        print("\n✓ 环境检查通过!")
    
    def print_install_instructions(self):
        """打印工具安装说明"""
        print("\n" + "="*60)
        print("工具安装说明")
        print("="*60)
        
        if self.is_windows:
            print("\nWindows 平台 - 请安装 MSYS2 (推荐):")
            print("  1. 下载并安装 MSYS2: https://www.msys2.org/")
            print("  2. 在 MSYS2 终端中运行:")
            print("     pacman -S base-devel mingw-w64-x86_64-toolchain")
        else:
            print("\nLinux 平台:")
            print("  Ubuntu/Debian: sudo apt-get install build-essential")
            print("  CentOS/RHEL: sudo yum groupinstall 'Development Tools'")
            print("\nmacOS 平台:")
            print("  xcode-select --install")
    
    def configure(self):
        """配置 protobuf"""
        print("\n" + "="*60)
        print("配置 protobuf")
        print("="*60)
        
        if self.is_configured():
            print(f"检测到已配置过，跳过 configure")
            print(f"  如需重新配置，请先运行: python3 build_protobuf.py clean")
            return
        
        # 创建安装目录
        self.install_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建构建目录
        self.build_dir.mkdir(parents=True, exist_ok=True)
        print(f"创建构建目录: {self.build_dir}")
        
        # 进入构建目录
        os.chdir(self.build_dir)
        
        # 检查 configure 脚本
        configure_script = self.protobuf_source_dir / "configure"
        if not configure_script.exists():
            print("\n错误: 未找到 configure 脚本")
            print(f"请确认 {self.protobuf_source_dir} 目录完整")
            sys.exit(1)
        
        # 运行 configure
        configure_cmd = [
            'sh',
            str(configure_script),
            f'--prefix={self.install_dir}'
        ]
        self.run_command(configure_cmd, description="运行 configure")
        
        print("\n✓ 配置完成!")
    
    def do_build(self):
        """编译 protobuf"""
        print("\n" + "="*60)
        print("编译 protobuf")
        print("="*60)
        
        # 检查是否已配置
        if not self.is_configured():
            print("未检测到配置，先执行 configure...")
            self.configure()
        
        # 确保在构建目录
        os.chdir(self.build_dir)
        
        if self.is_built():
            print("检测到已编译过，跳过编译")
            print("  如需重新编译，请先运行: python3 build_protobuf.py clean")
            return
        
        # 运行 make
        make_cmd = ['make', f'-j{self.cpu_count}']
        self.run_command(make_cmd, description=f"使用 {self.cpu_count} 个CPU核心并行编译")
        
        print("\n✓ 编译完成!")
    
    def do_install(self):
        """安装 protobuf"""
        print("\n" + "="*60)
        print("安装 protobuf")
        print("="*60)
        
        # 检查是否已编译
        if not self.is_built():
            print("未检测到编译结果，先执行编译...")
            self.do_build()
        
        # 确保在构建目录
        os.chdir(self.build_dir)
        
        # 运行 make install
        install_cmd = ['make', 'install']
        self.run_command(install_cmd, description="安装到目标目录")
        
        print("\n✓ 安装完成!")
        
        # 打印使用说明
        self.print_usage()
    
    def print_usage(self):
        """打印使用说明"""
        bin_dir = self.install_dir / 'bin'
        lib_dir = self.install_dir / 'lib'
        protoc_name = 'protoc.exe' if self.is_windows else 'protoc'
        protoc_path = bin_dir / protoc_name
        
        print(f"\n" + "="*60)
        print("使用说明")
        print("="*60)
        print(f"安装位置: {self.install_dir}")
        print(f"protoc: {protoc_path}")
        
        print(f"\n验证安装:")
        print(f"  {protoc_path} --version")
        
        print(f"\n设置环境变量:")
        if self.is_windows:
            print(f"  # Windows (PowerShell)")
            print(f"  $env:Path = \"{bin_dir};$env:Path\"")
        else:
            print(f"  # Linux/macOS")
            print(f"  export PATH={bin_dir}:$PATH")
            print(f"  export LD_LIBRARY_PATH={lib_dir}:$LD_LIBRARY_PATH")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='protobuf 构建工具 - 支持 Linux/macOS/Windows',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令说明:
  build   - 配置并编译（不安装）
  install - 编译并安装到 teamtalk/.sdk/protobuf/
  clean   - 清理所有编译结果
  all     - 完整流程：清理 + 编译 + 安装（默认）

使用示例:
  python3 build_protobuf.py build      # 只编译
  python3 build_protobuf.py install    # 编译并安装
  python3 build_protobuf.py clean      # 清理
  python3 build_protobuf.py all        # 完整流程（默认）
  python3 build_protobuf.py            # 等同于 all
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='all',
        choices=['build', 'install', 'clean', 'all'],
        help='要执行的操作（默认: all）'
    )
    
    args = parser.parse_args()
    
    try:
        builder = ProtobufBuilder()
        
        # 除了 clean 命令，其他都需要先检查环境
        if args.command != 'clean':
            builder.check_environment()
        
        # 执行相应的命令
        if args.command == 'clean':
            builder.clean()
        
        elif args.command == 'build':
            builder.configure()
            builder.do_build()
            print("\n✓ 构建完成!")
            print("  运行以下命令安装: python3 build_protobuf.py install")
        
        elif args.command == 'install':
            builder.configure()
            builder.do_build()
            builder.do_install()
            print("\n✓ 全部完成!")
        
        elif args.command == 'all':
            print("\n" + "="*60)
            print("protobuf 完整构建流程")
            print("="*60)
            builder.clean()
            builder.configure()
            builder.do_build()
            builder.do_install()
            print("\n" + "="*60)
            print("✓ 全部完成!")
            print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        return 1
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
