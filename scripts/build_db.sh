#!/bin/bash
# filepath: scripts/build_db.sh

# 设置源码和数据库目录
SRC_DIR="/workspace/src/requests"
DB_DIR="/workspace/db"

# 创建CodeQL数据库
codeql database create "$DB_DIR" \
    --language=python \
    --source-root="$SRC_DIR"

echo "CodeQL数据库已创建在