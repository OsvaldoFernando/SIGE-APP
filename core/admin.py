from django.contrib import admin
from .models import (
    ConfiguracaoEscola, Curso, Disciplina, Escola, Inscricao, Professor, 
    Turma, Aluno, Pai, AnoAcademico, PerfilUsuario, Notificacao, Subscricao, 
    PagamentoSubscricao, RecuperacaoSenha, Documento, PrerequisitoDisciplina,
    HistoricoAcademico, NotaDisciplina, PeriodoLectivo, ConfiguracaoAcademica, Sala
)

@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'capacidade', 'tipo', 'ativa']
    list_filter = ['tipo', 'ativa']
    search_fields = ['nome']

@admin.register(ConfiguracaoAcademica)
class ConfiguracaoAcademicaAdmin(admin.ModelAdmin):
    list_display = ['percentagem_prova_continua', 'percentagem_exame_final', 'minimo_presenca_obrigatoria']
    
    def has_add_permission(self, request):
        if ConfiguracaoAcademica.objects.exists():
            return False
        return super().has_add_permission(request)

@admin.register(PeriodoLectivo)
class PeriodoLectivoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'ano_lectivo', 'data_inicio', 'data_fim', 'estado']
    list_filter = ['estado', 'ano_lectivo']
    search_fields = ['nome']
    ordering = ['ano_lectivo', 'data_inicio']

@admin.register(AnoAcademico)
class AnoAcademicoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descricao', 'estado', 'ano_atual', 'data_criacao']
    list_filter = ['estado', 'ano_atual', 'data_criacao']
    ordering = ['-data_inicio']
    
    actions = ['marcar_como_ativo']
    
    def marcar_como_ativo(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "Selecione apenas um ano para ativar.", level='error')
            return
            
        ano = queryset.first()
        try:
            ano.estado = 'ATIVO'
            ano.save()
            self.message_user(request, f"Ano acadêmico {ano} marcado como ativo!")
        except ValueError as e:
            self.message_user(request, str(e), level='error')

@admin.register(ConfiguracaoEscola)
class ConfiguracaoEscolaAdmin(admin.ModelAdmin):
    list_display = ['nome_escola', 'telefone', 'email']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome_escola', 'endereco', 'telefone', 'email', 'logo')
        }),
        ('Templates de Documentos', {
            'fields': ('template_confirmacao_inscricao',)
        }),
    )
    
    def has_add_permission(self, request):
        if ConfiguracaoEscola.objects.exists():
            return False
        return super().has_add_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        return False

class PrerequisitoDisciplinaInline(admin.TabularInline):
    model = PrerequisitoDisciplina
    extra = 1
    fields = ['disciplina_prerequisito', 'nota_minima_prerequisito', 'obrigatorio', 'ordem']
    ordering = ['ordem']

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'duracao_meses', 'vagas', 'vagas_disponiveis', 'requer_prerequisitos', 'ativo']
    list_filter = ['ativo', 'requer_prerequisitos', 'duracao_meses', 'data_criacao']
    search_fields = ['nome', 'codigo', 'descricao']
    readonly_fields = ['data_criacao', 'data_atualizacao']
    inlines = [PrerequisitoDisciplinaInline]
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('codigo', 'nome', 'descricao')
        }),
        ('Configuração do Curso', {
            'fields': ('duracao_meses', 'vagas', 'nota_minima')
        }),
        ('Pré-requisitos', {
            'fields': ('requer_prerequisitos',),
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Auditoria', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'curso', 'carga_horaria']
    list_filter = ['curso']
    search_fields = ['nome', 'codigo', 'curso__nome']
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('curso', 'nome', 'codigo')
        }),
        ('Detalhes', {
            'fields': ('carga_horaria', 'descricao')
        }),
    )

class NotaDisciplinaInline(admin.TabularInline):
    model = NotaDisciplina
    extra = 1
    fields = ['disciplina', 'nota', 'ano_conclusao', 'observacoes']
    ordering = ['-ano_conclusao', 'disciplina']

@admin.register(HistoricoAcademico)
class HistoricoAcademicoAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'data_criacao', 'data_atualizacao']
    list_filter = ['data_criacao', 'data_atualizacao']
    readonly_fields = ['inscricao', 'data_criacao', 'data_atualizacao']
    inlines = [NotaDisciplinaInline]
    fieldsets = (
        ('Informações', {
            'fields': ('inscricao', 'data_criacao', 'data_atualizacao')
        }),
    )
    
    def has_add_permission(self, request):
        return False

@admin.register(PrerequisitoDisciplina)
class PrerequisitoDisciplinaAdmin(admin.ModelAdmin):
    list_display = ['curso', 'disciplina_prerequisito', 'nota_minima_prerequisito', 'obrigatorio', 'ordem']
    list_filter = ['curso', 'obrigatorio']
    search_fields = ['curso__nome', 'disciplina_prerequisito__nome']
    ordering = ['curso', 'ordem']

@admin.register(NotaDisciplina)
class NotaDisciplinaAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'nota', 'ano_conclusao']
    list_filter = ['ano_conclusao', 'disciplina']
    search_fields = ['historico__inscricao__nome_completo', 'disciplina__nome']
    readonly_fields = ['historico']
    ordering = ['-ano_conclusao', 'disciplina']

@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'municipio', 'provincia', 'tipo', 'data_cadastro']
    list_filter = ['tipo', 'provincia']
    search_fields = ['nome', 'municipio', 'provincia']
    readonly_fields = ['data_cadastro']

@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ['numero_inscricao', 'get_nome_completo', 'curso', 'nota_teste', 'aprovado', 'data_inscricao']
    
    def get_nome_completo(self, obj):
        return obj.nome_completo
    get_nome_completo.short_description = 'Nome Completo'
    
    list_filter = ['curso', 'aprovado', 'data_inscricao']
    search_fields = ['numero_inscricao', 'primeiro_nome', 'apelido', 'bilhete_identidade', 'email']
    readonly_fields = ['numero_inscricao', 'data_inscricao', 'data_resultado']
    fieldsets = (
        ('Informações da Inscrição', {
            'fields': ('numero_inscricao', 'curso', 'data_inscricao')
        }),
        ('Dados Pessoais', {
            'fields': ('primeiro_nome', 'nomes_meio', 'apelido', 'data_nascimento', 'sexo', 'bilhete_identidade')
        }),
        ('Contato', {
            'fields': ('telefone', 'email', 'endereco')
        }),
        ('Avaliação', {
            'fields': ('nota_teste', 'aprovado', 'data_resultado')
        }),
    )

@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'bilhete_identidade', 'especialidade', 'telefone', 'email']
    search_fields = ['nome_completo', 'bilhete_identidade', 'especialidade']
    list_filter = ['sexo', 'data_contratacao']

@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'curso', 'ano_letivo', 'professor_titular']
    list_filter = ['curso', 'ano_letivo']
    search_fields = ['nome', 'curso__nome']

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ['numero_estudante', 'nome_completo', 'turma', 'telefone', 'email']
    list_filter = ['turma', 'sexo', 'data_matricula']
    search_fields = ['numero_estudante', 'nome_completo', 'bilhete_identidade']
    readonly_fields = ['numero_estudante', 'data_matricula']

@admin.register(Pai)
class PaiAdmin(admin.ModelAdmin):
    list_display = ['nome_completo', 'telefone', 'email']
    search_fields = ['nome_completo', 'bilhete_identidade']

@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ['user', 'nivel_acesso', 'telefone', 'ativo', 'data_cadastro']
    list_filter = ['nivel_acesso', 'ativo', 'data_cadastro']
    search_fields = ['user__username', 'telefone']
    readonly_fields = ['data_cadastro']

@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'tipo', 'global_notificacao', 'ativa', 'data_criacao']
    list_filter = ['tipo', 'global_notificacao', 'ativa', 'data_criacao']
    search_fields = ['titulo', 'mensagem']
    filter_horizontal = ['destinatarios', 'lida_por']
    readonly_fields = ['data_criacao']

@admin.register(Subscricao)
class SubscricaoAdmin(admin.ModelAdmin):
    list_display = ['nome_escola', 'plano', 'estado', 'data_inicio', 'data_expiracao', 'esta_ativo']
    list_filter = ['plano', 'estado', 'data_inicio', 'data_expiracao']
    search_fields = ['nome_escola']
    readonly_fields = ['data_criacao', 'esta_ativo']

@admin.register(PagamentoSubscricao)
class PagamentoSubscricaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'subscricao', 'plano_escolhido', 'valor', 'data_pagamento', 'status']
    list_filter = ['status', 'plano_escolhido']
    search_fields = ['subscricao__nome_escola']
    readonly_fields = ['data_submissao']

@admin.register(RecuperacaoSenha)
class RecuperacaoSenhaAdmin(admin.ModelAdmin):
    list_display = ['user', 'tipo', 'usado', 'esta_expirado', 'data_criacao']
    list_filter = ['tipo', 'usado']
    readonly_fields = ['data_criacao']

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'secao', 'ativo', 'data_criacao']
    list_filter = ['secao', 'ativo']
    readonly_fields = ['data_criacao', 'data_atualizacao']
