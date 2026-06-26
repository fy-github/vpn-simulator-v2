.PHONY: help install dev test lint format build run clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖
	poetry install

dev: ## 安装开发依赖
	poetry install --with dev

test: ## 运行测试
	poetry run pytest

test-cov: ## 运行测试并生成覆盖率报告
	poetry run pytest --cov=vpn_simulator --cov-report=html

lint: ## 运行 linting
	poetry run ruff check .
	poetry run mypy .

format: ## 格式化代码
	poetry run black .
	poetry run isort .

run: ## 运行应用
	poetry run uvicorn vpn_simulator.api.app:app --reload

run-cli: ## 运行 CLI
	poetry run vpn-simulator --help

build: ## 构建 Docker 镜像
	docker build -t vpn-simulator .

run-docker: ## 运行 Docker 容器
	docker-compose up -d

stop-docker: ## 停止 Docker 容器
	docker-compose down

clean: ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov

db-migrate: ## 运行数据库迁移
	poetry run alembic upgrade head

db-revision: ## 创建数据库迁移
	poetry run alembic revision --autogenerate -m "$(msg)"

docs: ## 生成文档
	poetry run mkdocs build

docs-serve: ## 本地预览文档
	poetry run mkdocs serve

web-install: ## 安装 Web UI 依赖
	cd web-ui && npm install

web-dev: ## 运行 Web UI 开发服务器
	cd web-ui && npm run dev

web-build: ## 构建 Web UI
	cd web-ui && npm run build
