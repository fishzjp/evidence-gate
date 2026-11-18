FROM python:3.12-slim
WORKDIR /app
COPY src/ ./src/
COPY run_task.py .
# build 审计：无 COPY 答案/数据文件，无 curl/wget 外部资源
CMD ["python", "run_task.py"]
