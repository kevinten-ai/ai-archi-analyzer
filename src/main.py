"""主程序入口"""

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

from .api.routes import router
from .config.settings import settings


def create_app() -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI(
        title="AI Architecture Analyzer",
        description="基于LLM的系统架构分析平台",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 配置日志
    settings.setup_logging()

    # 确保目录存在
    settings.ensure_directories()

    # 注册路由
    app.include_router(router, prefix="/api", tags=["architecture-analysis"])

    # 全局异常处理
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理"""
        logger.warning(f"请求验证失败: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "请求参数验证失败",
                "details": exc.errors()
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理"""
        logger.error(f"未处理的异常: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "服务器内部错误",
                "details": str(exc) if settings.debug else None
            }
        )

    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "name": "AI Architecture Analyzer",
            "version": "1.0.0",
            "description": "基于LLM的系统架构分析平台",
            "docs": "/docs",
            "health": "/api/health"
        }

    # 启动事件
    @app.on_event("startup")
    async def startup_event():
        """启动事件"""
        logger.info("AI Architecture Analyzer 启动中...")
        logger.info(f"环境: {settings.environment}")
        logger.info(f"调试模式: {settings.debug}")
        logger.info(f"LLM提供商: {settings.llm.provider}")
        if settings.mcp.enabled:
            logger.info(f"MCP端点: {settings.mcp.endpoint}")

    # 关闭事件
    @app.on_event("shutdown")
    async def shutdown_event():
        """关闭事件"""
        logger.info("AI Architecture Analyzer 关闭中...")

    return app


def main():
    """主函数"""
    app = create_app()

    # 启动服务器
    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        workers=settings.api.workers,
        reload=settings.api.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()



