"""Todas as informações enviadas pelo usuário são validadas aqui."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Entrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Compra(Entrada):
    produto_id: int = Field(gt=0, strict=True)
    quantidade: int = Field(ge=1, le=10, strict=True)
    nome: str = Field(min_length=2, max_length=80)
    email: EmailStr
    cep: str = Field(pattern=r"^[0-9]{5}-[0-9]{3}$")
    tentativa_id: UUID
    confirmar: Literal[True]


class Mensagem(Entrada):
    texto: str = Field(min_length=1, max_length=1000)
    assunto: Literal["vendas", "suporte"] = "vendas"
