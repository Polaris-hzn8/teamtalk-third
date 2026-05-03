#!/usr/bin/env python3
"""
编译并安装 jsoncpp 到 teamtalk/.sdk/jsoncpp/ 目录（供其他进程 / CMake find_package / pkg-config 使用）。
默认仅编译静态库（libjsoncpp.a），不使用动态库。
使用 CMake 外部构建：源码在 jsoncpp/，产物在 build/jsoncpp/。
配置阶段在构建目录内执行「cmake <源码绝对路径>」（兼容 CMake 3.10+，不依赖 -S/-B）。

使用方法:
    python3 build_jsoncpp.py build     # 配置并编译（不安装）
    python3 build_jsoncpp.py install   # 编译并安装
    python3 build_jsoncpp.py clean     # 清理构建目录
    python3 build_jsoncpp.py all       # 清理 + 配置 + 编译 + 安装（默认）
"""

import sys
import subprocess
import multiprocessing
import platform
import shutil
import argparse
from pathlib import Path

def _banner(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

class JsoncppBuilder:
    """jsoncpp 构建器（CMake）"""

    def __init__(self):
        self.script_dir = Path(__file__).resolve().parent
        self.install_dir = self.script_dir.parent / ".sdk" / "jsoncpp"
        self.jsoncpp_source_dir = self.script_dir / "jsoncpp"
        self.build_dir = self.script_dir / "build" / "jsoncpp"
        self.cpu_count = multiprocessing.cpu_count()
        self.platform_name = platform.system()
        self.is_windows = self.platform_name == "Windows"

    def run_command(self, cmd, shell=False, description=None, cwd=None):
        if description:
            print(f"\n{description}")
        if cwd:
            print(f"工作目录: {cwd}")
        print(f"执行命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        result = subprocess.run(cmd, shell=shell, cwd=cwd)
        if result.returncode != 0:
            print(f"错误: 命令执行失败 (退出码: {result.returncode})")
            sys.exit(1)
        return result

    @staticmethod
    def _which(name):
        return shutil.which(name) is not None

    def _release_args(self):
        """Windows 下 Visual Studio 等多配置生成器需要指定构建类型。"""
        return ["--config", "Release"] if self.is_windows else []

    def is_configured(self):
        return (self.build_dir / "CMakeCache.txt").exists()

    def clean(self):
        _banner("清理编译结果")
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
        _banner("检查编译环境")
        print(f"操作系统: {self.platform_name}")
        print(f"Python版本: {sys.version.split()[0]}")
        print(f"CPU核心数: {self.cpu_count}")
        print(f"源码目录: {self.jsoncpp_source_dir}")
        print(f"构建目录: {self.build_dir}")
        print(f"安装目录: {self.install_dir}")

        if not self.jsoncpp_source_dir.exists():
            print(f"\n错误: jsoncpp 源码目录不存在: {self.jsoncpp_source_dir}")
            sys.exit(1)
        if not (self.jsoncpp_source_dir / "CMakeLists.txt").exists():
            print(f"\n错误: 未找到 {self.jsoncpp_source_dir / 'CMakeLists.txt'}")
            sys.exit(1)

        missing = []
        print("\n检查必要工具:")
        if self._which("cmake"):
            print("  ✓ cmake")
        else:
            print("  ✗ cmake (未找到)")
            missing.append("cmake")

        cxx = next((t for t in ("g++", "clang++", "cl") if self._which(t)), None)
        if cxx:
            print(f"  ✓ {cxx} - C++ 编译器")
        else:
            print("  ✗ C++ 编译器 (需要 g++、clang++ 或 Windows 下 cl)")
            missing.append("c++")

        if missing:
            print(f"\n错误: 缺少必要工具: {', '.join(missing)}")
            print("\n请安装 CMake 与 C++ 编译器。")
            print("  Linux: sudo apt-get install cmake build-essential")
            print("  macOS: brew install cmake ; xcode-select --install")
            print("  Windows: CMake + MSYS2 (pacman -S mingw-w64-x86_64-toolchain cmake)")
            sys.exit(1)

        print("\n✓ 环境检查通过!")

    def configure(self):
        _banner("配置 jsoncpp (CMake)")

        if self.is_configured():
            print("检测到已配置过，跳过 cmake 配置")
            print("  如需重新配置，请先运行: python3 build_jsoncpp.py clean")
            return

        self.install_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)

        src = str(self.jsoncpp_source_dir.resolve())
        cmake_cmd = [
            "cmake",
            f"-DCMAKE_INSTALL_PREFIX={self.install_dir}",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DJSONCPP_WITH_TESTS=OFF",
            "-DJSONCPP_WITH_POST_BUILD_UNITTEST=OFF",
            "-DJSONCPP_WITH_EXAMPLE=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DBUILD_STATIC_LIBS=ON",
            src,
        ]
        self.run_command(
            cmake_cmd,
            cwd=str(self.build_dir),
            description="运行 cmake 生成构建文件",
        )
        print("\n✓ 配置完成!")

    def do_build(self):
        _banner("编译 jsoncpp")

        if not self.is_configured():
            print("未检测到配置，先执行 cmake 配置...")
            self.configure()

        build_dir = str(self.build_dir)

        if self.is_windows:
            # Visual Studio 等多配置生成器必须指定 Release / Debug
            build_cmd = [
                "cmake",
                "--build",
                build_dir,
                "--config",
                "Release",
            ]
        else:
            # 并行选项跟在 -- 后面，交给 make / ninja，兼容旧版 CMake（无需 cmake --parallel）
            build_cmd = [
                "cmake",
                "--build",
                build_dir,
                "--",
                "-j" + str(self.cpu_count),
            ]

        self.run_command(build_cmd, description="编译 jsoncpp")
        print("\n✓ 编译完成!")

    def do_install(self):
        _banner("安装 jsoncpp")

        install_cmd = [
            "cmake",
            "--build",
            str(self.build_dir),
            "--target",
            "install",
        ] + self._release_args()
        self.run_command(install_cmd, description="安装到 .sdk/jsoncpp")
        print("\n✓ 安装完成!")
        self.print_usage()

    def print_usage(self):
        inc_dir = self.install_dir / "include"
        lib_dir = self.install_dir / "lib"
        cmake_dir = lib_dir / "cmake" / "jsoncpp"
        pc_dir = lib_dir / "pkgconfig"

        _banner("其他工程如何使用本 SDK")
        print(f"安装根目录: {self.install_dir}")
        print(f"头文件:     {inc_dir}")
        print(f"库目录:     {lib_dir}")
        print(f"CMake 包:   {cmake_dir} (若已生成)")
        print(f"pkg-config: {pc_dir / 'jsoncpp.pc'} (若已生成)")

        print("\nCMake 示例 (find_package):")
        print(f'  cmake -DCMAKE_PREFIX_PATH="{self.install_dir}" ..')

        print("\n说明: 当前为仅静态库安装，链接时指定库路径即可，一般无需设置 LD_LIBRARY_PATH。")
        print("\n编译 / 链接时环境变量 (Linux/macOS):")
        print(f'  export CMAKE_PREFIX_PATH="{self.install_dir}:$CMAKE_PREFIX_PATH"')
        print(f'  export PKG_CONFIG_PATH="{pc_dir}:$PKG_CONFIG_PATH"')

        if self.is_windows:
            print("\nWindows (PowerShell):")
            print(f'  $env:CMAKE_PREFIX_PATH = "{self.install_dir};$env:CMAKE_PREFIX_PATH"')


def main():
    parser = argparse.ArgumentParser(
        description="jsoncpp 构建工具 — 安装到 teamtalk/.sdk/jsoncpp/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  build   - CMake 配置并编译（不安装）
  install - 编译并安装到 teamtalk/.sdk/jsoncpp/
  clean   - 删除 build/jsoncpp/
  all     - clean + configure + build + install（默认）

示例:
  python3 build_jsoncpp.py install
  python3 build_jsoncpp.py clean && python3 build_jsoncpp.py build
        """,
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="all",
        choices=["build", "install", "clean", "all"],
        help="要执行的操作（默认: all）",
    )

    args = parser.parse_args()

    try:
        builder = JsoncppBuilder()

        if args.command != "clean":
            builder.check_environment()

        if args.command == "clean":
            builder.clean()
        elif args.command == "build":
            builder.configure()
            builder.do_build()
            print("\n✓ 构建完成!")
            print("  安装请运行: python3 build_jsoncpp.py install")
        elif args.command == "install":
            builder.configure()
            builder.do_build()
            builder.do_install()
            print("\n✓ 安装流程结束!")
        elif args.command == "all":
            _banner("jsoncpp 完整构建流程")
            builder.clean()
            builder.configure()
            builder.do_build()
            builder.do_install()
            print("\n" + "=" * 60)
            print("✓ 全部完成!")
            print("=" * 60)

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
