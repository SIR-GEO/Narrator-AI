from dotenv import load_dotenv
load_dotenv()
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import aiohttp
import base64
from narrate_description import router as narrate_description_router


app = FastAPI()

app.include_router(narrate_description_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.mount("/templates", StaticFiles(directory="templates"), name="templates")



@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    return FileResponse('templates/main.html')
