FROM ubuntu:22.04

# 拉取CodeQL CLI
RUN apt-get update && apt-get install -y wget unzip
RUN wget https://github.com/github/codeql-cli-binaries/releases/download/v2.21.4/codeql-linux64.zip -O /tmp/codeql.zip \
    && unzip /tmp/codeql.zip -d /opt \
    && ln -s /opt/codeql/codeql /usr/local/bin/codeql \
    && rm /tmp/codeql.zip

# 拉取CodeQL语言包及安装对应语言环境

# Go
# RUN apt-get update && apt-get install -y golang

# C/C++
RUN apt-get update && apt-get install -y build-essential

# Java
RUN apt-get update && apt-get install -y openjdk-21-jdk

# 设置工作目录
WORKDIR /workspace

# # 复制数据库构建脚本
# COPY scripts/build_db.sh /scripts/
# RUN chmod +x /scripts/build_db.sh

# 检查是否已安装python3，若无则安装
RUN if ! command -v python3 >/dev/null 2>&1; then \
    apt-get update && apt-get install -y python3 python3-venv python3-pip; \
    fi

# 默认启动命令：等待compose挂载源码后手动执行脚本
CMD ["sleep", "infinity"]