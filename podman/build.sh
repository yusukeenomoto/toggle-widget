#!/bin/sh
# podman でビルド・動作確認する
#   ./podman/build.sh image    ビルド用イメージを作る
#   ./podman/build.sh windows  dist/windows/ToggleView.exe を作る
#   ./podman/build.sh linux    dist/linux/ToggleView を作る (spec の確認用)
#   ./podman/build.sh check    作った exe を Wine + Xvfb で起動して dist/screenshot-windows.png を撮る
set -eu
cd "$(dirname "$0")/.."

WIN_IMAGE=toggleview-build-windows:local
LINUX_IMAGE=toggleview-build-linux:local

run() {
  podman run --rm --init -v "$PWD":/src "$@"
}

case "${1:-}" in
  image)
    podman build -t "$WIN_IMAGE" -f podman/Containerfile.windows .
    podman build -t "$LINUX_IMAGE" -f podman/Containerfile.linux .
    ;;
  windows)
    run "$WIN_IMAGE" sh -c '
      wine "C:\Python\python.exe" -m PyInstaller --noconfirm --clean \
        --distpath dist/windows --workpath build/windows ToggleView.spec
      wineserver -w'
    ls -l dist/windows/ToggleView.exe
    ;;
  linux)
    run "$LINUX_IMAGE" pyinstaller --noconfirm --clean \
      --distpath dist/linux --workpath build/linux ToggleView.spec
    ls -l dist/linux/ToggleView
    ;;
  check)
    # データは使い捨てのコンテナ内 %APPDATA% に作られる
    run "$WIN_IMAGE" xvfb-run -a -s "-screen 0 640x480x24" sh -c '
      wine dist/windows/ToggleView.exe &
      sleep 15
      import -window root dist/screenshot-windows.png
      wineserver -k'
    ls -l dist/screenshot-windows.png
    ;;
  *)
    sed -n "2,7p" "$0"
    exit 1
    ;;
esac
