// Sem framework: buscar dados, desenhar produtos e enviar os dois formulários.
const $ = (seletor) => document.querySelector(seletor);
const dinheiro = (centavos) => (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
let produtos = [];
let categoria = 'Todos';
let selecionado = null;
let tentativaId = null;

// Ilustrações locais: nenhum serviço externo é necessário para abrir a página.
const desenhos = {
  headphones: '<path d="M45 85V66a45 45 0 0 1 90 0v19" fill="none" stroke="#3b5648" stroke-width="15"/><rect x="30" y="72" width="30" height="57" rx="13" fill="#344d40"/><rect x="120" y="72" width="30" height="57" rx="13" fill="#344d40"/><path d="M54 82v37M126 82v37" stroke="#162f24" stroke-width="9" stroke-linecap="round"/>',
  shoe: '<path d="M28 86 48 51 83 71 110 73 140 100 164 111v15H23V99Z" fill="#e0d6c3" stroke="#aa9e87" stroke-width="2"/><path d="m24 112 140 2v17H24Z" fill="#fffefa"/><path d="m70 76 20 7m-11-16 21 16m-11-7 22 16" stroke="#fffdf7" stroke-width="5"/><path d="m33 89 21 10 21-9" fill="none" stroke="#688372" stroke-width="9"/>',
  coffee: '<rect x="43" y="23" width="94" height="114" rx="10" fill="#43564a"/><path d="M47 40h87v12H47z" fill="#637768"/><rect x="57" y="61" width="60" height="59" rx="5" fill="#25332b"/><path d="M60 89h49v29H60z" fill="#e1c59b"/><path d="M110 93h12v18h-12" fill="none" stroke="#e1c59b" stroke-width="5"/><circle cx="124" cy="66" r="4" fill="#e7dcbb"/><rect x="35" y="133" width="110" height="9" rx="3" fill="#283c2f"/>',
  watch: '<rect x="67" y="6" width="46" height="148" rx="17" fill="#525e4e"/><rect x="52" y="42" width="76" height="78" rx="19" fill="#a9b09a"/><rect x="57" y="47" width="66" height="68" rx="15" fill="#1d3025"/><circle cx="90" cy="81" r="23" stroke="#cee290" stroke-width="3" fill="none"/><path d="M90 65v17l13 7" stroke="#f4efda" fill="none" stroke-width="3"/><rect x="128" y="66" width="5" height="13" rx="2" fill="#939b87"/>',
  bag: '<path d="M72 40v-9a18 18 0 0 1 36 0v9" fill="none" stroke="#8c6749" stroke-width="7"/><rect x="43" y="37" width="94" height="105" rx="24" fill="#b99570"/><rect x="55" y="93" width="70" height="40" rx="10" fill="#a78461"/><path d="M58 103h64M55 66q35-14 70 0" stroke="#dcc1a0" stroke-width="3" fill="none"/><rect x="84" y="68" width="12" height="9" rx="2" fill="#4e5d4b"/>',
  lamp: '<ellipse cx="95" cy="140" rx="46" ry="8" fill="#8d9d85"/><path d="M96 137V70l-33-21" stroke="#61795f" stroke-width="8" fill="none"/><path d="m51 26 31 19-28 40-42-26Z" fill="#789171"/><ellipse cx="32" cy="73" rx="24" ry="8" transform="rotate(32 32 73)" fill="#f3e9b2"/><circle cx="96" cy="71" r="7" fill="#344e36"/>',
};

async function api(url, dadosEnvio) {
  const options = dadosEnvio ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(dadosEnvio) } : {};
  const resposta = await fetch(url, options);
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível concluir. Tente novamente.');
  return dados;
}

function elemento(tag, classe, texto) {
  const item = document.createElement(tag);
  item.className = classe;
  if (texto !== undefined) item.textContent = texto;
  return item;
}

function mostrarProdutos() {
  const busca = $('#busca').value.toLocaleLowerCase('pt-BR');
  const visiveis = produtos.filter(p => (categoria === 'Todos' || p.categoria === categoria) && p.nome.toLocaleLowerCase('pt-BR').includes(busca));
  $('#produtos').replaceChildren();
  $('#contagem').textContent = `${visiveis.length} produtos`;
  if (!visiveis.length) $('#produtos').append(elemento('p', '', 'Nenhum produto encontrado. Tente outra busca.'));
  for (const produto of visiveis) {
    const card = elemento('article', 'product');
    const arte = elemento('div', 'product-art');
    // Apenas SVGs constantes deste arquivo; dados da API entram via textContent.
    arte.innerHTML = `<svg viewBox="0 0 180 160" aria-hidden="true">${desenhos[produto.icone] || ''}</svg>`;
    arte.append(elemento('span', '', 'SELEÇÃO ESSENCIAL'));
    const info = elemento('div', 'product-info');
    info.append(elemento('span', 'category', produto.categoria), elemento('h3', '', produto.nome), elemento('p', 'description', produto.descricao), elemento('div', 'price', dinheiro(produto.preco_centavos)), elemento('p', 'stock', `${produto.estoque} disponíveis · Frete simulado grátis`));
    const botao = elemento('button', 'buy', produto.estoque > 0 ? 'Comprar agora ↗' : 'Esgotado');
    botao.disabled = produto.estoque === 0;
    botao.addEventListener('click', () => abrirCompra(produto));
    info.append(botao);
    card.append(arte, info);
    $('#produtos').append(card);
  }
}

async function carregarProdutos() {
  produtos = await api('/api/produtos');
  mostrarProdutos();
}

function abrirCompra(produto) {
  selecionado = produto;
  tentativaId = crypto.randomUUID();
  $('#compra-form').reset();
  $('#compra-titulo').textContent = produto.nome;
  $('#erro-compra').textContent = '';
  $('#compra-form').elements.quantidade.max = Math.min(10, produto.estoque);
  atualizarTotal();
  $('#compra-dialog').showModal();
}

function atualizarTotal() {
  $('#compra-total').textContent = dinheiro(selecionado.preco_centavos * Number($('#compra-form').elements.quantidade.value));
}

async function mostrarPedidos() {
  const lista = $('#pedidos');
  lista.textContent = 'Carregando pedidos…';
  if (!$('#pedidos-dialog').open) $('#pedidos-dialog').showModal();
  try {
    const pedidos = await api('/api/pedidos');
    lista.replaceChildren();
    if (!pedidos.length) lista.append(elemento('p', '', 'Suas próximas descobertas aparecerão aqui. Você ainda não tem pedidos.'));
    for (const pedido of pedidos) {
      const item = elemento('div', 'order');
      item.append(elemento('strong', '', pedido.produto), elemento('p', '', `${pedido.quantidade} unidade(s) · ${dinheiro(pedido.total_centavos)}`), elemento('p', '', pedido.status), elemento('p', '', `Pedido ${pedido.id}`));
      lista.append(item);
    }
  } catch (erro) { lista.textContent = erro.message; }
}

$('#compra-form').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const form = evento.currentTarget;
  const botao = form.querySelector('button[type=submit]');
  const campos = form.elements;
  botao.disabled = true;
  $('#erro-compra').textContent = '';
  try {
    await api('/api/compras', { produto_id: selecionado.id, quantidade: Number(campos.quantidade.value), nome: campos.nome.value, email: campos.email.value, cep: campos.cep.value, tentativa_id: tentativaId, confirmar: campos.confirmar.checked });
    $('#compra-dialog').close();
    await mostrarPedidos();
    await carregarProdutos().catch(() => { $('#erro-catalogo').textContent = 'Compra confirmada. Atualize a página para conferir o estoque.'; });
  } catch (erro) { $('#erro-compra').textContent = erro.message; }
  finally { botao.disabled = false; }
});

function adicionarMensagem(texto, autor) {
  $('#mensagens').append(elemento('div', `bubble ${autor}`, texto));
  $('#mensagens').scrollTop = $('#mensagens').scrollHeight;
}

$('#chat-form').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  const texto = $('#mensagem').value.trim();
  if (!texto) return;
  const botao = evento.currentTarget.querySelector('button');
  botao.disabled = true;
  $('#mensagem').disabled = true;
  $('#erro-chat').textContent = '';
  adicionarMensagem(texto, 'user');
  botao.textContent = '…';
  try {
    const resultado = await api('/api/chat', { texto, assunto: $('#assunto').value });
    adicionarMensagem(resultado.resposta, 'assistant');
    $('#mensagem').value = '';
  } catch (erro) { $('#erro-chat').textContent = erro.message; }
  finally { botao.disabled = false; botao.textContent = '↑'; $('#mensagem').disabled = false; $('#mensagem').focus(); }
});

$('#busca').addEventListener('input', mostrarProdutos);
$('.filters').addEventListener('click', (evento) => {
  const botao = evento.target.closest('[data-category]');
  if (!botao) return;
  categoria = botao.dataset.category;
  document.querySelectorAll('[data-category]').forEach(b => { b.classList.toggle('active', b === botao); b.setAttribute('aria-pressed', String(b === botao)); });
  mostrarProdutos();
});
$('#compra-form').elements.quantidade.addEventListener('input', atualizarTotal);
// Ao editar os dados, inicia-se outra tentativa. Um simples reenvio mantém o ID.
$('#compra-form').addEventListener('input', () => { tentativaId = crypto.randomUUID(); });
$('#fechar-compra').addEventListener('click', () => $('#compra-dialog').close());
$('#fechar-pedidos').addEventListener('click', () => $('#pedidos-dialog').close());
$('#abrir-pedidos').addEventListener('click', mostrarPedidos);

async function iniciar() {
  // Primeiro estabelece o cookie; só depois dispara outras consultas.
  try {
    const config = await api('/api/config');
    $('#modo-chat').textContent = config.modo === 'demo' ? 'Modo demonstração · sem IA' : 'Atendimento com DeepSeek';
    await carregarProdutos();
  } catch (erro) {
    $('#produtos').textContent = '';
    $('#erro-catalogo').textContent = `Não foi possível carregar a loja. ${erro.message}`;
  }
}
iniciar();
