"""Leia os grafos de cima para baixo: cada nó é uma função comum."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from agents import responder
from models import Compra
from store import buscar_produto, registrar_compra


class EstadoCompra(TypedDict, total=False):
    entrada: dict
    sessao: str
    compra: Compra
    erro: str
    pedido: dict


def validar_compra(estado):
    return {"compra": Compra.model_validate(estado["entrada"])}


def verificar_produto(estado):
    if not buscar_produto(estado["compra"].produto_id):
        return {"erro": "Produto não encontrado."}
    return {"erro": ""}


def registrar_pedido(estado):
    try:
        return {"pedido": registrar_compra(estado["compra"], estado["sessao"])}
    except ValueError as erro:
        return {"erro": str(erro)}


grafo_compra = StateGraph(EstadoCompra)
grafo_compra.add_node("validar", validar_compra)
grafo_compra.add_node("verificar", verificar_produto)
grafo_compra.add_node("registrar", registrar_pedido)
grafo_compra.add_edge(START, "validar")
grafo_compra.add_edge("validar", "verificar")
grafo_compra.add_conditional_edges("verificar", lambda e: "rejeitar" if e["erro"] else "continuar", {
    "rejeitar": END, "continuar": "registrar",
})
grafo_compra.add_edge("registrar", END)
fluxo_compra = grafo_compra.compile()


class EstadoChat(TypedDict, total=False):
    assunto: str
    sessao: str
    historico: list[dict]
    resposta: str


def agente_vendas(estado):
    return {"resposta": responder("vendas", estado["sessao"], estado["historico"])}


def agente_suporte(estado):
    return {"resposta": responder("suporte", estado["sessao"], estado["historico"])}


grafo_chat = StateGraph(EstadoChat)
grafo_chat.add_node("vendas", agente_vendas)
grafo_chat.add_node("suporte", agente_suporte)
grafo_chat.add_conditional_edges(START, lambda e: e["assunto"], {"vendas": "vendas", "suporte": "suporte"})
grafo_chat.add_edge("vendas", END)
grafo_chat.add_edge("suporte", END)
fluxo_chat = grafo_chat.compile()
