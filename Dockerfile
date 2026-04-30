# syntax=docker/dockerfile:1
FROM python:3.13-rc-slim

# 安装 uv
RUN pip install --upgrade pip --timeout 1000 --retries 5 -i https://pypi.tuna.tsinghua.edu.cn/simple uv

# 使用 bash 作为 shell
SHELL ["/bin/bash", "-c"]

# 设置工作目录
WORKDIR /app

# 拷贝项目文件
COPY . .

# 安装项目及全部依赖
RUN uv pip install --system --index-url https://pypi.tuna.tsinghua.edu.cn/simple -e ".[full]"

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]