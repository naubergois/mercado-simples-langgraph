# Especificação: Mercado Simples

## Objetivo e escopo
Um exemplo didático de marketplace inspirado no Mercado Livre, com identidade
própria, catálogo, compra de um produto por vez e chat. Não cobra dinheiro,
não realiza entregas e não integra o Mercado Livre. A prioridade é código legível.

## Critérios de aceitação
- **CAT-01**: listar produtos com preço em reais, categoria e estoque; filtrar por nome.
- **VAL-01**: Pydantic rejeita nome vazio, e-mail inválido, CEP fora do formato
  00000-000, quantidade não inteira ou fora de 1–10, mensagem vazia/maior que
  1000 caracteres e campos extras. Nenhum pedido é criado quando há erro.
- **BUY-01**: o LangGraph executa validar → verificar produto → registrar → fim;
  produto inexistente termina em rejeição. O registro verifica o estoque e o
  decrementa na mesma transação SQLite que cria o pedido.
- **BUY-02**: o servidor calcula valores em centavos pelo catálogo. Frete é
  zero apenas nesta simulação. Nenhum preço vem do navegador ou do agente.
- **BUY-03**: a interface exige confirmação explícita antes da compra simulada.
  Um identificador de tentativa evita duplicação por reenvio; reutilizá-lo com
  dados diferentes é rejeitado.
- **CHAT-01**: LangGraph encaminha o assunto escolhido pelo usuário a vendas ou
  suporte; LangChain cria os dois agentes, com ferramentas apenas de leitura.
- **CHAT-02**: vendas consulta catálogo; suporte consulta pedidos da sessão e
  regras da demonstração. Chat não cria pedidos nem modifica estoque.
- **CHAT-03**: contexto inclui as últimas 10 mensagens guardadas no servidor
  por sessão; o cliente não pode injetar mensagens de sistema ou histórico.
- **CHAT-04**: modo demo é identificado e usa respostas fixas, sem LLM. Falha
  no provedor em modo deepseek gera erro amigável, sem fingir resposta de IA.
- **DATA-01**: pedidos e estoque persistem em SQLite; sessões são cookies
  aleatórios HttpOnly; consultas de pedidos são filtradas pela sessão.
- **UI-01**: página responsiva, busca, filtro por categoria, formulário de compra,
  pedidos da sessão, chat, estados de carregamento e mensagens de erro.

## Desenvolvimento orientado a especificações
1. Alterar ou adicionar um critério aqui antes de mudar o comportamento.
2. Descrever os cenários de sucesso e erro em `tests/test_app.py`.
3. Implementar a menor alteração necessária.
4. Rodar `pytest -q` e revisar o resultado na página.

## Fora do escopo
Login, vendedores, pagamentos reais, carrinho de vários produtos, cancelamento
real e infraestrutura de produção. O cookie representa um visitante deste
exemplo, não uma identidade autenticada. Histórico de chat expira ao reiniciar;
limita-se a 10 mensagens e 1000 sessões em memória. Para produção é necessário
login, HTTPS/cookie Secure, proteção contra abuso, sessões persistentes e
integração de pagamento. Não inserir dados reais durante a demonstração.
