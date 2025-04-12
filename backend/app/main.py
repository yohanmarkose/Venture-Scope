import io, os, time, base64, asyncio
from io import BytesIO
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

@app.get("/")
def read_root():
    return "Welcome to the Venture-Scope API!"
