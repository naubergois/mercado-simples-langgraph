"""Cenários derivados de specs/01-marketplace.md, sem chamar uma IA paga."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import agents
import main
from models import Compra
from store import buscar_produto, conexao, listar_pedidos, registrar_compra


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "teste.db"))
    monkeypatch.setenv("CHAT_MODE", "demo")
    main.historicos.clear()
    with TestClient(main.app) as client:
        client.get("/api/config")
        yield client


def dados_compra(**alteracoes):
    return {"produto_id": 1, "quantidade": 2, "nome": "Maria Exemplo",
            "email": "maria@example.com", "cep": "60000-000",
            "tentativa_id": str(uuid4()), "confirmar": True, **alteracoes}


def test_catalogo_e_pagina(cliente):
    """CAT-01: catálogo disponível com valores e estoque."""
    assert cliente.get("/").status_code == 200
    produtos = cliente.get("/api/produtos").json()
    assert len(produtos) == 6
    assert produtos[0]["preco_centavos"] == 12990


@pytest.mark.parametrize("alteracoes", [
    {"nome": "  "}, {"email": "invalido"}, {"cep": "abcdefghi"},
    {"quantidade": 0}, {"quantidade": 11}, {"quantidade": 1.5},
    {"quantidade": True}, {"preco_centavos": 1}, {"confirmar": False},
])
def test_rejeita_compra_invalida(cliente, alteracoes):
    """VAL-01: entradas inválidas não produzem efeitos."""
    assert cliente.post("/api/compras", json=dados_compra(**alteracoes)).status_code == 422
    assert cliente.get("/api/pedidos").json() == []
    assert buscar_produto(1)["estoque"] == 20


def test_compra_e_reenvio(cliente):
    """BUY-01/02/03: valor confiável e exatamente um pedido por tentativa."""
    dados = dados_compra()
    primeira = cliente.post("/api/compras", json=dados)
    segunda = cliente.post("/api/compras", json=dados)
    assert primeira.status_code == segunda.status_code == 200
    assert primeira.json() == segunda.json()
    assert primeira.json()["total_centavos"] == 25980
    assert buscar_produto(1)["estoque"] == 18
    assert len(cliente.get("/api/pedidos").json()) == 1
    dados["quantidade"] = 3
    assert cliente.post("/api/compras", json=dados).status_code == 409


def test_produto_inexistente_e_estoque_insuficiente(cliente):
    assert cliente.post("/api/compras", json=dados_compra(produto_id=999)).status_code == 409
    assert cliente.post("/api/compras", json=dados_compra(produto_id=3, quantidade=9)).status_code == 409
    assert buscar_produto(3)["estoque"] == 8
    assert cliente.get("/api/pedidos").json() == []


def test_ultima_unidade_nao_e_vendida_duas_vezes(cliente):
    """BUY-01: transação protege o estoque em compras concorrentes."""
    with conexao() as banco:
        banco.execute("UPDATE produtos SET estoque = 1 WHERE id = 1")

    def comprar(_):
        try:
            registrar_compra(Compra(**dados_compra(quantidade=1)), "mesma-sessao")
            return "ok"
        except ValueError:
            return "esgotado"

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultados = list(executor.map(comprar, range(2)))
    assert sorted(resultados) == ["esgotado", "ok"]
    assert buscar_produto(1)["estoque"] == 0
    assert len(listar_pedidos("mesma-sessao")) == 1


def test_pedidos_persistem_e_sao_isolados(cliente):
    """DATA-01: outro visitante não vê pedidos da primeira sessão."""
    cliente.post("/api/compras", json=dados_compra())
    cookie = cliente.cookies.get("sessao")
    with TestClient(main.app) as outro:
        assert outro.get("/api/pedidos").json() == []
        resposta = outro.post("/api/chat", json={"texto": "Quais meus pedidos?", "assunto": "suporte"})
        assert "ainda não tem pedidos" in resposta.json()["resposta"]
    with TestClient(main.app) as reaberto:
        reaberto.cookies.set("sessao", cookie)
        assert len(reaberto.get("/api/pedidos").json()) == 1


@pytest.mark.parametrize("dados", [{"texto": " "}, {"texto": "a" * 1001}, {"texto": "oi", "assunto": "admin"}, {"texto": "oi", "historico": []}])
def test_chat_valida_entrada(cliente, dados):
    assert cliente.post("/api/chat", json=dados).status_code == 422


def test_chat_demo_e_roteamento(cliente):
    """CHAT-01/02/04: os dois caminhos do LangGraph funcionam sem chave."""
    venda = cliente.post("/api/chat", json={"texto": "fone", "assunto": "vendas"}).json()
    assert venda["agente"] == "vendas"
    assert "Modo demo" in venda["resposta"]
    assert "Fone sem fio" in venda["resposta"]
    cliente.post("/api/compras", json=dados_compra())
    suporte = cliente.post("/api/chat", json={"texto": "meus pedidos", "assunto": "suporte"}).json()
    assert suporte["agente"] == "suporte"
    assert "Confirmado" in suporte["resposta"]
    assert buscar_produto(1)["estoque"] == 18


def test_chat_memoria_e_falha_provedor(cliente, monkeypatch):
    """CHAT-03/04: memória no servidor, integração substituída por um fake."""
    monkeypatch.setenv("CHAT_MODE", "deepseek")
    chamadas = []

    class AgenteFake:
        def invoke(self, dados, config):
            chamadas.append(dados["messages"].copy())
            return {"messages": [AIMessage(content="Olá, posso ajudar.")]}

    monkeypatch.setattr(agents, "criar_agente", lambda assunto, sessao: AgenteFake())
    cliente.post("/api/chat", json={"texto": "Quero um fone"})
    resultado = cliente.post("/api/chat", json={"texto": "Qual o preço?"})
    assert resultado.status_code == 200
    assert [m["role"] for m in chamadas[-1]] == ["user", "assistant", "user"]
    assert chamadas[-1][0]["content"] == "Quero um fone"

    def falhar(*args):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(agents, "criar_agente", falhar)
    assert cliente.post("/api/chat", json={"texto": "oi"}).status_code == 503


def test_agentes_langchain_compilam_sem_rede(cliente, monkeypatch):
    """Verifica a API real de criação e o isolamento das ferramentas."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "chave-ficticia-apenas-para-teste")
    for assunto in ["vendas", "suporte"]:
        agente = agents.criar_agente(assunto, "sessao-teste")
        assert "model" in agente.get_graph().nodes


def test_validacao_direta_do_grafo(cliente):
    from pydantic import ValidationError
    from flows import fluxo_compra

    with pytest.raises(ValidationError):
        fluxo_compra.invoke({"entrada": dados_compra(quantidade=-1), "sessao": "teste"})
