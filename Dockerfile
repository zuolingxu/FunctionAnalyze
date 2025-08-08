FROM ubuntu:22.04

# 拉取CodeQL CLI
RUN apt-get update && apt-get install -y wget unzip

# CodeQL CLI 包更新很快，请确保拉取的镜像是最新版本
RUN wget https://github.com/github/codeql-cli-binaries/releases/download/v2.22.3/codeql-linux64.zip -O /tmp/codeql.zip \
    && unzip /tmp/codeql.zip -d /opt \
    && ln -s /opt/codeql/codeql /usr/local/bin/codeql \
    && rm /tmp/codeql.zip

RUN apt-get update

# 拉取CodeQL语言包及安装对应语言环境
# Go
# RUN apt-get install -y golang

# C/C++
RUN apt-get install -y build-essential
RUN apt-get update && apt-get install -y nasmx

# Java
RUN apt-get install -y openjdk-21-jdk

# 设置工作目录
WORKDIR /workspace

COPY scripts /workspace/scripts

# 默认启动命令：等待compose挂载源码后手动执行脚本
CMD ["sleep", "infinity"]