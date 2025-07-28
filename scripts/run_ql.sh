#!/bin/bash
# filepath: scripts/run_ql.sh

QUERIES_DIR="/workspace/queries"
OUTPUTS_DIR="/workspace/outputs"
DB_DIR="/workspace/db"
SRC_DIR="/workspace/src/requests"

mkdir -p "$OUTPUTS_DIR"

# # 安装依赖包（确保qlpack.yml中的依赖已下载）
# if [ -f "$QUERIES_DIR/qlpack.yml" ]; then
#     echo "Installing CodeQL query pack dependencies..."
#     codeql pack install "$QUERIES_DIR"
# fi

# 检查数据库是否已创建（判断目录下是否有db-*文件夹）
if [ ! -d "$DB_DIR"/db-python ] && [ ! -d "$DB_DIR"/db-clang ] && [ ! -d "$DB_DIR"/db-cpp ] && [ ! -d "$DB_DIR"/db-java ]; then
    echo "CodeQL数据库不存在，正在创建..."
    codeql database create "$DB_DIR" --language=python --source-root="$SRC_DIR"
    echo "数据库创建完成。"
else
    echo "检测到已存在的CodeQL数据库，跳过创建。"
fi

for query in "$QUERIES_DIR"/*.ql; do
    query_name=$(basename "$query" .ql)
    output_file="$OUTPUTS_DIR/${query_name}.bqrs"
    echo "Running $query ..."
    codeql query run "$query" --database "$DB_DIR" --output "$output_file"
done

echo "All queries executed. Results are in $OUTPUTS_DIR."