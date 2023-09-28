import os
import subprocess
import shutil
import urllib.request

# Helper functions
def run_cmd(cmd, capture_output=False):
    result = subprocess.run(cmd, capture_output=capture_output, text=True, shell=True)
    if result.returncode != 0:
        raise Exception(f"Command failed with error {result.returncode}: {result.stderr}")
    if capture_output:
        return result.stdout

def mkdir_p(path):
    os.makedirs(path, exist_ok=True)

def rm_rf(path):
    shutil.rmtree(path, ignore_errors=True)

# Translate Makefile and build.sh to Python functions

def get_env_vars():
    GOOS = run_cmd("go env GOOS", capture_output=True).strip()
    GOARCH = run_cmd("go env GOARCH", capture_output=True).strip()
    GOOS_GOARCH = f"{GOOS}_{GOARCH}"
    GOOS_GOARCH_NATIVE = f"{run_cmd('go env GOHOSTOS', capture_output=True).strip()}_{run_cmd('go env GOHOSTARCH', capture_output=True).strip()}"
    
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    DEST = os.path.join(ROOT_DIR, "dist", GOOS_GOARCH)
    DEST_LIB = os.path.join(DEST, "lib")
    DEST_INCLUDE = os.path.join(DEST, "include")
    
    return GOOS, GOARCH, GOOS_GOARCH, GOOS_GOARCH_NATIVE, ROOT_DIR, DEST, DEST_LIB, DEST_INCLUDE

def prepare(DEST, DEST_LIB, DEST_INCLUDE):
    rm_rf(DEST)
    mkdir_p(DEST_LIB)
    mkdir_p(DEST_INCLUDE)

# Modify the build function to conditionally set the compiler flags based on the platform

def build(DEST, ROOT_DIR):
    DIRECTORY = ROOT_DIR
    
    GOOS, GOARCH, _, _, _, _, _, _ = get_env_vars()
    
    INSTALL_PREFIX = DEST

    BUILD_FLAGS = "-fPIC -O3 -pipe"
    BUILD_PATH = "/tmp/build"
    mkdir_p(BUILD_PATH)

    CMAKE_REQUIRED_PARAMS = "-DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_INSTALL_PREFIX={} -DPORTABLE=1 -DWITH_CORE_TOOLS=OFF".format(INSTALL_PREFIX)

    CMAKE_CXX_FLAGS = ""
    CMAKE_C_FLAGS = ""

    if GOOS == "linux":
        CMAKE_CXX_FLAGS = "-Wno-cast-function-type"
        CMAKE_C_FLAGS = "-Wno-error=cast-function-type"

    if GOOS == "linux" and GOARCH == "arm64":
        os.environ["DIST_DIR"] = INSTALL_PREFIX
        CMAKE_REQUIRED_PARAMS = "-DCMAKE_TOOLCHAIN_FILE={}/linux_arm64.cmake {}".format(DIRECTORY, CMAKE_REQUIRED_PARAMS)
    elif GOOS == "darwin" and GOARCH == "arm64":
        os.environ["DIST_DIR"] = INSTALL_PREFIX
        BUILD_FLAGS = "-target arm64-apple-macos11 {}".format(BUILD_FLAGS)
        CMAKE_REQUIRED_PARAMS = "-DCMAKE_TOOLCHAIN_FILE={}/darwin_arm64.cmake {}".format(DIRECTORY, CMAKE_REQUIRED_PARAMS)
    elif GOOS == "windows":
        os.environ["DIST_DIR"] = INSTALL_PREFIX
        BUILD_FLAGS = "-fPIC -O3 -pipe"
        CMAKE_REQUIRED_PARAMS = "-DROCKSDB_INSTALL_ON_WINDOWS=ON -DCMAKE_TOOLCHAIN_FILE={}/win64.cmake {}".format(DIRECTORY, CMAKE_REQUIRED_PARAMS)

    os.environ["CFLAGS"] = BUILD_FLAGS
    os.environ["CXXFLAGS"] = BUILD_FLAGS

    print("Building rocksdb for {} {}...".format(GOOS, GOARCH))

    rocksdb_version = "7.8.3"
    
    # Downloading the tar.gz and building it
    url = "https://github.com/facebook/rocksdb/archive/v{}.tar.gz".format(rocksdb_version)
    tar_file = os.path.join(BUILD_PATH, "v{}.tar.gz".format(rocksdb_version))
    rocksdb_dir = os.path.join(BUILD_PATH, "rocksdb-{}".format(rocksdb_version))
    build_place_dir = os.path.join(rocksdb_dir, "build_place")
    
    urllib.request.urlretrieve(url, tar_file)
    shutil.unpack_archive(tar_file, BUILD_PATH)
    
    mkdir_p(build_place_dir)
    os.chdir(build_place_dir)

    cmake_cmd = (
        "cmake "
        "-DCMAKE_BUILD_TYPE=Release "
        "{} "  # This is for CMAKE_REQUIRED_PARAMS
        "-DCMAKE_CXX_FLAGS='{}' "  # This is for CMAKE_CXX_FLAGS
        "-DCMAKE_C_FLAGS='{}' "    # This is for CMAKE_C_FLAGS
        "-DCMAKE_PREFIX_PATH={} "  # This is for INSTALL_PREFIX
        "-DWITH_TESTS=OFF "
        "-DWITH_GFLAGS=OFF "
        "-DWITH_BENCHMARK_TOOLS=OFF "
        "-DWITH_TOOLS=OFF "
        "-DWITH_MD_LIBRARY=OFF "
        "-DWITH_RUNTIME_DEBUG=OFF "
        "-DROCKSDB_BUILD_SHARED=OFF "
        "-DWITH_SNAPPY=OFF "
        "-DWITH_LZ4=OFF "
        "-DWITH_ZLIB=OFF "
        "-DWITH_LIBURING=OFF "
        "-DWITH_ZSTD=OFF "
        "-DWITH_BZ2=OFF "
        "-WITH_GFLAGS=OFF "
        ".."
    ).format(CMAKE_REQUIRED_PARAMS, CMAKE_CXX_FLAGS, CMAKE_C_FLAGS, INSTALL_PREFIX)
    
    if GOOS == "windows":
        cmake_cmd += ' -DCMAKE_CXX_COMPILER="C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.37.32822/bin/Hostx64/x64/cl.exe"'
        cmake_cmd += ' -DCMAKE_C_COMPILER="C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.37.32822/bin/Hostx64/x64/cl.exe"'
        cmake_cmd += ' -DCMAKE_ASM_COMPILER="C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.37.32822/bin/Hostx64/x64/ml64.exe"'

    run_cmd(cmake_cmd)

    # Execute the build command based on the platform
    if GOOS == "windows":
        msbuild_path = '"C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\MSBuild\\Current\\Bin\\MSBuild.exe"'
        build_cmd = '{} ALL_BUILD.vcxproj /p:Configuration=Release /m'.format(msbuild_path)
        install_cmd = '{} INSTALL.vcxproj /p:Configuration=Release'.format(msbuild_path)
    else:
        build_cmd = 'make -j16'
        install_cmd = 'make install/strip'
    
    run_cmd(build_cmd)
    run_cmd(install_cmd)
    
    rm_rf(BUILD_PATH)
    
    dirs_to_remove = [os.path.join(INSTALL_PREFIX, d) for d in ["bin", "share", "lib/cmake", "lib64/cmake", "lib/pkgconfig", "lib64/pkgconfig"]]
    for d in dirs_to_remove:
        rm_rf(d)




def test():
    run_cmd("go test -v -count=1 -tags testing")

# Mimic the Makefile default target
def main():
    GOOS, GOARCH, GOOS_GOARCH, GOOS_GOARCH_NATIVE, ROOT_DIR, DEST, DEST_LIB, DEST_INCLUDE = get_env_vars()
    
    prepare(DEST, DEST_LIB, DEST_INCLUDE)
    build(DEST, ROOT_DIR)

main()
