name: Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libssl-dev cmake libffi-dev libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
          pip3 install --user --upgrade buildozer cython
      - name: Build with Buildozer
        run: |
          export PATH=$PATH:~/.local/bin/
          buildozer -v android debug
      - name: Upload APK
        uses: actions/upload-artifact@v4
        with:
          name: package
          path: bin/*.apk
