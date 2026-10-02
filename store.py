"""SQLite: catálogo e pedidos. Dinheiro é sempre um inteiro em centavos."""

import json
import os
import sqlite3
from contextlib import contextmanager
from uuid import uuid4

from models import Compra

PRODUTOS = [
    (1, "Fone sem fio Pulse", "Eletrônicos", 12990, 20, "headphones", "Som para acompanhar seu dia."),
    (2, "Tênis urbano Move", "Moda", 18990, 12, "shoe", "Conforto em cada passo."),
    (3, "Cafeteira elétrica Aroma", "Casa", 15990, 8, "coffee", "Sua pausa favorita, todos os dias."),
    (4, "Smartwatch Fit", "Eletrônicos", 24990, 15, "watch", "Mais movimento na sua rotina."),
    (5, "Mochila Essencial", "Moda", 11990, 10, "bag", "Tudo o que você precisa, com você."),
    (6, "Luminária de mesa Luna", "Casa", 8990, 18, "lamp", "Uma nova luz para seu espaço."),
]


@contextmanager
def conexao():
    banco = sqlite3.connect(os.getenv("DATABASE_PATH", "mercado.db"), timeout=10)
    banco.row_factory = sqlite3.Row
    try:
        with banco:
            yield banco
    finally:
        banco.close()


def iniciar_banco():
    with conexao() as banco:
        banco.execute("""CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY, nome TEXT, categoria TEXT,
            preco_centavos INTEGER, estoque INTEGER CHECK(estoque >= 0),
            icone TEXT, descricao TEXT)""")
        banco.executemany("INSERT OR IGNORE INTO produtos VALUES (?, ?, ?, ?, ?, ?, ?)", PRODUTOS)
        banco.execute("""CREATE TABLE IF NOT EXISTS pedidos (
            id TEXT PRIMARY KEY, sessao TEXT, tentativa TEXT, entrada TEXT,
            dados TEXT, UNIQUE(sessao, tentativa))""")


def listar_produtos():
    with conexao() as banco:
        return [dict(linha) for linha in banco.execute("SELECT * FROM produtos ORDER BY id")]


def buscar_produto(produto_id):
    return next((p for p in listar_produtos() if p["id"] == produto_id), None)


def listar_pedidos(sessao):
    with conexao() as banco:
        linhas = banco.execute("SELECT dados FROM pedidos WHERE sessao = ? ORDER BY rowid DESC", (sessao,))
        return [json.loads(linha["dados"]) for linha in linhas]


def registrar_compra(compra: Compra, sessao: str):
    # BEGIN IMMEDIATE impede duas compras de consumir a última unidade juntas.
    with conexao() as banco:
        banco.execute("BEGIN IMMEDIATE")
        anterior = banco.execute(
            "SELECT entrada, dados FROM pedidos WHERE sessao = ? AND tentativa = ?",
            (sessao, str(compra.tentativa_id)),
        ).fetchone()
        if anterior:
            if anterior["entrada"] != compra.model_dump_json():
                raise ValueError("Esta tentativa já foi usada com outros dados.")
            return json.loads(anterior["dados"])

        produto = banco.execute("SELECT * FROM produtos WHERE id = ?", (compra.produto_id,)).fetchone()
        if not produto or produto["estoque"] < compra.quantidade:
            raise ValueError("Produto indisponível ou estoque insuficiente.")
        pedido = {
            "id": str(uuid4()), "produto": produto["nome"],
            "quantidade": compra.quantidade,
            "total_centavos": produto["preco_centavos"] * compra.quantidade,
            "status": "Confirmado • simulação, sem cobrança",
        }
        banco.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (compra.quantidade, compra.produto_id))
        banco.execute("INSERT INTO pedidos VALUES (?, ?, ?, ?, ?)", (
            pedido["id"], sessao, str(compra.tentativa_id),
            compra.model_dump_json(), json.dumps(pedido, ensure_ascii=False),
        ))
        return pedido
