#!/bin/bash

echo "============================================"
echo "  HarmonyOS HelloWorld - Build Script"
echo "============================================"
echo

if [ ! -f "hvigorw" ]; then
    echo "[ERROR] hvigorw not found!"
    echo "Please open this project in DevEco Studio and wait for Sync to complete."
    exit 1
fi

echo "[1/2] Building HAP package..."
chmod +x hvigorw
./hvigorw assembleHap --mode module -p product=default

if [ $? -ne 0 ]; then
    echo
    echo "[ERROR] Build failed!"
    exit 1
fi

echo
echo "[2/2] Build completed!"
echo
echo "Output: entry/build/default/outputs/default/entry-default-signed.hap"
echo
echo "Install: hdc install entry/build/default/outputs/default/entry-default-signed.hap"
echo
