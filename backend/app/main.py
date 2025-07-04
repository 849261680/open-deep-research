import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.research import router as research_router

app = FastAPI(title="Deep Research Agent", version="1.0.0")

# 获取允许的源
allowed_origins = [
    "http://localhost:3000",  # 本地开发
    "http://localhost:3001",  # 备用端口
    "https://research-gpt-blue.vercel.app",  # Vercel生产域名
]

# 从环境变量添加生产域名
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url:
    allowed_origins.append(frontend_url)

# Vercel自动部署域名
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    allowed_origins.extend([
        f"https://{vercel_url}",
        f"http://{vercel_url}"
    ])

# 启用CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
app.include_router(research_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Deep Research Agent API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Deep Research Agent API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)