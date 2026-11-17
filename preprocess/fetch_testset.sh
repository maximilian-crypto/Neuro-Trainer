#!/usr/bin/env bash
# Lädt den Testsatz (DATA.md) nach data/raw/. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/raw/bhsd data/raw/cq500
CQ=https://s3.ap-south-1.amazonaws.com/qure.headct.study
[ -f data/raw/cq500/reads.csv ] || curl -sSL --retry 4 -o data/raw/cq500/reads.csv "$CQ/reads.csv"
for n in $(cat preprocess/testset_cq500.txt); do
  [ -f "data/raw/cq500/$n.zip" ] || curl -sSL --retry 4 -o "data/raw/cq500/$n.zip" "$CQ/$n.zip"
done
if [ ! -d data/raw/bhsd_x/label_192 ]; then
  [ -f data/raw/bhsd/label_192.zip ] || curl -sSL --retry 4 -o data/raw/bhsd/label_192.zip \
    https://huggingface.co/datasets/Wendy-Fly/BHSD/resolve/main/label_192.zip
  unzip -q -o data/raw/bhsd/label_192.zip -d data/raw/bhsd_x/
fi
