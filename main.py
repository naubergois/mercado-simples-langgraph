"""API e página web. Execute: uvicorn main:app --reload"""

import logging
import os
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from flows import fluxo_chat, fluxo_compra
from models import Compra, Mensagem
from store import iniciar_banco, listar_pedidos, listar_produtos

PASTA = Path(__file__).parent
historicos = OrderedDict()
trava = Lock()


@asynccontextmanager
async def lifespan(app):
    iniciar_banco()
    yield


app = FastAPI(title="Mercado Simples", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=PASTA / "static"), name="static")


@app.middleware("http")
async def identificar_visitante(request: Request, call_next):
    sessao = request.cookies.get("sessao", "")
    try:
        sessao = str(UUID(sessao))
    except ValueError:
        sessao = str(uuid4())
    request.state.sessao = sessao
    resposta = await call_next(request)
    if request.cookies.get("sessao") != sessao:
        resposta.set_cookie("sessao", sessao, httponly=True, samesite="strict", max_age=86400)
    return resposta


@app.exception_handler(RequestValidationError)
async def entrada_invalida(request, erro):
    # Não devolvemos nem registramos o conteúdo de dados pessoais inválidos.
    campos = sorted({str(item["loc"][-1]) for item in erro.errors()})
    return JSONResponse(status_code=422, content={"detail": "Confira os campos: " + ", ".join(campos)})


@app.get("/")
def pagina():
    return FileResponse(PASTA / "static" / "index.html")


@app.get("/api/config")
def configuracao():
    return {"modo": os.getenv("CHAT_MODE", "demo")}


@app.get("/api/produtos")
def produtos():
    return listar_produtos()


@app.get("/api/pedidos")
def pedidos(request: Request):
    return listar_pedidos(request.state.sessao)


@app.post("/api/compras")
def comprar(compra: Compra, request: Request):
    resultado = fluxo_compra.invoke({"entrada": compra.model_dump(), "sessao": request.state.sessao})
    if resultado.get("erro"):
        raise HTTPException(status_code=409, detail=resultado["erro"])
    return resultado["pedido"]


@app.post("/api/chat")
def conversar(mensagem: Mensagem, request: Request):
    sessao = request.state.sessao
    with trava:
        historico = historicos.get(sessao, []).copy()
    historico = historico[-10:] + [{"role": "user", "content": mensagem.texto}]
    try:
        resultado = fluxo_chat.invoke({
            "assunto": mensagem.assunto, "sessao": sessao, "historico": historico,
        })
    except Exception as erro:
        logging.getLogger(__name__).warning("Chat indisponível: %s", type(erro).__name__)
        raise HTTPException(status_code=503, detail="Atendimento indisponível. Tente novamente em instantes.") from erro
    historico.append({"role": "assistant", "content": resultado["resposta"]})
    with trava:
        historicos[sessao] = historico[-10:]
        historicos.move_to_end(sessao)
        if len(historicos) > 1000:
            historicos.popitem(last=False)
    return {"resposta": resultado["resposta"], "agente": mensagem.assunto}
