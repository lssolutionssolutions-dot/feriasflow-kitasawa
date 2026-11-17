import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from secrets import token_hex
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'feriasflow.db'
app = Flask(__name__)
app.secret_key = os.environ.get('FERIASFLOW_SECRET_KEY') or token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(_error):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()


def init_db():
    with app.app_context():
        conn = db()
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL, perfil TEXT NOT NULL CHECK(perfil IN ('colaborador','gestor','rh')),
            equipe TEXT NOT NULL, saldo INTEGER NOT NULL DEFAULT 30,
            aquisitivo_inicio TEXT NOT NULL, aquisitivo_fim TEXT NOT NULL,
            concessivo_fim TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            inicio TEXT NOT NULL, fim TEXT NOT NULL, dias INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente','aprovada','rejeitada')),
            observacao TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL
        );''')
        if not conn.execute('SELECT 1 FROM usuarios LIMIT 1').fetchone():
            people = [
                ('Ana Oliveira','ana@exemplo.test','colaborador','Administrativo',30),
                ('Bruno Costa','bruno@exemplo.test','colaborador','Administrativo',24),
                ('Marina Souza','marina@exemplo.test','gestor','Administrativo',30),
                ('Carla Lima','carla@exemplo.test','rh','RH',30),
            ]
            for nome,email,perfil,equipe,saldo in people:
                conn.execute('''INSERT INTO usuarios(nome,email,senha_hash,perfil,equipe,saldo,aquisitivo_inicio,aquisitivo_fim,concessivo_fim)
                    VALUES(?,?,?,?,?,?, '2025-01-01','2025-12-31','2026-12-31')''',
                    (nome,email,generate_password_hash('Demo@2026!'),perfil,equipe,saldo))
            conn.execute('''INSERT INTO solicitacoes(usuario_id,inicio,fim,dias,status,criado_em)
                VALUES(2,'2026-12-07','2026-12-16',10,'pendente',?)''',(datetime.now().isoformat(timespec='seconds'),))
        conn.commit()


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped

@app.before_request
def csrf_check():
    if 'csrf' not in session:
        session['csrf'] = token_hex(24)
    if request.method == 'POST' and request.form.get('csrf') != session['csrf']:
        abort(400, 'Formulário expirado. Atualize a página e tente novamente.')

@app.context_processor
def globals_for_templates():
    return {'csrf': session.get('csrf'), 'current_user': current_user()}


def current_user():
    uid = session.get('user_id')
    return db().execute('SELECT * FROM usuarios WHERE id=?',(uid,)).fetchone() if uid else None

@app.route('/')
def index():
    return redirect(url_for('painel') if session.get('user_id') else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('senha','')
        user = db().execute('SELECT * FROM usuarios WHERE email=?',(email,)).fetchone()
        if user and check_password_hash(user['senha_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['csrf'] = token_hex(24)
            return redirect(url_for('painel'))
        flash('E-mail ou senha incorretos.', 'erro')
    return render_template('login.html', title='Entrar')

@app.post('/sair')
@login_required
def sair():
    session.clear()
    return redirect(url_for('login'))

@app.route('/painel')
@login_required
def painel():
    user = current_user()
    solicitacoes = db().execute('SELECT * FROM solicitacoes WHERE usuario_id=? ORDER BY id DESC',(user['id'],)).fetchall()
    aprovados = db().execute("SELECT COALESCE(SUM(dias),0) FROM solicitacoes WHERE usuario_id=? AND status='aprovada'",(user['id'],)).fetchone()[0]
    return render_template('painel.html',title='Painel inicial',solicitacoes=solicitacoes,saldo_disponivel=max(0,user['saldo']-aprovados))

@app.route('/solicitar', methods=['GET','POST'])
@login_required
def solicitar():
    user = current_user()
    if request.method == 'POST':
        try:
            inicio = date.fromisoformat(request.form.get('inicio',''))
            fim = date.fromisoformat(request.form.get('fim',''))
            dias = (fim-inicio).days+1
            aprovados = db().execute("SELECT COALESCE(SUM(dias),0) FROM solicitacoes WHERE usuario_id=? AND status='aprovada'",(user['id'],)).fetchone()[0]
            saldo = user['saldo'] - aprovados
            if inicio < date.today() or fim < inicio or dias > saldo or dias < 1:
                raise ValueError('Confira as datas e o saldo disponível.')
            if fim > date.fromisoformat(user['concessivo_fim']):
                raise ValueError('O término ultrapassa o período concessivo informado.')
            overlap = db().execute('''SELECT 1 FROM solicitacoes WHERE usuario_id=? AND status IN ('pendente','aprovada')
                AND inicio<=? AND fim>=? LIMIT 1''',(user['id'],fim.isoformat(),inicio.isoformat())).fetchone()
            if overlap:
                raise ValueError('Já existe uma solicitação ativa nesse período.')
            db().execute('''INSERT INTO solicitacoes(usuario_id,inicio,fim,dias,criado_em) VALUES(?,?,?,?,?)''',
                         (user['id'],inicio.isoformat(),fim.isoformat(),dias,datetime.now().isoformat(timespec='seconds')))
            db().commit()
            flash('Solicitação registrada — Pendente de análise.', 'sucesso')
            return redirect(url_for('painel'))
        except (ValueError, TypeError) as error:
            flash(str(error) if str(error) else 'Informe datas válidas.', 'erro')
    aprovados = db().execute("SELECT COALESCE(SUM(dias),0) FROM solicitacoes WHERE usuario_id=? AND status='aprovada'",(user['id'],)).fetchone()[0]
    return render_template('solicitar.html',title='Solicitar férias',saldo=max(0,user['saldo']-aprovados),hoje=date.today().isoformat())

@app.route('/aprovacoes')
@login_required
def aprovacoes():
    user = current_user()
    if user['perfil'] not in ('gestor','rh'):
        abort(403)
    if user['perfil']=='gestor':
        rows = db().execute('''SELECT s.*,u.nome,u.equipe FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id
            WHERE u.equipe=? AND u.id<>? ORDER BY CASE s.status WHEN 'pendente' THEN 0 ELSE 1 END,s.id DESC''',
            (user['equipe'],user['id'])).fetchall()
    else:
        rows = db().execute('''SELECT s.*,u.nome,u.equipe FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id
            ORDER BY CASE s.status WHEN 'pendente' THEN 0 ELSE 1 END,s.id DESC''').fetchall()
    items = []
    for row in rows:
        conflict = db().execute('''SELECT COUNT(*) FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id
            WHERE s.id<>? AND u.equipe=? AND s.status IN ('pendente','aprovada') AND s.inicio<=? AND s.fim>=?''',
            (row['id'],row['equipe'],row['fim'],row['inicio'])).fetchone()[0]
        items.append({'sol':row,'conflitos':conflict})
    return render_template('aprovacoes.html',title='Análise de solicitações',items=items)

@app.post('/decidir/<int:sol_id>')
@login_required
def decidir(sol_id):
    user = current_user()
    if user['perfil'] not in ('gestor','rh'):
        abort(403)
    row = db().execute('''SELECT s.*,u.equipe,u.saldo FROM solicitacoes s JOIN usuarios u ON u.id=s.usuario_id WHERE s.id=?''',(sol_id,)).fetchone()
    if not row or (user['perfil']=='gestor' and row['equipe']!=user['equipe']):
        abort(404)
    if row['status']!='pendente':
        flash('Esta solicitação já foi analisada.', 'erro')
        return redirect(url_for('aprovacoes'))
    status = request.form.get('decisao')
    if status not in ('aprovada','rejeitada'):
        abort(400)
    if status=='aprovada':
        approved = db().execute("SELECT COALESCE(SUM(dias),0) FROM solicitacoes WHERE usuario_id=? AND status='aprovada'",(row['usuario_id'],)).fetchone()[0]
        if row['dias'] > row['saldo']-approved:
            flash('Saldo insuficiente para aprovação.', 'erro')
            return redirect(url_for('aprovacoes'))
    obs = request.form.get('observacao','').strip()[:300]
    db().execute('UPDATE solicitacoes SET status=?, observacao=? WHERE id=?',(status,obs,sol_id))
    db().commit()
    flash('Solicitação '+status+' com sucesso.', 'sucesso')
    return redirect(url_for('aprovacoes'))

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=False)
