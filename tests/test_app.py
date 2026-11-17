"""Testes unitários e de integração do MVP FériasFlow."""
import sqlite3
from datetime import date, timedelta
import pytest
import app as modulo

@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo, 'DB', tmp_path / 'teste.db')
    monkeypatch.setattr(modulo, 'render_template', lambda nome, **kwargs: f'Template: {nome}')
    modulo.app.config.update(TESTING=True)
    modulo.init_db()
    with modulo.app.test_client() as client:
        yield client

def sessao(client, usuario=None):
    with client.session_transaction() as sess:
        sess['csrf'] = 'token-teste'
        if usuario is not None:
            sess['user_id'] = usuario

def test_inicio_redireciona_login(cliente):
    assert cliente.get('/').headers['Location'].endswith('/login')

def test_login_invalido(cliente):
    sessao(cliente)
    resposta = cliente.post('/login', data={'email':'ana@exemplo.test','senha':'incorreta','csrf':'token-teste'})
    assert resposta.status_code == 200

def test_login_valido(cliente):
    sessao(cliente)
    resposta = cliente.post('/login', data={'email':'ana@exemplo.test','senha':'Demo@2026!','csrf':'token-teste'})
    assert resposta.status_code == 302
    assert resposta.headers['Location'].endswith('/painel')

def test_painel_exige_login(cliente):
    assert cliente.get('/painel').status_code == 302

def test_painel_autenticado(cliente):
    sessao(cliente, 1)
    assert cliente.get('/painel').status_code == 200

def test_post_sem_csrf_bloqueado(cliente):
    sessao(cliente, 1)
    assert cliente.post('/solicitar', data={}).status_code == 400

def test_colaborador_nao_acessa_aprovacoes(cliente):
    sessao(cliente, 1)
    assert cliente.get('/aprovacoes').status_code == 403

def test_gestor_acessa_aprovacoes(cliente):
    sessao(cliente, 3)
    assert cliente.get('/aprovacoes').status_code == 200

def test_solicitacao_data_passada_nao_e_gravada(cliente):
    sessao(cliente, 1)
    ontem = (date.today()-timedelta(days=1)).isoformat()
    cliente.post('/solicitar', data={'inicio':ontem,'fim':ontem,'csrf':'token-teste'})
    with sqlite3.connect(modulo.DB) as conn:
        assert conn.execute('SELECT COUNT(*) FROM solicitacoes WHERE usuario_id=1').fetchone()[0] == 0

def test_solicitacao_valida_e_gravada(cliente):
    sessao(cliente, 1)
    # Ajusta o período concessivo do dado fictício para permitir datas futuras.
    with sqlite3.connect(modulo.DB) as conn:
        conn.execute("UPDATE usuarios SET concessivo_fim='2099-12-31' WHERE id=1")
    inicio = (date.today()+timedelta(days=7)).isoformat()
    fim = (date.today()+timedelta(days=9)).isoformat()
    resposta = cliente.post('/solicitar', data={'inicio':inicio,'fim':fim,'csrf':'token-teste'})
    assert resposta.status_code == 302
    with sqlite3.connect(modulo.DB) as conn:
        assert conn.execute('SELECT dias FROM solicitacoes WHERE usuario_id=1').fetchone()[0] == 3

def test_decisao_invalida_bloqueada(cliente):
    sessao(cliente, 3)
    assert cliente.post('/decidir/1', data={'decisao':'outro','csrf':'token-teste'}).status_code == 400

def test_rh_aprova_solicitacao(cliente):
    sessao(cliente, 4)
    resposta = cliente.post('/decidir/1', data={'decisao':'aprovada','csrf':'token-teste'})
    assert resposta.status_code == 302
    with sqlite3.connect(modulo.DB) as conn:
        assert conn.execute('SELECT status FROM solicitacoes WHERE id=1').fetchone()[0] == 'aprovada'
