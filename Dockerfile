FROM ubuntu:22.04

# 拉取CodeQL CLI
RUN apt-get update && apt-get install -y wget unzip
RUN wget https://github.com/github/codeql-cli-binaries/releases/download/v2.21.4/codeql-linux64.zip -O /tmp/codeql.zip \
    && unzip /tmp/codeql.zip -d /opt \
    && ln -s /opt/codeql/codeql /usr/local/bin/codeql \
    && rm /tmp/codeql.zip

# 拉取CodeQL语言包及安装对应语言环境

# JavaScript
# RUN /opt/codeql/codeql pack download codeql/javascript-all
# RUN apt-get update && apt-get install -y nodejs npm

# Go
# RUN /opt/codeql/codeql pack download codeql/go-all
# RUN apt-get update && apt-get install -y golang

# Python
RUN /opt/codeql/codeql pack download codeql/python-all
RUN apt-get update && apt-get install -y python3.11 python3-pip

# C/C++
# RUN /opt/codeql/codeql pack download codeql/cpp-all
# RUN apt-get update && apt-get install -y build-essential

# Java
# RUN /opt/codeql/codeql pack download codeql/java-all
# RUN apt-get update && apt-get install -y openjdk-17-jdk

# 设置工作目录
WORKDIR /workspace

# 复制数据库构建脚本
COPY scripts/build_db.sh /scripts/
RUN chmod +x /scripts/build_db.sh

# 默认启动命令：等待compose挂载源码后手动执行脚本
CMD ["sleep", "infinity"]