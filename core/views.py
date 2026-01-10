from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from .models import Curso, Inscricao, ConfiguracaoEscola, Escola, AnoAcademico, Notificacao, PerfilUsuario, Subscricao, PagamentoSubscricao, RecuperacaoSenha, Documento, Semestre
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.db import IntegrityError
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from datetime import datetime, date
from django.conf import settings
import os

def processar_aprovacoes_curso(curso_id):
    curso = Curso.objects.get(id=curso_id)
    inscricoes_com_nota = curso.inscricoes.filter(nota_teste__isnull=False, nota_teste__gte=curso.nota_minima).order_by('-nota_teste')
    
    for inscricao in curso.inscricoes.all():
        inscricao.aprovado = False
        inscricao.save()
    
    vagas_disponiveis = curso.vagas
    for i, inscricao in enumerate(inscricoes_com_nota):
        if i < vagas_disponiveis:
            inscricao.aprovado = True
            inscricao.data_resultado = timezone.now()
            inscricao.save()
    
    messages.success(None, 'Processo de aprovação concluído com sucesso!')

def index_redirect(request):
    """Redireciona para login se não autenticado, caso contrário para painel principal"""
    if request.user.is_authenticated:
        return redirect('painel_principal')
    return redirect('login')

@login_required
def index(request):
    ano_atual = AnoAcademico.objects.filter(ano_atual=True).first()
    semestre_atual = None
    if ano_atual:
        semestre_atual = ano_atual.semestres.filter(ativo=True).first()
    
    cursos = Curso.objects.filter(ativo=True)
    config = ConfiguracaoEscola.objects.first()
    anos_academicos = AnoAcademico.objects.all()
    
    # Adicionar cálculo de receita diária (exemplo simplificado)
    # Aqui você pode buscar do modelo de Pagamentos se existir
    receita_hoje = 0.00
    
    return render(request, 'core/index.html', {
        'cursos': cursos,
        'config': config,
        'anos_academicos': anos_academicos,
        'ano_atual': ano_atual,
        'semestre_atual': semestre_atual,
        'receita_hoje': receita_hoje
    })

def inscricao_create(request, curso_id):
    """View para criar inscrição em um curso. Apenas cursos ativos aceitam inscrições."""
    curso = get_object_or_404(Curso, id=curso_id)
    cursos = Curso.objects.filter(ativo=True)
    anos_academicos = AnoAcademico.objects.filter(ano_atual=True)
    
    # Validar se o curso está ativo
    if not curso.ativo:
        messages.error(
            request, 
            f'O curso "{curso.nome}" está indisponível para inscrições. '
            f'Por favor, entre em contato com a administração para mais informações.'
        )
        return redirect('index')
    
    context = {
        'curso': curso,
        'cursos': cursos,
        'anos_academicos': anos_academicos
    }
    if curso.requer_prerequisitos:
        context['prerequisitos'] = curso.prerequisitos.all()
    
    if request.method == 'POST':
        # Validar BI único
        bilhete_identidade = request.POST.get('bilhete_identidade')
        if bilhete_identidade and Inscricao.objects.filter(bilhete_identidade=bilhete_identidade).exists():
            messages.error(request, 'Este Bilhete de Identidade já está registrado no sistema!')
            return render(request, 'core/inscricao_form.html', {'curso': curso})
        
        # Validar email único em inscrições
        email = request.POST.get('email')
        if email and Inscricao.objects.filter(email=email).exists():
            messages.error(request, 'Este email já está sendo usado em outra inscrição!')
            return render(request, 'core/inscricao_form.html', {'curso': curso})
        
        # Validar telefone único em inscrições
        telefone = request.POST.get('telefone')
        if telefone and Inscricao.objects.filter(telefone=telefone).exists():
            messages.error(request, 'Este telefone já está sendo usado em outra inscrição!')
            return render(request, 'core/inscricao_form.html', {'curso': curso})
        
        # Obter escola
        escola_id = request.POST.get('escola_id')
        escola = None
        if escola_id:
            try:
                escola = Escola.objects.get(id=escola_id)
            except Escola.DoesNotExist:
                pass
        
        # 1. Informações Pessoais
        inscricao = Inscricao(
            curso=curso,
            primeiro_nome=request.POST['primeiro_nome'],
            nomes_meio=request.POST.get('nomes_meio', ''),
            apelido=request.POST['apelido'],
            data_nascimento=request.POST['data_nascimento'],
            local_nascimento=request.POST['local_nascimento'],
            nacionalidade=request.POST['nacionalidade'],
            bilhete_identidade=request.POST['bilhete_identidade'],
            data_validade_bi=request.POST.get('data_validade_bi') or None,
            sexo=request.POST['sexo'],
            estado_civil=request.POST.get('estado_civil', 'S'),
            endereco=request.POST['endereco'],
            telefone=request.POST['telefone'],
            email=request.POST.get('email'),
            # Documentos
            arquivo_bi=request.FILES.get('arquivo_bi'),
            arquivo_certificado=request.FILES.get('arquivo_certificado'),
            status_inscricao='submetida',
            # 2. Informações Académicas
            escola=escola,
            ano_conclusao=request.POST['ano_conclusao'],
            certificados_obtidos=request.POST.get('certificados_obtidos', ''),
            historico_escolar=request.POST.get('historico_escolar', ''),
            turno_preferencial=request.POST.get('turno_preferencial', 'M'),
            # 3. Informações Financeiras
            numero_comprovante=request.POST.get('numero_comprovante', ''),
            responsavel_financeiro_nome=request.POST.get('responsavel_financeiro_nome', ''),
            responsavel_financeiro_telefone=request.POST.get('responsavel_financeiro_telefone', ''),
            responsavel_financeiro_relacao=request.POST.get('responsavel_financeiro_relacao', ''),
            # 4. Responsáveis
            responsavel_legal_nome=request.POST.get('responsavel_legal_nome', ''),
            responsavel_legal_vinculo=request.POST.get('responsavel_legal_vinculo', ''),
            responsavel_legal_telefone=request.POST.get('responsavel_legal_telefone', ''),
            responsavel_pedagogico_nome=request.POST.get('responsavel_pedagogico_nome', ''),
            responsavel_pedagogico_vinculo=request.POST.get('responsavel_pedagogico_vinculo', ''),
            responsavel_pedagogico_telefone=request.POST.get('responsavel_pedagogico_telefone', ''),
        )
        
        inscricao.save()
        
        # Criar histórico académico e salvar notas se curso requer pré-requisitos
        if curso.requer_prerequisitos:
            from .models import HistoricoAcademico, NotaDisciplina
            historico, created = HistoricoAcademico.objects.get_or_create(inscricao=inscricao)
            
            for prereq in curso.prerequisitos.all():
                nota_str = request.POST.get(f'nota_{prereq.disciplina_prerequisito.id}')
                if nota_str:
                    try:
                        nota = float(nota_str)
                        ano = int(request.POST.get(f'ano_{prereq.disciplina_prerequisito.id}', 2024))
                        NotaDisciplina.objects.update_or_create(
                            historico=historico,
                            disciplina=prereq.disciplina_prerequisito,
                            defaults={'nota': nota, 'ano_conclusao': ano}
                        )
                    except (ValueError, TypeError):
                        pass
        
        messages.success(request, f'Inscrição realizada com sucesso! Seu número de inscrição é: {inscricao.numero_inscricao}')
        return redirect('inscricao_consulta', numero=inscricao.numero_inscricao)
    
    return render(request, 'core/inscricao_form.html', context)

def inscricao_consulta(request, numero):
    inscricao = get_object_or_404(Inscricao, numero_inscricao=numero)
    return render(request, 'core/inscricao_consulta.html', {'inscricao': inscricao})

def inscricao_buscar(request):
    if request.method == 'POST':
        numero = request.POST.get('numero_inscricao', '').strip()
        if numero:
            try:
                inscricao = Inscricao.objects.get(numero_inscricao=numero)
                return redirect('inscricao_consulta', numero=numero)
            except Inscricao.DoesNotExist:
                messages.error(request, 'Número de inscrição não encontrado!')
    
    return render(request, 'core/inscricao_buscar.html')

def gerar_pdf_confirmacao(request, numero):
    inscricao = get_object_or_404(Inscricao, numero_inscricao=numero)
    config = ConfiguracaoEscola.objects.first()
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor='#1a1a1a',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#333333',
        spaceAfter=12,
        alignment=TA_LEFT
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#000000',
        spaceAfter=8,
        alignment=TA_LEFT
    )
    
    logo_path = os.path.join(settings.BASE_DIR, 'core', 'static', 'core', 'images', 'siga-logo.png')
    if os.path.exists(logo_path):
        try:
            img = Image(logo_path, width=4*cm, height=1.5*cm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Spacer(1, 0.5*cm))
        except:
            pass
    
    escola_nome = config.nome_escola if config else "Sistema Escolar"
    story.append(Paragraph(escola_nome, title_style))
    story.append(Paragraph("CONFIRMAÇÃO DE INSCRIÇÃO", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    if config and config.template_confirmacao_inscricao:
        template = config.template_confirmacao_inscricao
    else:
        template = "CONFIRMAÇÃO DE INSCRIÇÃO\n\nNome: {nome}\nCurso: {curso}\nNúmero de Inscrição: {numero}\nData: {data}"
    
    conteudo = template.format(
        nome=inscricao.nome_completo,
        curso=inscricao.curso.nome,
        numero=inscricao.numero_inscricao,
        data=inscricao.data_inscricao.strftime('%d/%m/%Y')
    )
    
    for linha in conteudo.split('\n'):
        if linha.strip():
            story.append(Paragraph(linha, normal_style))
    
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(f"Data de Nascimento: {inscricao.data_nascimento.strftime('%d/%m/%Y')}", normal_style))
    story.append(Paragraph(f"Bilhete de Identidade: {inscricao.bilhete_identidade}", normal_style))
    story.append(Paragraph(f"Telefone: {inscricao.telefone}", normal_style))
    if inscricao.email:
        story.append(Paragraph(f"Email: {inscricao.email}", normal_style))
    
    if inscricao.nota_teste is not None:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"Nota do Teste: {inscricao.nota_teste}", normal_style))
        status = "APROVADO" if inscricao.aprovado else "NÃO APROVADO"
        story.append(Paragraph(f"Status: {status}", normal_style))
    
    doc.build(story)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="confirmacao_{inscricao.numero_inscricao}.pdf"'
    
    return response

@login_required
def admissao_estudantes(request):
    cursos = Curso.objects.filter(ativo=True)
    config = ConfiguracaoEscola.objects.first()
    return render(request, 'core/admissao.html', {
        'cursos': cursos,
        'config': config
    })

@login_required
def admissao_inscricao(request):
    cursos = Curso.objects.filter(ativo=True)
    config = ConfiguracaoEscola.objects.first()
    
    if request.method == 'POST':
        curso_id = request.POST.get('curso_id')
        if curso_id:
            return redirect('inscricao_create', curso_id=curso_id)
    
    return render(request, 'core/admissao_inscricao.html', {
        'cursos': cursos,
        'config': config
    })

@login_required
def cursos_lista(request):
    cursos = Curso.objects.all().order_by('-ativo', 'nome')
    return render(request, 'core/cursos_lista.html', {'cursos': cursos})

@login_required
def curso_create(request):
    if request.method == 'POST':
        curso = Curso(
            nome=request.POST['nome'],
            codigo=request.POST.get('codigo', 'CURSO-' + request.POST['nome'][:3].upper()),
            grau=request.POST['grau'],
            regime=request.POST['regime'],
            modalidade=request.POST['modalidade'],
            vagas=request.POST['vagas'],
            duracao_meses=request.POST['duracao_meses'],
            nota_minima=request.POST['nota_minima'],
            descricao=request.POST.get('descricao', ''),
            requer_prerequisitos='requer_prerequisitos' in request.POST
        )
        curso.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Curso criado com sucesso!'})
        messages.success(request, f'Curso "{curso.nome}" cadastrado com sucesso!')
        return redirect('cursos_lista')
    return render(request, 'core/curso_form.html')

@login_required
def curso_edit(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    if request.method == 'POST':
        curso.nome = request.POST['nome']
        curso.grau = request.POST['grau']
        curso.regime = request.POST['regime']
        curso.modalidade = request.POST['modalidade']
        curso.vagas = request.POST['vagas']
        curso.duracao_meses = request.POST['duracao_meses']
        curso.nota_minima = request.POST['nota_minima']
        curso.descricao = request.POST.get('descricao', '')
        curso.requer_prerequisitos = 'requer_prerequisitos' in request.POST
        curso.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Curso atualizado com sucesso!'})
        messages.success(request, f'Curso "{curso.nome}" atualizado com sucesso!')
        return redirect('cursos_lista')
    return render(request, 'core/curso_form.html', {'curso': curso})

@login_required
def curso_toggle(request, curso_id):
    curso = get_object_or_404(Curso, id=curso_id)
    curso.ativo = not curso.ativo
    curso.save()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'ativo': curso.ativo,
            'message': f'Curso {"ativado" if curso.ativo else "desativado"} com sucesso!'
        })
    status = "ativado" if curso.ativo else "desativado"
    messages.success(request, f'Curso "{curso.nome}" {status} com sucesso!')
    return redirect('cursos_lista')

@login_required
def curso_delete(request, curso_id):
    if request.method == 'POST':
        curso = get_object_or_404(Curso, id=curso_id)
        nome = curso.nome
        curso.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Curso "{nome}" deletado com sucesso!'})
        messages.success(request, f'Curso "{nome}" deletado com sucesso!')
    return redirect('cursos_lista')

@login_required
def disciplina_create(request):
    if request.method == 'POST':
        curso_id = request.POST.get('curso_id')
        curso = get_object_or_404(Curso, id=curso_id)
        disciplina = Disciplina.objects.create(
            nome=request.POST['nome'],
            curso=curso,
            carga_horaria=request.POST['carga_horaria']
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Disciplina criada com sucesso!'})
        messages.success(request, f'Disciplina "{disciplina.nome}" criada com sucesso!')
        return redirect('cursos_lista')
    return redirect('cursos_lista')

"""
@login_required
def dashboard(request):
    cursos = Curso.objects.all()
    total_inscricoes = Inscricao.objects.count()
    total_aprovados = Inscricao.objects.filter(aprovado=True).count()
    total_reprovados = Inscricao.objects.filter(aprovado=False, nota_teste__isnull=False).count()
    aguardando_nota = Inscricao.objects.filter(nota_teste__isnull=True).count()
    
    return render(request, 'core/dashboard.html', {
        'cursos': cursos,
        'total_inscricoes': total_inscricoes,
        'total_aprovados': total_aprovados,
        'total_reprovados': total_reprovados,
        'aguardando_nota': aguardando_nota
    })
"""

def consultar_aprovacao(request):
    if request.method == 'POST':
        query = request.POST.get('numero_ou_bi', '').strip()
        if query:
            inscricao = Inscricao.objects.filter(
                Q(numero_inscricao=query) | Q(bilhete_identidade=query)
            ).first()
            
            if inscricao:
                if inscricao.aprovado:
                    messages.success(request, f'Parabéns {inscricao.nome_completo}! Você foi aprovado. Pode prosseguir com a matrícula.')
                    return render(request, 'core/consultar_aprovacao.html', {
                        'inscricao': inscricao,
                        'aprovado': True
                    })
                elif inscricao.nota_teste is not None:
                    messages.warning(request, f'Lamentamos {inscricao.nome_completo}, mas você não foi selecionado para este curso.')
                else:
                    messages.info(request, f'Olá {inscricao.nome_completo}, seu teste ainda está sendo processado. Por favor, aguarde.')
            else:
                messages.error(request, 'Inscrição ou BI não encontrado no sistema.')
    
    return render(request, 'core/consultar_aprovacao.html')

@require_http_methods(["GET"])
def verificar_existente(request):
    query = request.GET.get('q', '').strip()
    campo = request.GET.get('campo', '').strip()
    
    if len(query) < 3 or campo not in ['nome_completo', 'bilhete_identidade', 'telefone']:
        return JsonResponse({'encontrado': False})
    
    if campo == 'nome_completo':
        existente = Inscricao.objects.filter(nome_completo__icontains=query).first()
    elif campo == 'bilhete_identidade':
        existente = Inscricao.objects.filter(bilhete_identidade=query).first()
    else: # telefone
        existente = Inscricao.objects.filter(telefone__contains=query).first()
        
    if existente:
        return JsonResponse({
            'encontrado': True,
            'valor': getattr(existente, campo),
            'nome': existente.nome_completo,
            'id': existente.id
        })
        
    return JsonResponse({'encontrado': False})

@require_http_methods(["GET"])
def escolas_autocomplete(request):
    """Retorna escolas para autocomplete"""
    query = request.GET.get('q', '')
    escolas = Escola.objects.filter(nome__icontains=query)[:10]
    
    resultados = [
        {
            'id': escola.id,
            'nome': escola.nome,
            'municipio': escola.municipio,
            'provincia': escola.provincia
        }
        for escola in escolas
    ]
    
    return JsonResponse({'escolas': resultados})

@require_http_methods(["POST"])
def escola_create_ajax(request):
    """Cria uma escola via AJAX"""
    try:
        data = json.loads(request.body)
        nome = data.get('nome', '').strip()
        municipio = data.get('municipio', '').strip()
        provincia = data.get('provincia', '').strip()
        tipo = data.get('tipo', 'Pública')
        
        if not nome:
            return JsonResponse({'success': False, 'error': 'Nome da escola é obrigatório'}, status=400)
        
        escola = Escola.objects.create(
            nome=nome,
            municipio=municipio,
            provincia=provincia,
            tipo=tipo
        )
        
        return JsonResponse({
            'success': True,
            'escola': {
                'id': escola.id,
                'nome': escola.nome,
                'municipio': escola.municipio,
                'provincia': escola.provincia
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_http_methods(["POST"])
def trocar_ano_academico(request):
    """Trocar ano acadêmico ativo"""
    try:
        ano_id = request.POST.get('ano_id')
        if not ano_id:
            return JsonResponse({'success': False, 'error': 'ID do ano não fornecido'}, status=400)
        
        ano = get_object_or_404(AnoAcademico, id=ano_id)
        
        # Desativar todos os anos
        AnoAcademico.objects.all().update(ativo=False)
        
        # Ativar o ano selecionado
        ano.ativo = True
        ano.save()
        
        return JsonResponse({
            'success': True,
            'ano': str(ano)
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def ano_academico_lista(request):
    anos = AnoAcademico.objects.all()
    return render(request, 'core/ano_academico_lista.html', {'anos': anos})

@login_required
def semestre_lista(request, ano_id):
    ano = get_object_or_404(AnoAcademico, id=ano_id)
    semestres = ano.semestres.all()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/partials/semestre_lista_inner.html', {'ano': ano, 'semestres': semestres})
    return render(request, 'core/semestre_lista.html', {'ano': ano, 'semestres': semestres})

@login_required
def ano_academico_create(request):
    if request.method == 'POST':
        codigo = request.POST.get('codigo')
        descricao = request.POST.get('descricao')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        estado = request.POST.get('estado')
        ano_atual = 'ano_atual' in request.POST
        
        AnoAcademico.objects.create(
            codigo=codigo,
            descricao=descricao,
            data_inicio=data_inicio,
            data_fim=data_fim,
            estado=estado,
            ano_atual=ano_atual,
            criado_por=request.user
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "Ano Académico criado com sucesso!"})
        messages.success(request, "Ano Académico criado com sucesso!")
        return redirect('ano_academico_lista')
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/partials/ano_academico_form_inner.html')
    return render(request, 'core/ano_academico_form.html')

@login_required
def ano_academico_edit(request, pk):
    ano = get_object_or_404(AnoAcademico, pk=pk)
    
    if ano.estado == 'ENCERRADO':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': "Erro: Este ano está encerrado e não pode ser editado."})
        messages.error(request, "Este ano está encerrado e não pode ser editado.")
        return redirect('ano_academico_lista')

    if request.method == 'POST':
        ano.codigo = request.POST.get('codigo')
        ano.descricao = request.POST.get('descricao')
        ano.data_inicio = request.POST.get('data_inicio')
        ano.data_fim = request.POST.get('data_fim')
        ano.estado = request.POST.get('estado')
        ano.ano_atual = 'ano_atual' in request.POST
        ano.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "Ano Académico atualizado com sucesso!"})
        messages.success(request, "Ano Académico atualizado com sucesso!")
        return redirect('ano_academico_lista')
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/partials/ano_academico_form_inner.html')
    return render(request, 'core/ano_academico_form.html')

@login_required
def semestre_create(request, ano_id):
    ano = get_object_or_404(AnoAcademico, id=ano_id)
    if request.method == 'POST':
        nome = request.POST.get('nome')
        data_inicio = request.POST.get('data_inicio')
        data_fim = request.POST.get('data_fim')
        ativo = 'ativo' in request.POST
        
        Semestre.objects.create(
            ano_academico=ano,
            nome=nome,
            data_inicio=data_inicio,
            data_fim=data_fim,
            ativo=ativo
        )
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "Semestre criado com sucesso!"})
        messages.success(request, "Semestre criado com sucesso!")
        return redirect('semestre_lista', ano_id=ano.id)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/partials/semestre_form_inner.html', {'ano': ano})
    return render(request, 'core/semestre_form.html', {'ano': ano})

@login_required
def semestre_edit(request, pk):
    semestre = get_object_or_404(Semestre, pk=pk)
    if request.method == 'POST':
        semestre.nome = request.POST.get('nome')
        semestre.data_inicio = request.POST.get('data_inicio')
        semestre.data_fim = request.POST.get('data_fim')
        semestre.ativo = 'ativo' in request.POST
        semestre.save()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': "Semestre atualizado com sucesso!"})
        messages.success(request, "Semestre atualizado com sucesso!")
        return redirect('semestre_lista', ano_id=semestre.ano_academico.id)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/partials/semestre_form_inner.html', {'semestre': semestre, 'ano': semestre.ano_academico})
    return render(request, 'core/semestre_form.html', {'semestre': semestre, 'ano': semestre.ano_academico})

def login_view(request):
    """View de login personalizada"""
    from .models import Subscricao
    
    if request.user.is_authenticated:
        return redirect('painel_principal')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if not hasattr(user, 'perfil'):
                from .models import PerfilUsuario
                PerfilUsuario.objects.get_or_create(user=user)
            
            if user.perfil.nivel_acesso == 'pendente':
                messages.warning(request, 'Sua conta está aguardando aprovação do administrador. Você receberá acesso assim que seu perfil for atribuído.')
                return render(request, 'core/login.html')
            
            auth_login(request, user)
            messages.success(request, f'Bem-vindo(a) de volta, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'painel_principal')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuário ou senha inválidos!')
    
    return render(request, 'core/login.html')

def registro_view(request):
    """View de registro de usuário"""
    if request.user.is_authenticated:
        return redirect('painel_principal')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        telefone = request.POST.get('telefone')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            messages.error(request, 'As senhas não coincidem!')
            return render(request, 'core/registro.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Nome de usuário já existe!')
            return render(request, 'core/registro.html')
        
        if email and User.objects.filter(email=email).exists():
            messages.error(request, 'Este email já está sendo usado por outro usuário!')
            return render(request, 'core/registro.html')
        
        if telefone and PerfilUsuario.objects.filter(telefone=telefone).exists():
            messages.error(request, 'Este telefone já está sendo usado por outro usuário!')
            return render(request, 'core/registro.html')
        
        for user in User.objects.all():
            if user.check_password(password1):
                messages.error(request, 'Esta senha já está sendo usada por outro usuário. Por favor, escolha uma senha diferente.')
                return render(request, 'core/registro.html')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
            
            if hasattr(user, 'perfil'):
                user.perfil.telefone = telefone
                user.perfil.save()
                messages.success(request, 'Registro realizado com sucesso! Aguarde a aprovação do administrador para acessar o sistema.')
                return redirect('login')
            else:
                messages.error(request, 'Erro: Perfil de usuário já existe. Entre em contato com o administrador.')
                user.delete()
                return render(request, 'core/registro.html')
                
        except IntegrityError:
            messages.error(request, 'Erro: Perfil de usuário já existe para este usuário. Entre em contato com o administrador.')
            return render(request, 'core/registro.html')
        except Exception as e:
            messages.error(request, f'Erro ao criar conta. Por favor, tente novamente.')
            return render(request, 'core/registro.html')
    
    return render(request, 'core/registro.html')

def logout_view(request):
    """View de logout"""
    auth_logout(request)
    return redirect('login')

@login_required
def notificacoes_view(request):
    """View para listar notificações do usuário"""
    notificacoes = Notificacao.objects.filter(
        Q(global_notificacao=True) | Q(destinatarios=request.user),
        ativa=True
    ).distinct().order_by('-data_criacao')
    
    nao_lidas = notificacoes.exclude(lida_por=request.user)
    
    # Ao marcar como lida ou voltar, redireciona para o perfil
    if request.GET.get('action') == 'marcar_lida':
        notificacao_id = request.GET.get('id')
        if notificacao_id:
            notificacao = get_object_or_404(Notificacao, id=notificacao_id)
            notificacao.marcar_como_lida(request.user)
            return redirect('perfil_usuario')

    context = {
        'notificacoes': notificacoes,
        'nao_lidas_count': nao_lidas.count(),
        'active_tab': 'notificacoes'
    }
    return render(request, 'core/notificacoes.html', context)

@login_required
@require_http_methods(["POST"])
def marcar_notificacao_lida(request, notificacao_id):
    """Marcar notificação como lida"""
    notificacao = get_object_or_404(Notificacao, id=notificacao_id)
    notificacao.marcar_como_lida(request.user)
    return JsonResponse({'success': True})

@login_required
def get_notificacoes_count(request):
    """Retorna contagem de notificações não lidas"""
    count = Notificacao.objects.filter(
        Q(global_notificacao=True) | Q(destinatarios=request.user),
        ativa=True
    ).exclude(lida_por=request.user).distinct().count()
    
    return JsonResponse({'count': count})

def pagamento_subscricao_view(request):
    """View para efetuar pagamento de subscrição"""
    from datetime import datetime
    
    subscricao = Subscricao.objects.filter(estado__in=['ativo', 'teste']).first()
    
    if not subscricao:
        messages.error(request, 'Nenhuma subscrição encontrada no sistema!')
        return redirect('login')
    
    if request.method == 'POST':
        plano = request.POST.get('plano')
        valor = request.POST.get('valor')
        data_pagamento = request.POST.get('data_pagamento')
        numero_referencia = request.POST.get('numero_referencia', '')
        comprovante = request.FILES.get('comprovante')
        observacoes = request.POST.get('observacoes', '')
        
        if not all([plano, valor, data_pagamento, comprovante]):
            messages.error(request, 'Por favor, preencha todos os campos obrigatórios!')
            return render(request, 'core/pagamento_subscricao.html', {'subscricao': subscricao})
        
        pagamento = PagamentoSubscricao.objects.create(
            subscricao=subscricao,
            plano_escolhido=plano,
            valor=valor,
            data_pagamento=datetime.strptime(data_pagamento, '%Y-%m-%d').date(),
            numero_referencia=numero_referencia,
            comprovante=comprovante,
            observacoes=observacoes,
            status='pendente'
        )
        
        messages.success(request, f'Pagamento registrado com sucesso! Número de referência: {pagamento.id:06d}. Aguarde a aprovação do administrador.')
        return redirect('login')
    
    return render(request, 'core/pagamento_subscricao.html', {'subscricao': subscricao})

def renovar_subscricao_view(request):
    """View pública para renovação de subscrição"""
    from datetime import datetime
    
    subscricao = Subscricao.objects.filter(estado__in=['ativo', 'teste']).first()
    
    if not subscricao:
        messages.error(request, 'Nenhuma subscrição encontrada no sistema!')
        return redirect('login')
    
    if request.method == 'POST':
        plano = request.POST.get('plano')
        valor = request.POST.get('valor')
        data_pagamento = request.POST.get('data_pagamento')
        numero_referencia = request.POST.get('numero_referencia', '')
        comprovante = request.FILES.get('comprovante')
        observacoes = request.POST.get('observacoes', '')
        
        if not all([plano, valor, data_pagamento, comprovante]):
            messages.error(request, 'Por favor, preencha todos os campos obrigatórios!')
            return render(request, 'core/renovar_subscricao.html', {'subscricao': subscricao})
        
        pagamento = PagamentoSubscricao.objects.create(
            subscricao=subscricao,
            plano_escolhido=plano,
            valor=valor,
            data_pagamento=datetime.strptime(data_pagamento, '%Y-%m-%d').date(),
            numero_referencia=numero_referencia,
            comprovante=comprovante,
            observacoes=observacoes,
            status='pendente'
        )
        
        messages.success(request, f'Pagamento registrado com sucesso! Número de referência: {pagamento.id:06d}. Aguarde a aprovação do administrador.')
        return redirect('login')
    
    return render(request, 'core/renovar_subscricao.html', {'subscricao': subscricao})

def esqueci_senha_view(request):
    """View para escolher método de recuperação de senha"""
    if request.method == 'POST':
        identificador = request.POST.get('identificador')
        metodo = request.POST.get('metodo')
        
        try:
            user = User.objects.filter(Q(username=identificador) | Q(email=identificador)).first()
            
            if not user:
                messages.error(request, 'Usuário não encontrado!')
                return render(request, 'core/esqueci_senha.html')
            
            perfil = PerfilUsuario.objects.filter(user=user).first()
            
            if metodo == 'telefone':
                if not perfil or not perfil.telefone:
                    messages.error(request, 'Este usuário não possui telefone cadastrado!')
                    return render(request, 'core/esqueci_senha.html')
                
                import random
                from datetime import timedelta
                from django.utils import timezone
                
                codigo_otp = str(random.randint(100000, 999999))
                
                recuperacao = RecuperacaoSenha.objects.create(
                    user=user,
                    tipo='telefone',
                    codigo_otp=codigo_otp,
                    telefone_enviado=perfil.telefone,
                    data_expiracao=timezone.now() + timedelta(minutes=10)
                )
                
                request.session['recuperacao_id'] = recuperacao.id
                messages.info(request, f'Código OTP enviado para o telefone {perfil.telefone}')
                return redirect('validar_otp')
                
            elif metodo == 'email':
                if not user.email:
                    messages.error(request, 'Este usuário não possui email cadastrado!')
                    return render(request, 'core/esqueci_senha.html')
                
                import secrets
                from datetime import timedelta
                from django.utils import timezone
                
                token = secrets.token_urlsafe(32)
                
                recuperacao = RecuperacaoSenha.objects.create(
                    user=user,
                    tipo='email',
                    token=token,
                    email_enviado=user.email,
                    data_expiracao=timezone.now() + timedelta(hours=1)
                )
                
                messages.info(request, f'Link de recuperação enviado para {user.email}')
                return redirect('login')
        
        except Exception as e:
            messages.error(request, f'Erro ao processar recuperação: {str(e)}')
    
    return render(request, 'core/esqueci_senha.html')

def validar_otp_view(request):
    """View para validar código OTP e redefinir senha"""
    recuperacao_id = request.session.get('recuperacao_id')
    
    if not recuperacao_id:
        messages.error(request, 'Sessão expirada! Solicite nova recuperação.')
        return redirect('esqueci_senha')
    
    try:
        recuperacao = RecuperacaoSenha.objects.get(id=recuperacao_id, tipo='telefone', usado=False)
        
        if recuperacao.esta_expirado():
            messages.error(request, 'Código OTP expirado! Solicite nova recuperação.')
            return redirect('esqueci_senha')
        
        if request.method == 'POST':
            codigo = request.POST.get('codigo_otp')
            nova_senha = request.POST.get('nova_senha')
            confirmar_senha = request.POST.get('confirmar_senha')
            
            if codigo != recuperacao.codigo_otp:
                messages.error(request, 'Código OTP inválido!')
                return render(request, 'core/validar_otp.html', {'recuperacao': recuperacao})
            
            if nova_senha != confirmar_senha:
                messages.error(request, 'As senhas não coincidem!')
                return render(request, 'core/validar_otp.html', {'recuperacao': recuperacao})
            
            if len(nova_senha) < 6:
                messages.error(request, 'A senha deve ter no mínimo 6 caracteres!')
                return render(request, 'core/validar_otp.html', {'recuperacao': recuperacao})
            
            for user_check in User.objects.exclude(id=recuperacao.user.id):
                if user_check.check_password(nova_senha):
                    messages.error(request, 'Esta senha já está sendo usada por outro usuário. Por favor, escolha uma senha diferente.')
                    return render(request, 'core/validar_otp.html', {'recuperacao': recuperacao})
            
            user = recuperacao.user
            user.set_password(nova_senha)
            user.save()
            
            recuperacao.marcar_como_usado()
            del request.session['recuperacao_id']
            
            messages.success(request, 'Senha redefinida com sucesso! Faça login com sua nova senha.')
            return redirect('login')
        
        return render(request, 'core/validar_otp.html', {'recuperacao': recuperacao})
    
    except RecuperacaoSenha.DoesNotExist:
        messages.error(request, 'Recuperação inválida!')
        return redirect('esqueci_senha')

def redefinir_senha_email_view(request, token):
    """View para redefinir senha via link de email"""
    try:
        recuperacao = RecuperacaoSenha.objects.get(token=token, tipo='email', usado=False)
        
        if recuperacao.esta_expirado():
            messages.error(request, 'Link expirado! Solicite nova recuperação.')
            return redirect('esqueci_senha')
        
        if request.method == 'POST':
            nova_senha = request.POST.get('nova_senha')
            confirmar_senha = request.POST.get('confirmar_senha')
            
            if nova_senha != confirmar_senha:
                messages.error(request, 'As senhas não coincidem!')
                return render(request, 'core/redefinir_senha_email.html', {'token': token})
            
            if len(nova_senha) < 6:
                messages.error(request, 'A senha deve ter no mínimo 6 caracteres!')
                return render(request, 'core/redefinir_senha_email.html', {'token': token})
            
            for user_check in User.objects.exclude(id=recuperacao.user.id):
                if user_check.check_password(nova_senha):
                    messages.error(request, 'Esta senha já está sendo usada por outro usuário. Por favor, escolha uma senha diferente.')
                    return render(request, 'core/redefinir_senha_email.html', {'token': token})
            
            user = recuperacao.user
            user.set_password(nova_senha)
            user.save()
            
            recuperacao.marcar_como_usado()
            
            messages.success(request, 'Senha redefinida com sucesso! Faça login com sua nova senha.')
            return redirect('login')
        
        return render(request, 'core/redefinir_senha_email.html', {'token': token})
    
    except RecuperacaoSenha.DoesNotExist:
        messages.error(request, 'Link inválido ou já utilizado!')
        return redirect('esqueci_senha')

@login_required
def perfis_pendentes_view(request):
    """View para administradores gerenciarem perfis pendentes"""
    if not request.user.is_staff:
        messages.error(request, 'Acesso negado! Apenas administradores podem acessar esta área.')
        return redirect('painel_principal')
    
    perfis_pendentes = PerfilUsuario.objects.filter(nivel_acesso='pendente').order_by('-data_cadastro')
    
    return render(request, 'core/perfis_pendentes.html', {
        'perfis_pendentes': perfis_pendentes
    })

@login_required
def atribuir_perfil_view(request, perfil_id):
    """View para atribuir perfil a um usuário"""
    if not request.user.is_staff:
        messages.error(request, 'Acesso negado!')
        return redirect('painel_principal')
    
    perfil = get_object_or_404(PerfilUsuario, id=perfil_id)
    
    if request.method == 'POST':
        nivel_acesso = request.POST.get('nivel_acesso')
        
        if nivel_acesso in ['admin', 'secretaria', 'professor', 'coordenador', 'aluno']:
            perfil.nivel_acesso = nivel_acesso
            perfil.save()
            
            Notificacao.objects.create(
                titulo='Perfil Atribuído',
                mensagem=f'Seu perfil foi atribuído como {perfil.get_nivel_acesso_display()}. Agora você pode acessar o sistema.',
                tipo='sucesso'
            ).destinatarios.add(perfil.user)
            
            messages.success(request, f'Perfil "{perfil.get_nivel_acesso_display()}" atribuído com sucesso para {perfil.user.get_full_name() or perfil.user.username}!')
        else:
            messages.error(request, 'Nível de acesso inválido!')
        
        return redirect('perfis_pendentes')
    
    return redirect('perfis_pendentes')

@login_required
def get_perfis_pendentes_count(request):
    """API endpoint para obter contagem de perfis pendentes"""
    if request.user.is_staff:
        count = PerfilUsuario.objects.filter(nivel_acesso='pendente').count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})

@login_required
def painel_principal(request):
    """View para o painel principal com menu lateral"""
    from datetime import date
    total_inscricoes = Inscricao.objects.count()
    total_aprovados = Inscricao.objects.filter(aprovado=True).count()
    total_reprovados = Inscricao.objects.filter(aprovado=False, nota_teste__isnull=False).count()
    aguardando_nota = Inscricao.objects.filter(nota_teste__isnull=True).count()
    
    anos_academicos = AnoAcademico.objects.all()
    ano_atual = AnoAcademico.objects.filter(ano_atual=True).first()
    
    notificacoes_nao_lidas = Notificacao.objects.filter(
        Q(global_notificacao=True) | Q(destinatarios=request.user),
        ativa=True
    ).exclude(lida_por=request.user).count()
    
    notificacoes_recentes = Notificacao.objects.filter(
        Q(global_notificacao=True) | Q(destinatarios=request.user),
        ativa=True
    ).distinct().order_by('-data_criacao')[:3]
    
    subscricao = Subscricao.objects.filter(estado__in=['ativo', 'teste']).first()
    
    context = {
        'total_inscricoes': total_inscricoes,
        'total_aprovados': total_aprovados,
        'total_reprovados': total_reprovados,
        'aguardando_nota': aguardando_nota,
        'anos_academicos': anos_academicos,
        'ano_atual': ano_atual,
        'notificacoes_nao_lidas': notificacoes_nao_lidas,
        'notificacoes_recentes': notificacoes_recentes,
        'subscricao': subscricao,
        'now': date.today()
    }
    return render(request, 'core/painel_principal.html', context)

@login_required
def trocar_ano(request):
    """View para seleção de ano acadêmico"""
    anos_academicos = AnoAcademico.objects.all().order_by('-data_inicio')
    ano_atual = AnoAcademico.objects.filter(ano_atual=True).first()
    
    context = {
        'anos_academicos': anos_academicos,
        'ano_atual': ano_atual
    }
    return render(request, 'core/trocar_ano.html', context)

@login_required
def painel_admin_view(request):
    """View para configurações gerais do sistema (Super Admin)"""
    if request.user.perfil.nivel_acesso not in ['admin', 'super_admin']:
        messages.error(request, 'Acesso negado. Apenas administradores podem acessar esta página.')
        return redirect('painel_principal')
    
    from .models import ConfiguracaoEscola
    config = ConfiguracaoEscola.objects.first()
    
    if request.method == 'POST':
        if not config:
            config = ConfiguracaoEscola.objects.create(nome_escola="SIGE - Sistema Escolar")
        
        # Só atualiza se o campo estiver presente no POST
        if 'nome_escola' in request.POST:
            config.nome_escola = request.POST.get('nome_escola')
        if 'email' in request.POST:
            config.email = request.POST.get('email')
        if 'telefone' in request.POST:
            config.telefone = request.POST.get('telefone')
        if 'endereco' in request.POST:
            config.endereco = request.POST.get('endereco')
        
        # Limpar campos de arquivo se for solicitado via POST (opcional, para resetar)
        if 'logo' in request.FILES:
            config.logo = request.FILES['logo']
        if 'favicon' in request.FILES:
            config.favicon = request.FILES['favicon']
            
        config.save()
        messages.success(request, 'Configurações atualizadas com sucesso!')
        
        # Garantir persistência antes do redirect
        config.refresh_from_db()
        return redirect('painel_admin')

    context = {
        'config': config,
        'active_tab': 'admin'
    }
    return render(request, 'core/painel_admin_view.html', context)

@login_required
def perfil_usuario(request):
    """View para exibir e editar perfil do usuário"""
    try:
        perfil = request.user.perfil
    except Exception:
        from .models import PerfilUsuario
        perfil = PerfilUsuario.objects.create(usuario=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_photo' and request.FILES.get('foto'):
            perfil.foto = request.FILES.get('foto')
            perfil.save()
            messages.success(request, 'Foto de perfil atualizada com sucesso!')
            
        elif action == 'update_profile':
            nome_completo = request.POST.get('nome', '').strip()
            if nome_completo:
                partes = nome_completo.split(' ')
                request.user.first_name = partes[0]
                request.user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''
            
            request.user.email = request.POST.get('email')
            request.user.save()
            perfil.telefone = request.POST.get('telefone')
            perfil.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            
        elif action == 'change_password':
            from django.contrib.auth import update_session_auth_hash
            from django.contrib.auth.forms import PasswordChangeForm
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha alterada com sucesso!')
            else:
                for error_list in form.errors.values():
                    for error in error_list:
                        messages.error(request, error)
        
        elif action == 'update_system_logo' and request.user.perfil.nivel_acesso == 'super_admin' and request.FILES.get('logo'):
            from .models import ConfiguracaoEscola
            config = ConfiguracaoEscola.objects.first()
            if not config:
                config = ConfiguracaoEscola.objects.create(nome_escola="SIGA")
            config.logo = request.FILES.get('logo')
            config.save()
            messages.success(request, 'Logotipo do sistema atualizado com sucesso!')
        
        return redirect('perfil_usuario')

    context = {
        'user': request.user,
    }
    return render(request, 'core/perfil_usuario.html', context)

@login_required
def quadro_avisos(request):
    """View para exibir quadro de avisos"""
    avisos = Notificacao.objects.filter(
        Q(global_notificacao=True) | Q(destinatarios=request.user),
        ativa=True
    ).distinct().order_by('-data_criacao')
    
    context = {
        'avisos': avisos
    }
    return render(request, 'core/quadro_avisos.html', context)

@login_required
def cursos_disciplinas(request):
    """View para gerenciar cursos e disciplinas com suporte AJAX"""
    from .models import Disciplina
    
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            acao = request.POST.get('acao')
            
            if acao == 'criar_curso':
                try:
                    codigo = request.POST.get('codigo')
                    nome = request.POST.get('nome')
                    vagas = int(request.POST.get('vagas', 30))
                    duracao = int(request.POST.get('duracao_meses', 12))
                    nota_minima = request.POST.get('nota_minima', '10.00')
                    
                    if Curso.objects.filter(codigo=codigo).exists():
                        return JsonResponse({'success': False, 'message': 'Código de curso já existe!'})
                    
                    curso = Curso.objects.create(
                        codigo=codigo,
                        nome=nome,
                        vagas=vagas,
                        duracao_meses=duracao,
                        nota_minima=nota_minima
                    )
                    return JsonResponse({
                        'success': True,
                        'message': f'Curso "{nome}" criado com sucesso!',
                        'curso': {
                            'id': curso.id,
                            'codigo': curso.codigo,
                            'nome': curso.nome,
                            'vagas': curso.vagas,
                            'nota_minima': str(curso.nota_minima),
                            'duracao': curso.get_duracao_meses_display()
                        }
                    })
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)})
            
            elif acao == 'editar_curso':
                try:
                    curso_id = int(request.POST.get('curso_id'))
                    curso = Curso.objects.get(id=curso_id)
                    curso.codigo = request.POST.get('codigo', curso.codigo)
                    curso.nome = request.POST.get('nome', curso.nome)
                    curso.vagas = int(request.POST.get('vagas', curso.vagas))
                    curso.duracao_meses = int(request.POST.get('duracao_meses', curso.duracao_meses))
                    curso.nota_minima = request.POST.get('nota_minima', curso.nota_minima)
                    curso.save()
                    return JsonResponse({'success': True, 'message': 'Curso atualizado com sucesso!'})
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)})
            
            elif acao == 'deletar_curso':
                try:
                    curso_id = int(request.POST.get('curso_id'))
                    curso = Curso.objects.get(id=curso_id)
                    nome = curso.nome
                    curso.delete()
                    return JsonResponse({'success': True, 'message': f'Curso "{nome}" deletado!'})
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)})
            
            elif acao == 'criar_disciplina':
                try:
                    from .models import Disciplina
                    curso_id = int(request.POST.get('curso_id'))
                    nome = request.POST.get('nome')
                    carga_horaria = int(request.POST.get('carga_horaria', 40))
                    
                    disciplina = Disciplina.objects.create(
                        curso_id=curso_id,
                        nome=nome,
                        carga_horaria=carga_horaria
                    )
                    return JsonResponse({'success': True, 'message': f'Disciplina "{nome}" criada com sucesso!'})
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)})
            
            elif acao == 'toggle_curso':
                try:
                    curso_id = int(request.POST.get('curso_id'))
                    curso = Curso.objects.get(id=curso_id)
                    curso.ativo = not curso.ativo
                    curso.save()
                    status_texto = "Ativado" if curso.ativo else "Desativado"
                    return JsonResponse({'success': True, 'message': f'Curso {status_texto}!', 'ativo': curso.ativo})
                except Exception as e:
                    return JsonResponse({'success': False, 'message': str(e)})
    
    cursos = Curso.objects.all()
    from .models import Disciplina
    disciplinas = Disciplina.objects.all()
    
    context = {
        'cursos': cursos,
        'disciplinas': disciplinas,
        'duracao_choices': Curso.DURACAO_CHOICES,
        'active': 'cursos'
    }
    return render(request, 'core/cursos_disciplinas.html', context)

@login_required
def grelha_curricular(request):
    """View para exibir grelha curricular estruturada por anos e semestres"""
    cursos = Curso.objects.filter(ativo=True)
    curso_id = request.GET.get('curso')
    disciplinas = []
    anos_range = []
    semestres_range = [1, 2]
    
    if curso_id:
        curso = get_object_or_404(Curso, id=curso_id)
        disciplinas = curso.disciplinas.all()
        # Calcula anos baseado na duração do curso (assume 12 meses por ano)
        anos = (curso.duracao_meses // 12) if curso.duracao_meses >= 12 else 1
        anos_range = range(1, anos + 1)

    return render(request, 'core/grelha_curricular.html', {
        'cursos': cursos,
        'disciplinas': disciplinas,
        'anos_range': anos_range,
        'semestres_range': semestres_range,
        'active': 'grelha'
    })

@login_required
def cronograma_academico(request):
    """View para exibir cronograma acadêmico"""
    context = {'active': 'cronograma'}
    return render(request, 'core/cronograma_academico.html', context)

@login_required
def periodo_letivo(request):
    """View para gerenciar período letivo"""
    context = {'active': 'periodo'}
    return render(request, 'core/periodo_letivo.html', context)

@login_required
def horarios(request):
    """View para gerenciar horários"""
    context = {'active': 'horarios'}
    return render(request, 'core/horarios.html', context)

@login_required
def titulos_academicos(request):
    """View para gerenciar títulos acadêmicos"""
    context = {'active': 'titulos'}
    return render(request, 'core/titulos_academicos.html', context)

@login_required
def modelo_avaliacao(request):
    """View para gerenciar modelo de avaliação"""
    context = {'active': 'modelo'}
    return render(request, 'core/modelo_avaliacao.html', context)

@login_required
def syllabus(request):
    """View para gerenciar syllabus acadêmico"""
    context = {'active': 'syllabus'}
    return render(request, 'core/syllabus.html', context)

@login_required
def admissao(request):
    """View para admissão de estudantes"""
    context = {}
    return render(request, 'core/admissao_view.html', context)

@login_required
def selecionar_tipo_matricula(request):
    """View para selecionar tipo de matrícula"""
    return render(request, 'core/selecionar_tipo_matricula.html')

@login_required
def matricula(request):
    """View para matrícula de estudantes"""
    # Get all enrollments with filtering
    inscricoes = Inscricao.objects.all().select_related('curso')
    
    # Filter options
    status_filter = request.GET.get('status', 'todos')
    curso_filter = request.GET.get('curso', '')
    
    if status_filter == 'pendente':
        inscricoes = inscricoes.filter(aprovado=False)
    elif status_filter == 'aprovado':
        inscricoes = inscricoes.filter(aprovado=True)
    
    if curso_filter:
        inscricoes = inscricoes.filter(curso_id=curso_filter)
    
    # Handle approval/rejection
    if request.method == 'POST':
        action = request.POST.get('action')
        inscricao_id = request.POST.get('inscricao_id')
        
        try:
            inscricao = Inscricao.objects.get(id=inscricao_id)
            
            if action == 'aprovar':
                inscricao.aprovado = True
                inscricao.data_resultado = timezone.now()
                inscricao.save()
                messages.success(request, f'Matrícula de {inscricao.nome_completo} aprovada com sucesso!')
            elif action == 'rejeitar':
                inscricao.aprovado = False
                inscricao.data_resultado = None
                inscricao.save()
                messages.success(request, f'Matrícula de {inscricao.nome_completo} rejeitada!')
        except Inscricao.DoesNotExist:
            messages.error(request, 'Matrícula não encontrada!')
        
        return redirect('matricula')
    
    cursos = Curso.objects.all()
    
    context = {
        'inscricoes': inscricoes,
        'cursos': cursos,
        'status_filter': status_filter,
        'curso_filter': curso_filter,
        'total': Inscricao.objects.count(),
        'aprovadas': Inscricao.objects.filter(aprovado=True).count(),
        'pendentes': Inscricao.objects.filter(aprovado=False).count(),
    }
    return render(request, 'core/matricula_view.html', context)

@login_required
def termo_renovacao(request):
    """View para termo de renovação de matrícula"""
    inscricoes_aprovadas = Inscricao.objects.filter(aprovado=True).select_related('curso')
    
    if request.method == 'POST':
        inscricao_id = request.POST.get('inscricao_id')
        try:
            inscricao = Inscricao.objects.get(id=inscricao_id)
            messages.success(request, f'Termo de renovação processado para {inscricao.nome_completo}!')
            return redirect('termo_renovacao')
        except Inscricao.DoesNotExist:
            messages.error(request, 'Matrícula não encontrada!')
    
    context = {'inscricoes': inscricoes_aprovadas}
    return render(request, 'core/termo_renovacao_view.html', context)

@login_required
def receber_documento_matricula(request):
    """View para receber documento de matrícula"""
    inscricoes_aprovadas = Inscricao.objects.filter(aprovado=True).select_related('curso')
    
    if request.method == 'POST':
        inscricao_id = request.POST.get('inscricao_id')
        try:
            inscricao = Inscricao.objects.get(id=inscricao_id)
            messages.success(request, f'Documento de matrícula entregue para {inscricao.nome_completo}!')
            return redirect('receber_documento_matricula')
        except Inscricao.DoesNotExist:
            messages.error(request, 'Matrícula não encontrada!')
    
    context = {'inscricoes': inscricoes_aprovadas}
    return render(request, 'core/receber_documento_matricula_view.html', context)

@login_required
def lista_estudantes(request):
    """View para lista de estudantes"""
    context = {}
    return render(request, 'core/lista_estudantes_view.html', context)

@login_required
def assiduidade(request):
    """View para controle de assiduidade"""
    context = {}
    return render(request, 'core/assiduidade_view.html', context)

@login_required
def certificados(request):
    """View para gerenciar certificados"""
    context = {}
    return render(request, 'core/certificados_view.html', context)

@login_required
def historico(request):
    """View para histórico escolar"""
    context = {}
    return render(request, 'core/historico_view.html', context)

@login_required
def materiais(request):
    """View para materiais de apoio"""
    context = {}
    return render(request, 'core/materiais_view.html', context)

@login_required
def solicitacao_docs(request):
    """View para solicitação de documentos"""
    context = {}
    return render(request, 'core/solicitacao_docs_view.html', context)

@login_required
def atividades_extracurriculares(request):
    """View para atividades extracurriculares"""
    context = {}
    return render(request, 'core/atividades_extracurriculares_view.html', context)

@login_required
def gestao_docentes(request):
    """View para página principal de gestão de docentes"""
    return render(request, 'core/gestao_docentes.html')

@login_required
def cadastro_professores(request):
    """View para cadastro e gestão de professores"""
    context = {}
    return render(request, 'core/cadastro_professores_view.html', context)

@login_required
def atribuicao_turmas(request):
    """View para atribuição de turmas e disciplinas"""
    context = {}
    return render(request, 'core/atribuicao_turmas_view.html', context)

@login_required
def assiduidade_docentes(request):
    """View para assiduidade de docentes"""
    context = {}
    return render(request, 'core/assiduidade_docentes_view.html', context)

@login_required
def gestao_licencas(request):
    """View para gestão de licenças"""
    context = {}
    return render(request, 'core/gestao_licencas_view.html', context)

@login_required
def avaliacao_desempenho(request):
    """View para avaliação de desempenho"""
    context = {}
    return render(request, 'core/avaliacao_desempenho_view.html', context)

@login_required
def gestao_administrativa(request):
    """View para página principal de gestão administrativa"""
    return render(request, 'core/gestao_administrativa.html')

@login_required
def painel_admin(request):
    """View para painel administrativo"""
    context = {}
    return render(request, 'core/painel_admin_view.html', context)

@login_required
def recursos_humanos(request):
    """View para recursos humanos"""
    context = {}
    return render(request, 'core/recursos_humanos_view.html', context)

@login_required
def departamentos(request):
    """View para departamentos"""
    context = {}
    return render(request, 'core/departamentos_view.html', context)

@login_required
def recrutamento(request):
    """View para recrutamento"""
    context = {}
    return render(request, 'core/recrutamento_view.html', context)

@login_required
def gestao_tarefas(request):
    """View para gestão de tarefas"""
    context = {}
    return render(request, 'core/gestao_tarefas_view.html', context)

@login_required
def gestao_eventos(request):
    """View para gestão de eventos"""
    context = {}
    return render(request, 'core/gestao_eventos_view.html', context)

@login_required
def gestao_financeira(request):
    """View para página principal de gestão financeira"""
    return render(request, 'core/gestao_financeira.html')

@login_required
def faturas_pagamentos(request):
    """View para faturas e pagamentos"""
    context = {}
    return render(request, 'core/faturas_pagamentos_view.html', context)

@login_required
def relatorios_financeiros(request):
    """View para relatórios financeiros"""
    context = {}
    return render(request, 'core/relatorios_financeiros_view.html', context)

@login_required
def gestao_despesas(request):
    """View para gestão de despesas"""
    context = {}
    return render(request, 'core/gestao_despesas_view.html', context)

@login_required
def bolsas_beneficios(request):
    """View para bolsas e benefícios"""
    context = {}
    return render(request, 'core/bolsas_beneficios_view.html', context)

@login_required
def pagamento_online(request):
    """View para pagamento online"""
    context = {}
    return render(request, 'core/pagamento_online_view.html', context)

@login_required
def gestao_recursos(request):
    """View para página principal de gestão de recursos"""
    return render(request, 'core/gestao_recursos.html')

@login_required
def biblioteca(request):
    """View para biblioteca"""
    context = {}
    return render(request, 'core/biblioteca_view.html', context)

@login_required
def laboratorios(request):
    """View para laboratórios"""
    context = {}
    return render(request, 'core/laboratorios_view.html', context)

@login_required
def transporte(request):
    """View para transporte escolar"""
    context = {}
    return render(request, 'core/transporte_view.html', context)

@login_required
def dormitorios(request):
    """View para dormitórios"""
    context = {}
    return render(request, 'core/dormitorios_view.html', context)

@login_required
def infraestrutura(request):
    """View para infraestrutura"""
    context = {}
    return render(request, 'core/infraestrutura_view.html', context)

@login_required
def gestao_documentos(request):
    """View principal de gestão de documentos"""
    documentos = Documento.objects.all().order_by('-data_criacao')
    return render(request, 'core/gestao_documentos.html', {'documentos': documentos})

@login_required
def documento_criar(request):
    """Criar novo documento template"""
    if request.method == 'POST':
        documento = Documento(
            titulo=request.POST.get('titulo'),
            secao=request.POST.get('secao'),
            conteudo=request.POST.get('conteudo'),
            descricao=request.POST.get('descricao', ''),
            ativo='ativo' in request.POST,
            criado_por=request.user
        )
        documento.save()
        messages.success(request, f'Documento "{documento.titulo}" criado com sucesso!')
        return redirect('gestao_documentos')
    
    return render(request, 'core/documento_form.html', {
        'secoes': Documento.SECAO_CHOICES,
        'variaveis': Documento.obter_variaveis_disponiveis(None)
    })

@login_required
def documento_editar(request, documento_id):
    """Editar documento existente"""
    documento = get_object_or_404(Documento, id=documento_id)
    
    if request.method == 'POST':
        documento.titulo = request.POST.get('titulo')
        documento.secao = request.POST.get('secao')
        documento.conteudo = request.POST.get('conteudo')
        documento.descricao = request.POST.get('descricao', '')
        documento.ativo = 'ativo' in request.POST
        documento.save()
        messages.success(request, f'Documento "{documento.titulo}" atualizado com sucesso!')
        return redirect('gestao_documentos')
    
    return render(request, 'core/documento_form.html', {
        'documento': documento,
        'secoes': Documento.SECAO_CHOICES,
        'variaveis': documento.obter_variaveis_disponiveis()
    })

@login_required
def documento_deletar(request, documento_id):
    """Deletar documento"""
    documento = get_object_or_404(Documento, id=documento_id)
    titulo = documento.titulo
    documento.delete()
    messages.success(request, f'Documento "{titulo}" deletado com sucesso!')
    return redirect('gestao_documentos')

@login_required
def documento_visualizar(request, documento_id):
    """Visualizar/pré-visualizar documento"""
    documento = get_object_or_404(Documento, id=documento_id)
    
    # Dados de exemplo para preview
    dados_exemplo = {
        'nome': 'João Silva Santos',
        'bilhete_identidade': '1234567890123',
        'email': 'joao@example.com',
        'telefone': '244999999999',
        'data_nascimento': '1990-05-15',
        'curso': 'Engenharia de Software',
        'numero_inscricao': 'INS-000001',
        'data_inscricao': date.today().strftime('%d/%m/%Y'),
        'data_hoje': date.today().strftime('%d/%m/%Y'),
        'nome_escola': 'Instituto Superior Técnico',
        'endereco': 'Rua Principal, 123',
        'sexo': 'Masculino',
        'estado_civil': 'Solteiro',
        'nacionalidade': 'Angolano',
        'local_nascimento': 'Luanda',
    }
    
    conteudo_renderizado = documento.renderizar(dados_exemplo)
    
    return render(request, 'core/documento_visualizar.html', {
        'documento': documento,
        'conteudo': conteudo_renderizado,
        'dados_exemplo': dados_exemplo
    })

def gerar_pdf_documento(request, documento_id, inscricao_id=None):
    """Gerar PDF de um documento com dados reais"""
    documento = get_object_or_404(Documento, id=documento_id)
    
    if inscricao_id:
        inscricao = get_object_or_404(Inscricao, id=inscricao_id)
        config = ConfiguracaoEscola.objects.first()
        
        # Preparar dados da inscrição para o documento
        dados = {
            'nome': inscricao.nome_completo,
            'bilhete_identidade': inscricao.bilhete_identidade,
            'email': inscricao.email,
            'telefone': inscricao.telefone,
            'data_nascimento': inscricao.data_nascimento.strftime('%d/%m/%Y'),
            'curso': inscricao.curso.nome,
            'numero_inscricao': inscricao.numero_inscricao,
            'data_inscricao': inscricao.data_inscricao.strftime('%d/%m/%Y'),
            'data_hoje': date.today().strftime('%d/%m/%Y'),
            'nome_escola': config.nome_escola if config else 'SIGE',
            'endereco': inscricao.endereco,
            'sexo': dict(Inscricao._meta.get_field('sexo').choices).get(inscricao.sexo, ''),
            'estado_civil': dict(Inscricao._meta.get_field('estado_civil').choices).get(inscricao.estado_civil, ''),
            'nacionalidade': inscricao.nacionalidade,
            'local_nascimento': inscricao.local_nascimento,
        }
    else:
        # Dados de exemplo se não houver inscrição
        dados = {
            'nome': 'Exemplo de Nome',
            'bilhete_identidade': '0000000000000',
            'email': 'exemplo@example.com',
            'telefone': '244999999999',
            'data_nascimento': date.today().strftime('%d/%m/%Y'),
            'curso': 'Curso de Exemplo',
            'numero_inscricao': 'INS-000000',
            'data_inscricao': date.today().strftime('%d/%m/%Y'),
            'data_hoje': date.today().strftime('%d/%m/%Y'),
            'nome_escola': 'SIGE',
            'endereco': 'Endereço de Exemplo',
            'sexo': 'M',
            'estado_civil': 'S',
            'nacionalidade': 'Angolana',
            'local_nascimento': 'Luanda',
        }
    
    # Gerar PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        textColor='#000000',
        spaceAfter=8,
        alignment=TA_LEFT
    )
    
    conteudo_renderizado = documento.renderizar(dados)
    
    for linha in conteudo_renderizado.split('\n'):
        if linha.strip():
            story.append(Paragraph(linha, normal_style))
    
    story.append(Spacer(1, 1*cm))
    
    doc.build(story)
    
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{documento.titulo.replace(" ", "_")}.pdf"'
    
    return response

# ============= GESTÃO DE CURSOS =============

@login_required
def listar_cursos(request):
    """Lista todos os cursos cadastrados"""
    perfil = getattr(request.user, 'perfil', None)
    if not request.user.is_staff and not (perfil and perfil.nivel_acesso in ['admin', 'super_admin']):
        messages.error(request, 'Acesso negado.')
        return redirect('painel_principal')
    cursos = Curso.objects.all()
    return render(request, 'core/cursos/listar_cursos.html', {
        'cursos': cursos,
        'total_cursos': cursos.count(),
    })

@login_required
def criar_curso(request):
    """Cria um novo curso"""
    perfil = getattr(request.user, 'perfil', None)
    if not request.user.is_staff and not (perfil and perfil.nivel_acesso in ['admin', 'super_admin']):
        messages.error(request, 'Acesso negado.')
        return redirect('listar_cursos')
    if request.method == 'POST':
        try:
            codigo = request.POST.get('codigo')
            nome = request.POST.get('nome')
            descricao = request.POST.get('descricao', '')
            vagas = int(request.POST.get('vagas', 0))
            duracao_meses = int(request.POST.get('duracao_meses', 12))
            nota_minima = request.POST.get('nota_minima', '10.00')
            grau = request.POST.get('grau')
            regime = request.POST.get('regime')
            modalidade = request.POST.get('modalidade')
            
            if Curso.objects.filter(codigo=codigo).exists():
                messages.error(request, 'Curso com este código já existe!')
                return render(request, 'core/cursos/curso_form.html', {
                    'duracao_choices': Curso.DURACAO_CHOICES,
                    'grau_choices': Curso.GRAU_CHOICES,
                    'regime_choices': Curso.REGIME_CHOICES,
                    'modalidade_choices': Curso.MODALIDADE_CHOICES,
                })
            
            curso = Curso.objects.create(
                codigo=codigo,
                nome=nome,
                descricao=descricao,
                vagas=vagas,
                duracao_meses=duracao_meses,
                nota_minima=nota_minima,
                grau=grau,
                regime=regime,
                modalidade=modalidade,
                ativo=True
            )
            
            messages.success(request, f'Curso "{curso.nome}" cadastrado com sucesso!')
            return redirect('listar_cursos')
        except Exception as e:
            messages.error(request, f'Erro ao criar curso: {str(e)}')
    
    return render(request, 'core/cursos/curso_form.html', {
        'duracao_choices': Curso.DURACAO_CHOICES,
        'grau_choices': Curso.GRAU_CHOICES,
        'regime_choices': Curso.REGIME_CHOICES,
        'modalidade_choices': Curso.MODALIDADE_CHOICES,
    })

@login_required
def detalhe_curso(request, curso_id):
    """Exibe detalhes de um curso"""
    curso = get_object_or_404(Curso, id=curso_id)
    inscricoes = curso.inscricoes.all()
    
    return render(request, 'core/cursos/detalhe_curso.html', {
        'curso': curso,
        'inscricoes': inscricoes,
        'total_inscricoes': inscricoes.count(),
        'total_aprovados': inscricoes.filter(aprovado=True).count(),
        'vagas_disponiveis': curso.vagas_disponiveis(),
    })

@login_required
def editar_curso(request, curso_id):
    """Edita um curso existente"""
    perfil = getattr(request.user, 'perfil', None)
    if not request.user.is_staff and not (perfil and perfil.nivel_acesso in ['admin', 'super_admin']):
        messages.error(request, 'Acesso negado.')
        return redirect('listar_cursos')
    curso = get_object_or_404(Curso, id=curso_id)
    
    if request.method == 'POST':
        try:
            curso.codigo = request.POST.get('codigo', curso.codigo)
            curso.nome = request.POST.get('nome', curso.nome)
            curso.descricao = request.POST.get('descricao', curso.descricao)
            curso.vagas = int(request.POST.get('vagas', curso.vagas))
            curso.duracao_meses = int(request.POST.get('duracao_meses', curso.duracao_meses))
            curso.nota_minima = request.POST.get('nota_minima', curso.nota_minima)
            curso.grau = request.POST.get('grau', curso.grau)
            curso.regime = request.POST.get('regime', curso.regime)
            curso.modalidade = request.POST.get('modalidade', curso.modalidade)
            curso.ativo = request.POST.get('ativo') == 'on'
            
            curso.save()
            messages.success(request, f'Curso "{curso.nome}" atualizado com sucesso!')
            return redirect('detalhe_curso', curso_id=curso.id)
        except Exception as e:
            messages.error(request, f'Erro ao editar curso: {str(e)}')
    
    return render(request, 'core/cursos/curso_form.html', {
        'curso': curso,
        'duracao_choices': Curso.DURACAO_CHOICES,
        'grau_choices': Curso.GRAU_CHOICES,
        'regime_choices': Curso.REGIME_CHOICES,
        'modalidade_choices': Curso.MODALIDADE_CHOICES,
        'edicao': True,
    })

@login_required
def deletar_curso(request, curso_id):
    """Deleta um curso"""
    perfil = getattr(request.user, 'perfil', None)
    if not request.user.is_staff and not (perfil and perfil.nivel_acesso in ['admin', 'super_admin']):
        messages.error(request, 'Acesso negado.')
        return redirect('listar_cursos')
    curso = get_object_or_404(Curso, id=curso_id)
    
    if request.method == 'POST':
        nome = curso.nome
        curso.delete()
        messages.success(request, f'Curso "{nome}" deletado com sucesso!')
        return redirect('listar_cursos')
    
    return render(request, 'core/cursos/confirmar_deletar.html', {
        'curso': curso,
    })

# ============================
# GESTÃO DE UTILIZADORES
# ============================

@login_required
def listar_utilizadores(request):
    """Lista todos os utilizadores do sistema"""
    # Verificar se é admin ou super_admin
    perfil = getattr(request.user, 'perfil', None)
    if not request.user.is_staff and not (perfil and perfil.nivel_acesso in ['admin', 'super_admin']):
        messages.error(request, 'Acesso negado. Apenas administradores podem acessar esta página.')
        return redirect('painel_principal')
    
    utilizadores = User.objects.all().prefetch_related('perfil').order_by('-date_joined')
    
    # Filtro por nível de acesso
    nivel_filtro = request.GET.get('nivel', '')
    if nivel_filtro:
        utilizadores = utilizadores.filter(perfil__nivel_acesso=nivel_filtro)
    
    # Filtro por status
    ativo_filtro = request.GET.get('ativo', '')
    if ativo_filtro == 'sim':
        utilizadores = utilizadores.filter(is_active=True).exclude(perfil__nivel_acesso='pendente')
    elif ativo_filtro == 'nao':
        utilizadores = utilizadores.filter(is_active=False)
    elif ativo_filtro == 'pendente':
        utilizadores = utilizadores.filter(perfil__nivel_acesso='pendente')
    
    contexto = {
        'utilizadores': utilizadores,
        'niveis_acesso': PerfilUsuario.NIVEL_ACESSO_CHOICES,
        'nivel_filtro': nivel_filtro,
        'ativo_filtro': ativo_filtro,
    }
    return render(request, 'core/utilizadores/listar.html', contexto)

@login_required
def criar_utilizador(request):
    """Cria novo utilizador via AJAX/Modal"""
    perfil_req = getattr(request.user, 'perfil', None)
    if not request.user.is_superuser and not (perfil_req and perfil_req.nivel_acesso == 'super_admin'):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Acesso negado.'})
        messages.error(request, 'Acesso negado. Apenas Super Administradores podem criar utilizadores.')
        return redirect('listar_utilizadores')
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            password = request.POST.get('password')
            nivel_acesso = request.POST.get('nivel_acesso', 'pendente')
            telefone = request.POST.get('telefone', '')
            
            # Validar
            if User.objects.filter(username=username).exists():
                return JsonResponse({'success': False, 'error': 'Utilizador já existe!'})
            
            # Criar utilizador
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password,
                is_active=True,
                is_staff=(nivel_acesso in ['admin', 'super_admin']),
                is_superuser=(nivel_acesso == 'super_admin')
            )
            
            # Criar/atualizar perfil
            perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
            perfil.nivel_acesso = nivel_acesso
            perfil.telefone = telefone
            perfil.ativo = True
            perfil.save()

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                messages.success(request, f'Utilizador "{username}" criado com sucesso!')
                return JsonResponse({'success': True})
            
            messages.success(request, f'Utilizador "{username}" criado com sucesso!')
            return redirect('listar_utilizadores')
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': str(e)})
            messages.error(request, f'Erro ao criar utilizador: {str(e)}')
    
    return redirect('listar_utilizadores')

@login_required
def editar_utilizador(request, user_id):
    """Edita um utilizador existente via AJAX"""
    perfil_req = getattr(request.user, 'perfil', None)
    if not request.user.is_superuser and not (perfil_req and perfil_req.nivel_acesso == 'super_admin'):
        return JsonResponse({'success': False, 'error': 'Acesso negado.'})
    
    user = get_object_or_404(User, id=user_id)
    perfil = user.perfil
    
    if request.method == 'POST':
        try:
            user.email = request.POST.get('email', user.email)
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.is_active = request.POST.get('is_active') == 'on'
            
            nivel_acesso = request.POST.get('nivel_acesso', perfil.nivel_acesso)
            user.is_staff = (nivel_acesso in ['admin', 'super_admin', 'secretario_academico', 'daac', 'financeiro', 'rh', 'bibliotecario'])
            user.is_superuser = (nivel_acesso == 'super_admin')
            
            user.save()
            
            perfil.nivel_acesso = nivel_acesso
            perfil.telefone = request.POST.get('telefone', perfil.telefone)
            perfil.ativo = user.is_active
            perfil.save()
            
            nova_password = request.POST.get('password', '')
            if nova_password:
                user.set_password(nova_password)
                user.save()
            
            messages.success(request, f'Utilizador "{user.username}" atualizado com sucesso!')
            return JsonResponse({'success': True, 'message': f'Utilizador "{user.username}" atualizado!'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Se for GET, retorna os dados para o modal
    return JsonResponse({
        'success': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'nivel_acesso': perfil.nivel_acesso,
            'telefone': perfil.telefone,
            'is_active': user.is_active
        }
    })

@login_required
def deletar_utilizador(request, user_id):
    """Deleta um utilizador"""
    perfil_req = getattr(request.user, 'perfil', None)
    if not request.user.is_superuser and not (perfil_req and perfil_req.nivel_acesso == 'super_admin'):
        messages.error(request, 'Acesso negado. Apenas Super Administradores podem deletar utilizadores.')
        return redirect('listar_utilizadores')
    
    user = get_object_or_404(User, id=user_id)
    
    # Não permitir deletar a si mesmo
    if user.id == request.user.id:
        messages.error(request, 'Não pode deletar sua própria conta!')
        return redirect('listar_utilizadores')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Utilizador "{username}" deletado com sucesso!')
        return redirect('listar_utilizadores')
    
    return render(request, 'core/utilizadores/confirmar_deletar.html', {
        'user': user,
    })

@login_required
def ativar_utilizador(request, user_id):
    """Ativa/Desativa um utilizador"""
    perfil_req = getattr(request.user, 'perfil', None)
    if not request.user.is_superuser and not (perfil_req and perfil_req.nivel_acesso == 'super_admin'):
        return JsonResponse({'success': False, 'error': 'Acesso negado'})
    
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    
    if hasattr(user, 'perfil'):
        user.perfil.ativo = user.is_active
        user.perfil.save()
    
    status = 'ativado' if user.is_active else 'desativado'
    messages.success(request, f'Utilizador {status} com sucesso!')
    return redirect('listar_utilizadores')

