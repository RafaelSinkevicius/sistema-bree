from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
from flask import request
import pandas as pd
import io
from flask import send_file
from sqlalchemy import extract
from flask import session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Você precisa estar logado para acessar esta página.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("usuario_tipo") != "admin":
            flash("Apenas administradores podem acessar esta página.")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

def agora_brasil():
    return datetime.now(tz=timezone(timedelta(hours=-3)))


app = Flask(__name__)
app.secret_key = "chave-super-secreta-bree-2025"

@app.before_request
def checar_login():
    if request.endpoint not in ["login", "static"] and "usuario_id" not in session:
        return redirect("/login")


app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:at242855@localhost/meu_erp'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_AS_ASCII'] = False

db = SQLAlchemy(app)

# Modelo Contrato
class Contrato(db.Model):
    __tablename__ = 'contratos'

    id = db.Column(db.Integer, primary_key=True)
    proposta = db.Column(db.String(50), unique=True, nullable=False)
    data_checagem = db.Column(db.Date)
    razao_social = db.Column(db.String(255))
    cnpj_cpf = db.Column(db.String(20))
    celular = db.Column(db.String(20))
    email = db.Column(db.String(255))
    atividade_economica = db.Column(db.String(255))
    cidade = db.Column(db.String(100))
    nome_plano = db.Column(db.String(255))
    data_vigencia = db.Column(db.Date)
    vidas = db.Column(db.Integer)
    valor_parcela = db.Column(db.Numeric(10,2))
    parcela_atual = db.Column(db.Integer)
    status = db.Column(db.String(50))
    mes_cancelamento = db.Column(db.Date, nullable=True)
    verificado = db.Column(db.Boolean, default=False)
    contrato = db.Column(db.String(50), unique=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedores.id'))
    dias_atraso = db.Column(db.Integer, nullable=True)  # NOVO CAMPO
    acoes = db.relationship('AcaoCobranca', backref='contrato', lazy=True)
    envio_sms = db.Column(db.Boolean, default=True)
    cliente_critico = db.Column(db.Boolean, default=False)

    vendedor = db.relationship('Vendedor', backref=db.backref('contratos', lazy=True))

# Modelo Vendedor
class Vendedor(db.Model):
    __tablename__ = 'vendedores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), unique=True)
    cpf_cnpj = db.Column(db.String(20), nullable=True)
    celular = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True)

class AcaoCobranca(db.Model):
    __tablename__ = "acoes_cobranca"
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contratos.id"), nullable=False)
    tipo = db.Column(db.String(50))  # Ex: SMS, WhatsApp
    mensagem = db.Column(db.Text)
    dia_atraso = db.Column(db.Integer)
    parcela = db.Column(db.Integer)
    enviada_em = db.Column(db.DateTime)
    status_envio = db.Column(db.String(50))
    usuario = db.Column(db.String(255), nullable=True)



class ResponsavelCobranca(db.Model):
    __tablename__ = "responsaveis_cobranca"
    id = db.Column(db.Integer, primary_key=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey("contratos.id"), nullable=False)
    usuario = db.Column(db.String(255), nullable=False)

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # admin ou usuario



# Rota do dashboard inicial (página principal do sistema)
@app.route('/')
def dashboard():
    ativos = Contrato.query.filter(Contrato.status.in_(["Em dia", "Pago"])).count()
    atrasados = Contrato.query.filter_by(status="Em atraso").count()
    cancelados_inad = Contrato.query.filter_by(status="Cancelado por Inadimplência").count()
    cancelados_regra = Contrato.query.filter_by(status="Cancelado por Regra").count()
    total = Contrato.query.count()

    status_counts = {
        "Ativos": ativos,
        "Atrasados": atrasados,
        "Cancelados Inad.": cancelados_inad,
        "Cancelados Regra": cancelados_regra
    }

    return render_template('dashboard.html', 
                           status_counts=status_counts,
                           total=total)

# Rota para listar detalhadamente os contratos cadastrados
@app.route('/contratos')
def listar_contratos():
    busca = request.args.get("busca", "")
    responsavel = request.args.get("responsavel", "")
    status = request.args.get("status", "")
    parcela = request.args.get("parcela", type=int)
    atraso_min = request.args.get("atraso_min", type=int)
    atraso_max = request.args.get("atraso_max", type=int)
    ordenar_por = request.args.get("ordenar", "dias_atraso_desc")
    critico = request.args.get("critico", "")
    sms = request.args.get("sms", "")

    query = db.session.query(Contrato, Vendedor.nome.label('nome_vendedor')).join(Vendedor)

    if busca:
        query = query.filter(
            db.or_(
                Contrato.proposta.ilike(f"%{busca}%"),
                Contrato.contrato.ilike(f"%{busca}%"),
                Contrato.razao_social.ilike(f"%{busca}%"),
                Contrato.cnpj_cpf.ilike(f"%{busca}%"),
                Contrato.celular.ilike(f"%{busca}%")
            )
        )

    if status == "Em dia + Pago":
        query = query.filter(Contrato.status.in_(["Em dia", "Pago"]))
    elif status == "Cancelado Total":
        query = query.filter(Contrato.status.in_(["Cancelado por Inadimplência", "Cancelado por Regra"]))
    elif status:
        query = query.filter(Contrato.status == status)

    if responsavel:
        subquery_ids = db.session.query(ResponsavelCobranca.contrato_id).filter_by(usuario=responsavel).all()
        ids = [r[0] for r in subquery_ids]
        query = query.filter(Contrato.id.in_(ids))

    if critico == "1":
        query = query.filter(Contrato.cliente_critico == True)
    elif critico == "0":
        query = query.filter(Contrato.cliente_critico == False)

    if sms == "1":
        query = query.filter(Contrato.envio_sms == True)
    elif sms == "0":
        query = query.filter(Contrato.envio_sms == False)

    if parcela:
        query = query.filter(Contrato.parcela_atual == parcela)

    if atraso_min is not None:
        query = query.filter(Contrato.dias_atraso >= atraso_min)
    if atraso_max is not None:
        query = query.filter(Contrato.dias_atraso <= atraso_max)

    if ordenar_por == "dias_atraso_asc":
        query = query.order_by(Contrato.dias_atraso.asc())
    elif ordenar_por == "dias_atraso_desc":
        query = query.order_by(Contrato.dias_atraso.desc())
    elif ordenar_por == "parcela_asc":
        query = query.order_by(Contrato.parcela_atual.asc())
    elif ordenar_por == "parcela_desc":
        query = query.order_by(Contrato.parcela_atual.desc())

    resultados = query.all()

    responsaveis = db.session.query(ResponsavelCobranca.usuario).distinct().all()

    return render_template(
        "index.html",
        resultados=resultados,
        busca=busca,
        status=status,
        responsavel=responsavel,
        parcela=parcela,
        atraso_min=atraso_min,
        atraso_max=atraso_max,
        critico=critico,
        sms=sms,
        ordenar_por=ordenar_por,
        responsaveis=[r[0] for r in responsaveis]
    )


@app.route("/cobranca")
def painel_cobranca():
    session.pop('_flashes', None)

    if request.args:
        session["filtros_cobranca"] = request.args.to_dict()

    filtros = session.get("filtros_cobranca", {})

    busca = filtros.get("busca", "")
    responsavel = filtros.get("responsavel", "")
    status = filtros.get("status", "")
    try:
        parcela = int(filtros.get("parcela")) if filtros.get("parcela") else None
    except ValueError:
        parcela = None

    try:
        atraso_min = int(filtros.get("atraso_min")) if filtros.get("atraso_min") else None
    except ValueError:
        atraso_min = None

    try:
        atraso_max = int(filtros.get("atraso_max")) if filtros.get("atraso_max") else None
    except ValueError:
        atraso_max = None
    ordenar_por = filtros.get("ordenar", "dias_atraso_desc")
    critico = filtros.get("critico", "")
    sms = filtros.get("sms", "")

    query = Contrato.query.filter(Contrato.status == "Em atraso")

    if busca:
        query = query.filter(
            db.or_(
                Contrato.proposta.ilike(f"%{busca}%"),
                Contrato.contrato.ilike(f"%{busca}%"),
                Contrato.razao_social.ilike(f"%{busca}%"),
                Contrato.cnpj_cpf.ilike(f"%{busca}%"),
                Contrato.celular.ilike(f"%{busca}%")
            )
        )

    if status:
        query = query.filter(Contrato.status == status)

    if responsavel:
        subquery_ids = db.session.query(ResponsavelCobranca.contrato_id).filter_by(usuario=responsavel).all()
        ids = [r[0] for r in subquery_ids]
        query = query.filter(Contrato.id.in_(ids))
    
    if critico == "1":
        query = query.filter(Contrato.cliente_critico == True)
    if critico == "0":
        query = query.filter(Contrato.cliente_critico == False)

    if sms == "1":
        query = query.filter(Contrato.envio_sms == True)
    if sms == "0":
        query = query.filter(Contrato.envio_sms == False)

    if parcela:
        query = query.filter(Contrato.parcela_atual == parcela)

    if atraso_min is not None:
        query = query.filter(Contrato.dias_atraso >= atraso_min)
    if atraso_max is not None:
        query = query.filter(Contrato.dias_atraso <= atraso_max)

    # Ordenação
    if ordenar_por == "dias_atraso_asc":
        query = query.order_by(Contrato.dias_atraso.asc())
    elif ordenar_por == "dias_atraso_desc":
        query = query.order_by(Contrato.dias_atraso.desc())
    elif ordenar_por == "parcela_asc":
        query = query.order_by(Contrato.parcela_atual.asc())
    elif ordenar_por == "parcela_desc":
        query = query.order_by(Contrato.parcela_atual.desc())

    contratos = query.all()

    responsaveis = db.session.query(ResponsavelCobranca.usuario).distinct().all()

    lista = []
    for c in contratos:
        ultima = AcaoCobranca.query.filter_by(contrato_id=c.id).order_by(AcaoCobranca.dia_atraso.desc()).first()
        responsavel_obj = ResponsavelCobranca.query.filter_by(contrato_id=c.id).first()
        lista.append({
            "contrato": c,
            "ultima_acao": ultima,
            "responsavel": responsavel_obj.usuario if responsavel_obj else None
        })

    return render_template(
        "cobranca.html",
        contratos=lista,
        responsaveis=[r[0] for r in responsaveis],
        busca=busca,
        status=status,
        responsavel=responsavel,
        parcela=parcela,
        atraso_min=atraso_min,
        atraso_max=atraso_max,
        critico=critico,
        sms=sms,
        ordenar_por=ordenar_por
    )

@app.route("/toggle_sms/<int:contrato_id>")
def toggle_sms(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    contrato.envio_sms = not contrato.envio_sms
    db.session.commit()
    flash(f"Envio de SMS {'ativado' if contrato.envio_sms else 'desativado'} para este contrato.")
    return redirect(f"/historico/{contrato_id}")

@app.route("/toggle_critico/<int:contrato_id>")
def toggle_critico(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    contrato.cliente_critico = not contrato.cliente_critico
    db.session.commit()
    flash(f"Cliente {'marcado como CRÍTICO' if contrato.cliente_critico else 'removido de críticos'}.")
    return redirect(f"/historico/{contrato_id}")

@app.route("/historico/<int:contrato_id>")
def historico_cobranca(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    acoes = AcaoCobranca.query.filter_by(contrato_id=contrato_id).order_by(AcaoCobranca.dia_atraso).all()
    return render_template("historico.html", contrato=contrato, acoes=acoes)

from flask import request, jsonify

@app.route("/assumir/<int:contrato_id>", methods=["GET", "POST"])
def assumir_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)
    usuario_logado = session.get("usuario_nome", "Usuário de Cobrança")

    # Verifica se já existe responsável
    responsavel_existente = ResponsavelCobranca.query.filter_by(contrato_id=contrato.id).first()

    if responsavel_existente:
        responsavel_existente.usuario = usuario_logado
    else:
        novo = ResponsavelCobranca(contrato_id=contrato.id, usuario=usuario_logado)
        db.session.add(novo)

    db.session.commit()

    # Se for requisição via fetch(), retorna JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"status": "ok", "responsavel": usuario_logado})

    # Se for acesso direto, redireciona normalmente
    flash(f"Contrato {contrato.contrato} agora está sob responsabilidade de {usuario_logado}")
    return redirect("/cobranca")

@app.route("/registrar_acao/<int:contrato_id>", methods=["GET", "POST"])
def registrar_acao(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    # 🔽 Adiciona a busca pelo nome do vendedor
    vendedor = "-"
    if contrato.vendedor_id:
        vendedor_obj = Vendedor.query.get(contrato.vendedor_id)
        if vendedor_obj:
            vendedor = vendedor_obj.nome

    if request.method == "POST":
        tipo = request.form.get("tipo")  # exemplo: LIGACAO, WHATSAPP, EMAIL
        mensagem = request.form.get("mensagem")
        usuario_logado = session.get("usuario_nome", "Usuário de Cobrança")

        if not mensagem:
            flash("A mensagem é obrigatória.")
            return redirect(f"/registrar_acao/{contrato_id}")

        nova_acao = AcaoCobranca(
            contrato_id=contrato.id,
            tipo=tipo,
            mensagem=mensagem,
            dia_atraso=contrato.dias_atraso or 0,
            parcela=contrato.parcela_atual,
            enviada_em=agora_brasil(),
            status_envio="Manual",
            usuario=usuario_logado
        )
        db.session.add(nova_acao)
        db.session.commit()

        flash("Ação registrada com sucesso.")
        anchor = request.args.get("anchor")
        return redirect(f"/cobranca#{anchor}" if anchor else "/cobranca")

    # 🔽 Aqui é onde você passa o nome do vendedor para o template
    return render_template("registrar_acao.html", contrato=contrato, vendedor=vendedor)


@app.route("/relatorio_cobranca")
@login_required
@admin_required
def relatorio_cobranca():
    from datetime import datetime
    from sqlalchemy import extract

    mes = request.args.get("mes", datetime.today().month, type=int)
    ano = request.args.get("ano", datetime.today().year, type=int)
    usuario_filtro = request.args.get("usuario", "")

    hoje = datetime.today()
    primeiro_dia = datetime(ano, mes, 1)
    if mes == 12:
        proximo_mes = datetime(ano + 1, 1, 1)
    else:
        proximo_mes = datetime(ano, mes + 1, 1)

    # Contratos com ações manuais registradas no mês
    contratos_em_atraso = db.session.query(AcaoCobranca.contrato_id).filter(
        AcaoCobranca.enviada_em >= primeiro_dia,
        AcaoCobranca.enviada_em < proximo_mes
    ).distinct().all()
    contratos_ids = {c[0] for c in contratos_em_atraso}

    # Adicionar contratos cancelados no mês, mesmo sem ações manuais
    contratos_cancelados = Contrato.query.filter(
        Contrato.mes_cancelamento >= primeiro_dia,
        Contrato.mes_cancelamento < proximo_mes,
        Contrato.status.ilike('%Cancelado%')
    ).all()

    for contrato in contratos_cancelados:
        contratos_ids.add(contrato.id)

    contratos = Contrato.query.filter(Contrato.id.in_(contratos_ids)).all()

    # Métricas gerais
    pagos = sum(1 for c in contratos if c.status in ["Pago", "Em dia"])
    cancelados = sum(1 for c in contratos if "Cancelado" in c.status)
    ainda_em_atraso = sum(1 for c in contratos if c.status == "Em atraso")
    total = len(contratos)

    taxa_recuperacao = f"{round((pagos / total * 100), 2)}%" if total > 0 else "0%"
    taxa_cancelamento = f"{round((cancelados / total * 100), 2)}%" if total > 0 else "0%"

    acoes_no_mes = AcaoCobranca.query.filter(
        AcaoCobranca.enviada_em >= primeiro_dia,
        AcaoCobranca.enviada_em < proximo_mes
    ).count()

    usuarios = db.session.query(ResponsavelCobranca.usuario).distinct().all()

    if usuario_filtro:
        usuarios = [(usuario_filtro,)]

    resumo_usuarios = []

    for (usuario,) in usuarios:
        contratos_ids_subquery = db.session.query(ResponsavelCobranca.contrato_id).filter_by(usuario=usuario).subquery()
        contratos_usuario = Contrato.query.filter(Contrato.id.in_(contratos_ids_subquery)).all()

        pagos_usuario = sum(1 for c in contratos_usuario if c.status in ["Pago", "Em dia"])
        em_atraso_usuario = sum(1 for c in contratos_usuario if c.status == "Em atraso")
        cancelados_usuario = sum(1 for c in contratos_usuario if "Cancelado" in c.status)
        total_assumidos = len(contratos_usuario)

        acoes = AcaoCobranca.query.filter(
            AcaoCobranca.usuario == usuario,
            extract("month", AcaoCobranca.enviada_em) == mes,
            extract("year", AcaoCobranca.enviada_em) == ano
        ).all()

        ultima_acao_data = db.session.query(db.func.max(AcaoCobranca.enviada_em)).filter(
            AcaoCobranca.usuario == usuario,
            extract("month", AcaoCobranca.enviada_em) == mes,
            extract("year", AcaoCobranca.enviada_em) == ano
        ).scalar()

        ultima_acao = ultima_acao_data.strftime('%d/%m/%Y') if ultima_acao_data else None

        resumo_usuarios.append({
            "usuario": usuario,
            "assumidos": total_assumidos,
            "acoes": len(acoes),
            "ultima_acao": ultima_acao,
            "pagos": pagos_usuario,
            "em_atraso": em_atraso_usuario,
            "cancelados": cancelados_usuario
        })

    return render_template(
        "relatorio_cobranca.html",
        total=total,
        pagos=pagos,
        cancelados=cancelados,
        ainda_em_atraso=ainda_em_atraso,
        taxa_recuperacao=taxa_recuperacao,
        taxa_cancelamento=taxa_cancelamento,
        acoes=acoes_no_mes,
        resumo_usuarios=resumo_usuarios,
        mes=mes,
        ano=ano,
        usuarios_filtro=[u[0] for u in usuarios],
        usuario_selecionado=usuario_filtro
    )

@app.route("/exportar_relatorio")
def exportar_relatorio():
    from datetime import datetime
    from sqlalchemy import extract

    mes = request.args.get("mes", datetime.today().month, type=int)
    ano = request.args.get("ano", datetime.today().year, type=int)
    usuario = request.args.get("usuario", "")

    subquery = db.session.query(
        AcaoCobranca.contrato_id,
        db.func.max(AcaoCobranca.enviada_em).label("ultima_data")
    ).group_by(AcaoCobranca.contrato_id).subquery()

    acoes = db.session.query(AcaoCobranca).join(
        subquery,
        (AcaoCobranca.contrato_id == subquery.c.contrato_id) &
        (AcaoCobranca.enviada_em == subquery.c.ultima_data)
    ).filter(
        extract("month", AcaoCobranca.enviada_em) == mes,
        extract("year", AcaoCobranca.enviada_em) == ano
    )

    if usuario:
        acoes = acoes.filter(AcaoCobranca.usuario == usuario)

    acoes = acoes.all()
    hoje = datetime.today().date()

    dados = []
    for acao in acoes:
        contrato = Contrato.query.get(acao.contrato_id)
        dados.append({
            "Contrato": contrato.contrato,
            "Proposta": contrato.proposta,
            "Razão Social": contrato.razao_social,
            "CNPJ/CPF": contrato.cnpj_cpf,
            "Cliente Crítico": "Sim" if contrato.cliente_critico else "Não",
            "Atividade Econômica": contrato.atividade_economica or "",
            "Celular": contrato.celular,
            "E-mail": contrato.email,
            "Cidade": contrato.cidade,
            "Data de Vigência": contrato.data_vigencia.strftime("%d/%m/%Y") if contrato.data_vigencia else "",
            "Vidas": contrato.vidas,
            "Valor da Parcela": contrato.valor_parcela,
            "Parcela Atual": contrato.parcela_atual,
            "Dias de Atraso": contrato.dias_atraso,
            "Status Atual": contrato.status,
            "Mês de Cancelamento": contrato.mes_cancelamento.strftime("%m/%Y") if contrato.mes_cancelamento else "",
            "Vendedor": contrato.vendedor.nome if contrato.vendedor else "",
            "Última Ação": acao.tipo,
            "Responsável": acao.usuario or "-",
            "Data da Ação": acao.enviada_em.strftime("%d/%m/%Y %H:%M"),
            "Mensagem Enviada": acao.mensagem
        })

    df = pd.DataFrame(dados)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Relatório")

    output.seek(0)
    return send_file(
        output,
        download_name=f"relatorio_cobranca_{hoje.strftime('%Y_%m_%d')}.xlsx",
        as_attachment=True
    )


@app.route("/exportar_relatorio_atendentes")
def exportar_relatorio_atendentes():
    from datetime import datetime
    from sqlalchemy import extract

    hoje = datetime.today().date()
    mes = request.args.get("mes", hoje.month, type=int)
    ano = request.args.get("ano", hoje.year, type=int)
    usuario_filtro = request.args.get("usuario", "")

    usuarios = db.session.query(ResponsavelCobranca.usuario).distinct().all()
    if usuario_filtro:
        usuarios = [(usuario_filtro,)]

    linhas = []
    for (usuario,) in usuarios:
        contratos_ids = db.session.query(ResponsavelCobranca.contrato_id).filter_by(usuario=usuario).subquery()
        contratos = Contrato.query.filter(Contrato.id.in_(contratos_ids)).all()

        total_assumidos = len(contratos)
        pagos = sum(1 for c in contratos if c.status in ["Pago", "Em dia"])
        em_atraso = sum(1 for c in contratos if c.status == "Em atraso")
        cancelados = sum(1 for c in contratos if "Cancelado" in c.status)

        acoes = AcaoCobranca.query.filter(
            AcaoCobranca.usuario == usuario,
            extract("month", AcaoCobranca.enviada_em) == mes,
            extract("year", AcaoCobranca.enviada_em) == ano
        ).count()

        taxa = f"{round((pagos / total_assumidos * 100), 2)}%" if total_assumidos > 0 else "0%"

        linhas.append({
            "Atendente": usuario,
            "Contratos Assumidos": total_assumidos,
            "Ações Realizadas": acoes,
            "Contratos Pagos": pagos,
            "Contratos Ainda em Atraso": em_atraso,
            "Contratos Cancelados": cancelados,
            "Taxa de Recuperação": taxa
        })

    df = pd.DataFrame(linhas)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Atendentes")

    output.seek(0)
    return send_file(
        output,
        download_name=f"relatorio_atendentes_{hoje.strftime('%Y_%m_%d')}.xlsx",
        as_attachment=True
    )

@app.route("/editar_contrato", methods=["GET", "POST"])
def editar_contrato_busca():
    if request.method == "POST":
        contrato_numero = request.form.get("numero_contrato")
        contrato = Contrato.query.filter_by(contrato=contrato_numero).first()
        if contrato:
            return redirect(f"/editar_contrato/{contrato.id}")
        else:
            flash("Contrato não encontrado.")
            return redirect("/editar_contrato")

    return render_template("buscar_contrato.html")

@app.route("/editar_contrato/<int:contrato_id>", methods=["GET", "POST"])
def editar_cadastro_contrato(contrato_id):
    contrato = Contrato.query.get_or_404(contrato_id)

    if request.method == "POST":
        usuario_tipo = session.get("usuario_tipo", "")

        contrato.celular = request.form.get("celular")
        contrato.email = request.form.get("email")

        if usuario_tipo == "admin":
            contrato.razao_social = request.form.get("razao_social")
            contrato.nome_plano = request.form.get("nome_plano")
            contrato.vidas = request.form.get("vidas", type=int)
            contrato.valor_parcela = request.form.get("valor_parcela", type=float)
            contrato.parcela_atual = request.form.get("parcela_atual", type=int)
            contrato.status = request.form.get("status")
            id_vendedor = request.form.get("vendedor_id")
            if id_vendedor:
                contrato.vendedor_id = int(id_vendedor)

        db.session.commit()
        flash("Contrato atualizado com sucesso.")
        return redirect("/")

    vendedores = Vendedor.query.all()
    return render_template("editar_contrato.html", contrato=contrato, vendedores=vendedores)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        senha = request.form.get("senha")

        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session["usuario_id"] = usuario.id
            session["usuario_nome"] = usuario.nome
            session["usuario_tipo"] = usuario.tipo
            flash("Login realizado com sucesso.")
            return redirect("/")
        else:
            flash("E-mail ou senha inválidos.")

    return render_template("login.html")

@app.route("/cadastro_usuario", methods=["GET", "POST"])
@login_required
@admin_required
def cadastro_usuario():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        senha = request.form.get("senha")
        tipo = request.form.get("tipo")

        if not nome or not email or not senha or tipo not in ["admin", "usuario"]:
            flash("Todos os campos são obrigatórios e o tipo deve ser válido.")
            return redirect("/cadastro_usuario")

        existente = Usuario.query.filter_by(email=email).first()
        if existente:
            flash("Já existe um usuário com este e-mail.")
            return redirect("/cadastro_usuario")

        novo_usuario = Usuario(
            nome=nome,
            email=email,
            senha=generate_password_hash(senha),
            tipo=tipo
        )
        db.session.add(novo_usuario)
        db.session.commit()
        flash("Usuário cadastrado com sucesso!")
        return redirect("/cadastro_usuario")

    return render_template("cadastro_usuario.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema com sucesso.")
    return redirect(url_for("login"))

@app.route("/limpar_filtros_cobranca")
def limpar_filtros_cobranca():
    session.pop("filtros_cobranca", None)
    return redirect("/cobranca")
   

if __name__ == '__main__':
    app.run(debug=True)
