from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class AnoAcademico(models.Model):
    ESTADO_CHOICES = [
        ('PLANEADO', 'Planeado'),
        ('ATIVO', 'Ativo'),
        ('ENCERRADO', 'Encerrado'),
    ]
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código (ex: 2024/2025)", default="0000/0000")
    descricao = models.CharField(max_length=255, verbose_name="Descrição", default="Ano Académico")
    data_inicio = models.DateField(verbose_name="Data de Início", default=timezone.now)
    data_fim = models.DateField(verbose_name="Data de Fim", default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PLANEADO', verbose_name="Estado")
    ano_atual = models.BooleanField(default=False, verbose_name="Ano Atual")
    
    # Configurações de Mensalidades e Multas
    cobrar_propinas = models.BooleanField(default=True, verbose_name="Cobrar Propinas/Mensalidades")
    dia_pagamento_limite = models.PositiveIntegerField(default=10, verbose_name="Dia Limite de Pagamento (sem multa)")
    dia_inicio_multa = models.PositiveIntegerField(default=11, verbose_name="Dia de Início da Multa")
    percentagem_multa_inicial = models.DecimalField(max_digits=5, decimal_places=2, default=10.00, verbose_name="% Multa Inicial")
    percentagem_multa_diaria = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, verbose_name="% Multa Diária Adicional")
    dia_limite_multa = models.PositiveIntegerField(default=30, verbose_name="Dia Limite para Pagamento com Multa")

    # Bloqueio de Estudantes
    dia_bloqueio_estudante = models.PositiveIntegerField(default=15, verbose_name="Dia de Bloqueio Automático")
    bloquear_estudante_atrasado = models.BooleanField(default=True, verbose_name="Bloquear Estudante em Atraso")
    
    # Campo para bloqueio manual ou automático por dívida
    bloqueado_por_divida = models.BooleanField(default=False, verbose_name="Bloqueado por Dívida")
    
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    
    class Meta:
        verbose_name = "Ano Académico"
        verbose_name_plural = "Anos Académicos"
        ordering = ['-data_inicio']
    
    def __str__(self):
        return self.codigo
    
    @classmethod
    def get_atual(cls):
        return cls.objects.filter(ano_atual=True).first()

    def inscricoes_abertas(self):
        """Verifica se as inscrições estão abertas com base no novo modelo de Eventos"""
        evento = EventoCalendario.objects.filter(
            ano_lectivo=self,
            tipo_evento='INSCRICAO',
            estado='ATIVO'
        ).first()
        
        if not evento:
            return False
        return evento.esta_ocorrendo()

    def save(self, *args, **kwargs):
        # Sincronização lógica: se for o Ano Atual, o estado deve ser ATIVO
        if self.ano_atual:
            self.estado = 'ATIVO'
            
        # Garante que apenas UM ano seja o "Atual" (ano_atual=True)
        if self.ano_atual:
            AnoAcademico.objects.exclude(pk=self.pk).update(ano_atual=False)
            
        # Ao ativar um ano (estado='ATIVO'), os outros são marcados como encerrados
        if self.estado == 'ATIVO':
            AnoAcademico.objects.exclude(pk=self.pk).update(estado='ENCERRADO', ano_atual=False)
            
        super().save(*args, **kwargs)

class EventoCalendario(models.Model):
    TIPO_EVENTO_CHOICES = [
        ('INSCRICAO', 'Inscrição'),
        ('MATRICULA', 'Matrícula'),
        ('PROVA_PARCELAR_1', '1ª Prova Parcelar'),
        ('PROVA_PARCELAR_2', '2ª Prova Parcelar'),
        ('EXAME', 'Exame'),
        ('RECURSO', 'Recurso'),
        ('EXAME_ESPECIAL', 'Exame Especial'),
        ('FERIAS', 'Férias'),
        ('OUTRO', 'Outro'),
    ]
    
    ESTADO_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('ENCERRADO', 'Encerrado'),
    ]
    
    ano_lectivo = models.ForeignKey(AnoAcademico, on_delete=models.CASCADE, related_name='eventos', verbose_name="Ano Lectivo")
    tipo_evento = models.CharField(max_length=20, choices=TIPO_EVENTO_CHOICES, verbose_name="Tipo de Evento")
    descricao = models.CharField(max_length=255, verbose_name="Descrição")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim = models.DateField(verbose_name="Data de Fim")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ATIVO', verbose_name="Estado")

    class Meta:
        verbose_name = "Evento de Calendário"
        verbose_name_plural = "Eventos de Calendário"
        ordering = ['data_inicio']

    def __str__(self):
        return f"{self.get_tipo_evento_display()} - {self.ano_lectivo}"

    def esta_ocorrendo(self):
        hoje = timezone.now().date()
        return self.estado == 'ATIVO' and self.data_inicio <= hoje <= self.data_fim

class PeriodoLectivo(models.Model):
    ESTADO_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('ENCERRADO', 'Encerrado'),
    ]
    ano_lectivo = models.ForeignKey(AnoAcademico, on_delete=models.CASCADE, related_name='periodos_lectivos', verbose_name="Ano Lectivo")
    nome = models.CharField(max_length=100, verbose_name="Nome (ex: 1º Semestre / 2º Semestre)")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim = models.DateField(verbose_name="Data de Fim")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ATIVO', verbose_name="Estado")
    ativo = models.BooleanField(default=False, verbose_name="Período Corrente")

    class Meta:
        verbose_name = "Período Lectivo"
        verbose_name_plural = "Períodos Lectivos"
        ordering = ['ano_lectivo', 'data_inicio']

    def __str__(self):
        return f"{self.nome} - {self.ano_lectivo}"

    def save(self, *args, **kwargs):
        # Apenas um período letivo pode ser o "corrente" (ativo=True) por ano académico
        if self.ativo:
            PeriodoLectivo.objects.filter(ano_lectivo=self.ano_lectivo).exclude(pk=self.pk).update(ativo=False)
        
        # Sincronização lógica: se está ativo (corrente), o estado deve ser ATIVO
        if self.ativo:
            self.estado = 'ATIVO'
            
        super().save(*args, **kwargs)

class Privilegio(models.Model):
    MODULO_CHOICES = [
        ('SA', 'Secretaria Acadêmica'),
        ('RH', 'Recursos Humanos'),
        ('FIN', 'Financeiro'),
        ('PED', 'Pedagógico'),
        ('ADM', 'Administrativo'),
    ]
    
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Privilégio")
    codigo = models.SlugField(max_length=100, unique=True, verbose_name="Código Interno")
    descricao = models.TextField(verbose_name="Descrição")
    modulo = models.CharField(max_length=5, choices=MODULO_CHOICES, verbose_name="Módulo")
    
    class Meta:
        verbose_name = "Privilégio"
        verbose_name_plural = "Privilégios"
        ordering = ['modulo', 'nome']
        
    def __str__(self):
        return f"{self.modulo} - {self.nome}"

class PerfilUsuario(models.Model):
    # ... campos existentes ...
    # ... adicione isso ao modelo PerfilUsuario existente no arquivo
    privilegios = models.ManyToManyField(Privilegio, blank=True, related_name='perfis', verbose_name="Privilégios")
    NIVEL_ACESSO_CHOICES = [
        ('admin', 'Administrador'),
        ('pedagogico', 'Pedagógico'),
        ('financeiro', 'Financeiro'),
        ('secretaria', 'Secretaria'),
        ('professor', 'Professor'),
        ('estudante', 'Estudante'),
        ('pendente', 'Pendente'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    nivel_acesso = models.CharField(max_length=20, choices=NIVEL_ACESSO_CHOICES, default='pendente')
    telefone = models.CharField(max_length=20, blank=True)
    foto = models.ImageField(upload_to='perfis/', blank=True, null=True)
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"
        
    def __str__(self):
        return f"{self.user.username} - {self.get_nivel_acesso_display()}"

class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('INFO', 'Informação'),
        ('AVISO', 'Aviso'),
        ('URGENTE', 'Urgente'),
        ('SISTEMA', 'Sistema'),
    ]
    
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='INFO')
    destinatarios = models.ManyToManyField(User, related_name='notificacoes_recebidas', blank=True)
    global_notificacao = models.BooleanField(default=False, help_text="Se marcado, todos os usuários verão esta notificação")
    lida_por = models.ManyToManyField(User, related_name='notificacoes_lidas', blank=True)
    ativa = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ['-data_criacao']
        
    def __str__(self):
        return self.titulo

class Subscricao(models.Model):
    ESTADO_CHOICES = [
        ('ativo', 'Ativo'),
        ('expirado', 'Expirado'),
        ('pendente', 'Pendente'),
        ('cancelado', 'Cancelado'),
    ]
    
    PLANO_CHOICES = [
        ('trial', 'Trial (15 dias)'),
        ('mensal', 'Mensal'),
        ('anual', 'Anual'),
    ]
    
    nome_escola = models.CharField(max_length=200)
    plano = models.CharField(max_length=20, choices=PLANO_CHOICES, default='trial')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendente')
    data_inicio = models.DateField(default=timezone.now)
    data_expiracao = models.DateField()
    valor_pago = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    observacoes = models.TextField(blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Subscrição"
        verbose_name_plural = "Subscrições"
        
    def __str__(self):
        return f"{self.nome_escola} - {self.plano}"
    
    def esta_ativo(self):
        return self.estado == 'ativo' and self.data_expiracao >= timezone.now().date()
    
    @property
    def dias_restantes(self):
        delta = self.data_expiracao - timezone.now().date()
        return max(0, delta.days)

class PagamentoSubscricao(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    
    subscricao = models.ForeignKey(Subscricao, on_delete=models.CASCADE, related_name='pagamentos')
    plano_escolhido = models.CharField(max_length=20)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_pagamento = models.DateField()
    numero_referencia = models.CharField(max_length=100, blank=True)
    comprovante = models.FileField(upload_to='pagamentos/comprovantes/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField(blank=True)
    aprovado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    recibo_pdf = models.FileField(upload_to='pagamentos/recibos/', blank=True, null=True)
    data_submissao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Pagamento de Subscrição"
        verbose_name_plural = "Pagamentos de Subscrição"

class RecuperacaoSenha(models.Model):
    TIPO_CHOICES = [
        ('email', 'E-mail'),
        ('sms', 'SMS'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    codigo = models.CharField(max_length=10, default='000000')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    usado = models.BooleanField(default=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_expiracao = models.DateTimeField()
    email_enviado = models.EmailField(blank=True, null=True)
    telefone_enviado = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        verbose_name = "Recuperação de Senha"
        verbose_name_plural = "Recuperações de Senha"
        
    def esta_expirado(self):
        return timezone.now() > self.data_expiracao

class Documento(models.Model):
    SECAO_CHOICES = [
        ('geral', 'Geral'),
        ('inscricao', 'Inscrição'),
        ('financeiro', 'Financeiro'),
        ('academico', 'Académico'),
        ('rh', 'Recursos Humanos'),
        ('biblioteca', 'Biblioteca'),
        ('inventario', 'Inventário'),
    ]
    
    STATUS_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('ativo', 'Ativo'),
        ('arquivado', 'Arquivado'),
        ('obsoleto', 'Obsoleto'),
    ]

    titulo = models.CharField(max_length=200)
    versao = models.CharField(max_length=10, default='1.0')
    descricao = models.TextField(blank=True)
    conteudo = models.TextField(help_text="Template do documento (HTML/Text)")
    secao = models.CharField(max_length=20, choices=SECAO_CHOICES, default='geral')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    metadata = models.JSONField(default=dict, blank=True, help_text="Metadados ERP (JSON)")
    ativo = models.BooleanField(default=True)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    @property
    def historico_versoes(self):
        # Implementação futura para controle de versões
        return []
    
    @classmethod
    def obter_variaveis_disponiveis(cls, *args, **kwargs):
        return {
            'Geral': [
                '{escola_nome}', '{escola_decreto}', '{escola_endereco}', 
                '{escola_telefone}', '{escola_email}', '{data_atual}', 
                '{usuario_logado}', '{nif_escola}'
            ],
            'Candidato / Estudante': [
                '{nome_completo}', '{primeiro_nome}', '{apelido}', '{numero_inscricao}', 
                '{numero_processo}', '{bilhete_identidade}', '{nacionalidade}', 
                '{naturalidade}', '{data_nascimento}', '{sexo}', '{estado_civil}',
                '{endereco_estudante}', '{telefone_estudante}', '{email_estudante}'
            ],
            'Académico': [
                '{curso_nome}', '{curso_codigo}', '{grau_academico}', '{turma_nome}', 
                '{ano_academico}', '{semestre_atual}', '{media_final}', 
                '{status_academico}', '{data_inicio_curso}', '{data_fim_curso}'
            ],
            'Financeiro': [
                '{valor_pagamento}', '{data_pagamento}', '{numero_comprovante}', 
                '{tipo_pagamento}', '{status_pagamento}', '{valor_extenso}'
            ],
            'Responsáveis': [
                '{pai_nome}', '{mae_nome}', '{encarregado_nome}', 
                '{encarregado_telefone}', '{encarregado_parentesco}'
            ],
            'Assinaturas': [
                '{diretor_geral}', '{diretor_academico}', '{secretario_geral}'
            ]
        }

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        
    def __str__(self):
        return self.titulo

class Semestre(models.Model):
    SEMESTRE_CHOICES = [
        ('1', '1º Semestre'),
        ('2', '2º Semestre'),
    ]
    ano_academico = models.ForeignKey(AnoAcademico, on_delete=models.CASCADE, related_name='semestres', verbose_name="Ano Académico")
    nome = models.CharField(max_length=20, choices=SEMESTRE_CHOICES, verbose_name="Semestre")
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_fim = models.DateField(verbose_name="Data de Fim")
    ativo = models.BooleanField(default=False, verbose_name="Semestre Atual")

    class Meta:
        verbose_name = "Semestre"
        verbose_name_plural = "Semestres"
        unique_together = ['ano_academico', 'nome']
        ordering = ['ano_academico', 'nome']

    def __str__(self):
        return f"{self.get_nome_display()} - {self.ano_academico}"

    def save(self, *args, **kwargs):
        if self.ativo:
            Semestre.objects.filter(ano_academico=self.ano_academico).exclude(pk=self.pk).update(ativo=False)
        super().save(*args, **kwargs)

class ConfiguracaoEscola(models.Model):
    nome_escola = models.CharField(max_length=200, verbose_name="Nome da Escola")
    endereco = models.TextField(blank=True, verbose_name="Endereço")
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="Email")
    logo = models.ImageField(upload_to='escola/', blank=True, null=True, verbose_name="Logo da Escola")
    favicon = models.ImageField(upload_to='escola/', blank=True, null=True, verbose_name="Favicon")
    decreto_legalidade = models.CharField(max_length=500, blank=True, null=True, verbose_name="Decreto de Legalidade", help_text="Decreto que aprova a legalidade da instituição")
    
    # Assinaturas Dinâmicas
    tipo_ensino = models.CharField(
        max_length=20, 
        choices=[('superior', 'Ensino Superior'), ('geral', 'Ensino Geral')], 
        default='superior',
        verbose_name="Tipo de Instituição"
    )
    
    # Responsável Principal (Visto)
    nome_responsavel_visto = models.CharField(max_length=255, blank=True, verbose_name="Nome do Responsável (Visto)")
    cargo_responsavel_visto = models.CharField(max_length=255, blank=True, verbose_name="Cargo do Responsável (Visto)")
    grau_responsavel_visto = models.CharField(max_length=100, blank=True, verbose_name="Grau Académico (Visto)")
    
    # Responsável Administrativo (Assinatura)
    nome_responsavel_assinatura = models.CharField(max_length=255, blank=True, verbose_name="Nome do Responsável (Assinatura)")
    cargo_responsavel_assinatura = models.CharField(max_length=255, blank=True, verbose_name="Cargo do Responsável (Assinatura)")
    grau_responsavel_assinatura = models.CharField(max_length=100, blank=True, verbose_name="Grau Académico (Assinatura)")

    template_confirmacao_inscricao = models.TextField(
        default="CONFIRMAÇÃO DE INSCRIÇÃO\n\nNome: {nome}\nCurso: {curso}\nNúmero de Inscrição: {numero}\nData: {data}",
        verbose_name="Template de Confirmação de Inscrição",
        help_text="Use {nome}, {curso}, {numero}, {data} para campos dinâmicos"
    )
    
    class Meta:
        verbose_name = "Configuração da Escola"
        verbose_name_plural = "Configurações da Escola"
    
    def __str__(self):
        return self.nome_escola
    
    def save(self, *args, **kwargs):
        if not self.pk and ConfiguracaoEscola.objects.exists():
            raise ValueError('Só pode existir uma configuração de escola')
        return super().save(*args, **kwargs)

class NivelAcademico(models.Model):
    codigo = models.CharField(max_length=10, unique=True, null=True, blank=True, verbose_name="Código")
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome do Nível")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # Estrutura Académica
    duracao_padrao = models.PositiveIntegerField(default=4, verbose_name="Duração Padrão (Anos)")
    tipo_periodo = models.CharField(
        max_length=20, 
        choices=[('semestre', 'Semestres'), ('trimestre', 'Trimestres')], 
        default='semestre', 
        verbose_name="Tipo de Período"
    )
    periodos_por_ano = models.PositiveIntegerField(default=2, verbose_name="Número de Períodos por Ano")
    creditos_minimos = models.PositiveIntegerField(default=0, verbose_name="Total Mínimo de Créditos")
    
    # Regras Académicas
    nota_minima_aprovacao = models.DecimalField(max_digits=4, decimal_places=2, default=10.00, validators=[MinValueValidator(0.0), MaxValueValidator(10.0)], verbose_name="Nota Mínima de Aprovação")
    escala_notas_min = models.IntegerField(default=0, verbose_name="Escala Mínima")
    escala_notas_max = models.IntegerField(default=20, validators=[MinValueValidator(0), MaxValueValidator(20)], verbose_name="Escala Máxima")
    media_minima_progressao = models.DecimalField(max_digits=4, decimal_places=2, default=10.00, verbose_name="Média Mínima para Progressão")
    limite_reprovacoes = models.PositiveIntegerField(null=True, blank=True, verbose_name="Limite de Reprovações")
    
    # Regras de Admissão
    nivel_entrada_exigido = models.CharField(max_length=100, blank=True, verbose_name="Nível de entrada exigido")
    exige_teste_admissao = models.BooleanField(default=False, verbose_name="Exige teste de admissão?")
    documentos_obrigatorios = models.TextField(blank=True, verbose_name="Documentos obrigatórios")
    
    # Regime de Funcionamento
    regime_regular = models.BooleanField(default=True, verbose_name="Regular")
    regime_pos_laboral = models.BooleanField(default=False, verbose_name="Pós-laboral")
    regime_modular = models.BooleanField(default=False, verbose_name="Modular")
    
    turno_manha = models.BooleanField(default=True, verbose_name="Manhã")
    turno_tarde = models.BooleanField(default=True, verbose_name="Tarde")
    turno_noite = models.BooleanField(default=False, verbose_name="Noite")
    
    # Situação Legal / Institucional
    base_legal = models.CharField(max_length=200, blank=True, verbose_name="Base legal")
    entidade_acreditadora = models.CharField(max_length=100, blank=True, verbose_name="Entidade acreditadora")
    
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nível Académico"
        verbose_name_plural = "Níveis Académicos"
        ordering = ['nome']

    def __str__(self):
        return self.nome

class Curso(models.Model):
    REGIME_CHOICES = [
        ('diurno', 'Diurno'),
        ('pos-laboral', 'Pós-Laboral'),
    ]
    
    MODALIDADE_CHOICES = [
        ('presencial', 'Presencial'),
        ('semipresencial', 'Semipresencial'),
        ('ead', 'EAD'),
    ]

    DURACAO_CHOICES = [
        (3, '3 meses'),
        (6, '6 meses'),
        (12, '1 ano'),
        (24, '2 anos'),
        (36, '3 anos'),
        (48, '4 anos'),
        (60, '5 anos'),
    ]
    
    codigo = models.CharField(max_length=50, unique=True, default="CURSO", verbose_name="Código do Curso")
    nome = models.CharField(max_length=200, verbose_name="Nome do Curso")
    slug = models.SlugField(unique=True, null=True, blank=True, verbose_name="Slug (URL Amigável)")
    grau = models.ForeignKey(NivelAcademico, on_delete=models.CASCADE, related_name='cursos', verbose_name="Grau Académico")
    regime = models.CharField(max_length=20, choices=REGIME_CHOICES, default='diurno', verbose_name="Regime")
    modalidade = models.CharField(max_length=20, choices=MODALIDADE_CHOICES, default='presencial', verbose_name="Modalidade")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    vagas = models.PositiveIntegerField(verbose_name="Número de Vagas")
    duracao_meses = models.PositiveIntegerField(
        choices=DURACAO_CHOICES,
        default=12,
        verbose_name="Duração"
    )
    nota_minima = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=10.00,
        validators=[MinValueValidator(10.00), MaxValueValidator(20.00)],
        verbose_name="Nota Mínima para Aprovação"
    )
    requer_prerequisitos = models.BooleanField(default=False, verbose_name="Requer Pré-requisitos")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            self.slug = slugify(self.nome)
            if Curso.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)
    
    def vagas_disponiveis(self):
        aprovados = self.inscricoes.filter(aprovado=True).count()
        return max(0, self.vagas - aprovados)
    
    def total_inscricoes(self):
        return self.inscricoes.count()
    
    def get_duracao_display_full(self):
        return f"{self.get_duracao_meses_display()}"

class ConfiguracaoAcademica(models.Model):
    # Regras de Avaliação
    percentagem_prova_continua = models.PositiveIntegerField(default=40, verbose_name="% Prova Contínua")
    peso_avaliacao_continua = models.PositiveIntegerField(default=1, help_text="Peso da avaliação contínua no cálculo final (ex: 1)", verbose_name="Peso Avaliação Contínua")
    percentagem_exame_final = models.PositiveIntegerField(default=60, verbose_name="% Exame Final")
    
    # Regras de Dispensa
    dispensa_apenas_complementares = models.BooleanField(default=False, verbose_name="Dispensa apenas disciplinas complementares", help_text="Se ativo, disciplinas nucleares/obrigatórias não permitem dispensa")
    exigir_duas_positivas_dispensa = models.BooleanField(default=True, verbose_name="Exigir duas provas parcelares positivas para dispensa", help_text="Se ativo, qualquer nota negativa nas parcelares bloqueia a dispensa, mesmo com média >= 14")
    
    aplicar_lei_da_setima_global = models.BooleanField(default=True, verbose_name="Aplicar Lei da Sétima Institucional", help_text="Ativa a regra de média mínima 7 em avaliações parciais para toda a escola")
    aplicar_regras_projeto_especiais = models.BooleanField(default=True, verbose_name="Aplicar Regras Especiais para Projeto", help_text="Ativa regras diferenciadas para disciplinas de projeto (Exame=Projeto, etc)")
    
    # Regras de Assiduidade
    minimo_presenca_obrigatoria = models.PositiveIntegerField(default=75, verbose_name="% Mínimo Presença")
    
    # Regras de Progressão Institucional
    ativar_barreiras_progressao = models.BooleanField(default=True, verbose_name="Ativar Barreiras de Progressão")
    permite_equivalencia_automatica = models.BooleanField(default=True, verbose_name="Permite Equivalência Automática")
    anos_com_barreira_atraso = models.CharField(max_length=100, default="3,5", help_text="Anos que exigem zero atrasos (ex: 3,5)")
    limite_semestres_trancamento = models.PositiveIntegerField(default=2, verbose_name="Máximo Semestres Trancamento")
    limite_tempo_exclusao_anos = models.PositiveIntegerField(default=1, verbose_name="Anos para Exclusão por Inatividade")

    # Novas Regras Globais Académicas
    criterio_desempate = models.CharField(
        max_length=50,
        choices=[
            ('idade_desc', 'Mais Velho primeiro'),
            ('idade_asc', 'Mais Novo primeiro'),
            ('inscricao_asc', 'Ordem de Inscrição (Primeiros primeiro)'),
            ('sexo_f', 'Prioridade Feminino'),
            ('sexo_m', 'Prioridade Masculino'),
            ('sexo_f_novo', 'Feminino e Mais Novo'),
            ('sexo_f_velho', 'Feminino e Mais Velho'),
        ],
        default='idade_desc',
        verbose_name="Critério de Desempate"
    )
    media_aprovacao_direta = models.DecimalField(max_digits=4, decimal_places=2, default=14.0, verbose_name="Média Aprovação Direta")
    media_minima_exame = models.DecimalField(max_digits=4, decimal_places=2, default=10.0, verbose_name="Média Mínima Exame")
    media_reprovacao_direta = models.DecimalField(max_digits=4, decimal_places=2, default=7.0, verbose_name="Média Reprovação Direta")
    max_disciplinas_atraso = models.PositiveIntegerField(default=2, verbose_name="Limite Cadeiras Atraso")
    permite_exame_especial = models.BooleanField(default=True, verbose_name="Permite Exames Especiais")
    precedencia_automatica_romana = models.BooleanField(default=True, verbose_name="Precedência Automática (I, II, III...)")
    usar_creditos = models.BooleanField(default=True, verbose_name="Usar Sistema de Créditos", help_text="Se desativado, o campo de créditos será opcional/oculto")

    class Meta:
        verbose_name = "Configuração Académica Global"
        verbose_name_plural = "Configurações Académicas Globais"

    def __str__(self):
        return "Configurações Globais do Sistema"

    def save(self, *args, **kwargs):
        if not self.pk and ConfiguracaoAcademica.objects.exists():
            return
        super().save(*args, **kwargs)

class GradeCurricular(models.Model):
    ESTADO_CHOICES = [
        ('rascunho', 'Rascunho'),
        ('ativo', 'Ativo'),
        ('obsoleto', 'Obsoleto'),
    ]
    
    TIPO_PERIODO_CHOICES = [
        ('semestre', 'Semestral'),
        ('trimestre', 'Trimestral'),
    ]
    
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='grades_curriculares', verbose_name="Curso")
    versao = models.CharField(max_length=50, verbose_name="Versão (Ano ou Código)")
    duracao_anos = models.PositiveIntegerField(default=4, verbose_name="Duração (Anos)")
    tipo_periodo = models.CharField(max_length=20, choices=TIPO_PERIODO_CHOICES, default='semestre', verbose_name="Tipo de Período")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='rascunho', verbose_name="Estado")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    
    # Regras Académicas da Grelha
    aplicar_lei_da_setima = models.BooleanField(default=True, verbose_name="Aplicar 'Lei da Sétima'", help_text="Média < 7 em avaliações parciais implica reprovação direta")
    media_aprovacao_direta = models.DecimalField(max_digits=4, decimal_places=2, default=14.00, verbose_name="Média para Dispensa/Aprovação Direta")
    media_minima_exame = models.DecimalField(max_digits=4, decimal_places=2, default=10.00, verbose_name="Média Mínima para Exame")
    media_reprovacao_direta = models.DecimalField(max_digits=4, decimal_places=2, default=7.00, verbose_name="Média para Reprovação Direta")
    max_disciplinas_atraso = models.PositiveIntegerField(default=2, verbose_name="Limite de Disciplinas em Atraso")
    permite_exame_especial = models.BooleanField(default=True, verbose_name="Permite Exame Especial (Recurso)")
    precedencia_automatica_romana = models.BooleanField(default=True, verbose_name="Ativar Precedência Automática (I, II, III, IV)")
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grade Curricular"
        verbose_name_plural = "Grades Curriculares"
        unique_together = ['curso', 'versao']
        ordering = ['curso', '-versao']

    def __str__(self):
        return f"{self.curso.nome} - {self.versao}"

class Reclamacao(models.Model):
    TIPO_CHOICES = [
        ('ACADEMICA', 'Académica'),
        ('FINANCEIRA', 'Financeira'),
    ]
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_ANALISE', 'Em Análise'),
        ('RESOLVIDO', 'Resolvido'),
        ('REJEITADO', 'Rejeitado'),
    ]
    ESTAGIO_CHOICES = [
        ('SECRETARIA', 'Secretaria / DAAC'),
        ('DIRETOR', 'Diretor'),
        ('ADMIN', 'Administrador'),
        ('SUPER_ADMIN', 'Super Administrador'),
    ]

    estudante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reclamacoes')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    motivo = models.TextField(verbose_name="Motivo / Descrição")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    estagio_atual = models.CharField(max_length=20, choices=ESTAGIO_CHOICES, default='SECRETARIA')
    
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    resposta = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Reclamação"
        verbose_name_plural = "Reclamações"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Reclamação {self.id} - {self.estudante.username}"

class Sala(models.Model):
    TIPO_CHOICES = [
        ('normal', 'Normal'),
        ('laboratorio', 'Laboratório'),
    ]
    
    nome = models.CharField(max_length=100, verbose_name="Nome da Sala")
    capacidade = models.PositiveIntegerField(verbose_name="Capacidade")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='normal', verbose_name="Tipo")
    ativa = models.BooleanField(default=True, verbose_name="Estado (Ativa)")

    class Meta:
        verbose_name = "Sala"
        verbose_name_plural = "Salas"

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

class Disciplina(models.Model):
    TIPO_CHOICES = [
        ('obrigatoria', 'Obrigatória'),
        ('opcional', 'Opcional'),
    ]

    AREA_CHOICES = [
        ('nuclear', 'Nuclear/Científica'),
        ('complementar', 'Complementar'),
        ('geral', 'Formação Geral'),
        ('projeto', 'Projeto/Estágio'),
    ]
    
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='disciplinas', verbose_name="Curso")
    grade_curricular = models.ForeignKey(GradeCurricular, on_delete=models.SET_NULL, null=True, blank=True, related_name='disciplinas', verbose_name="Grade Curricular")
    nome = models.CharField(max_length=200, verbose_name="Nome da Disciplina")
    area_conhecimento = models.CharField(max_length=30, choices=AREA_CHOICES, default='nuclear', verbose_name="Área de Conhecimento")
    is_projeto = models.BooleanField(default=False, verbose_name="É Disciplina de Projeto?")
    carga_horaria = models.PositiveIntegerField(verbose_name="Carga Horária (horas)", default=40)
    creditos = models.PositiveIntegerField(default=0, verbose_name="Créditos", null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='obrigatoria', verbose_name="Tipo")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    codigo = models.CharField(max_length=50, blank=True, verbose_name="Código da Disciplina")
    ano_curricular = models.PositiveIntegerField(default=1, verbose_name="Ano Curricular", null=True, blank=True)
    semestre_curricular = models.PositiveIntegerField(
        default=1, 
        verbose_name="Período Curricular",
        null=True,
        blank=True
    )
    prerequisitos = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='sucessoras', verbose_name="Pré-requisitos")
    requer_duas_positivas_para_dispensa = models.BooleanField(default=False, verbose_name="Requer Positiva nas Provas Parcelares para Dispensa")
    lei_7_aplicavel = models.BooleanField(default=False, verbose_name="Aplicar Lei 7 (Reprovação Direta se Média < 7)")
    
    def save(self, *args, **kwargs):
        if self.is_projeto:
            self.lei_7_aplicavel = False
            self.requer_duas_positivas_para_dispensa = False
        
        # Arredondamento de notas se aplicável (exemplo: para o inteiro mais próximo ou 1 casa decimal)
        # Se houver campos de nota específicos aqui, poderiam ser arredondados.
        # No contexto de GradeCurricular e Disciplina, as regras de média são decimais.
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Disciplina"
        verbose_name_plural = "Disciplinas"
        ordering = ['curso', 'ano_curricular', 'semestre_curricular', 'nome']
    
    def __str__(self):
        return f"{self.nome} ({self.curso.codigo})"

class PrerequisitoDisciplina(models.Model):
    """Define as disciplinas pré-requisito para inscrição em um curso"""
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='prerequisitos', verbose_name="Curso")
    disciplina_prerequisito = models.ForeignKey(Disciplina, on_delete=models.CASCADE, verbose_name="Disciplina Pré-requisito")
    nota_minima_prerequisito = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=12.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(20.0)],
        verbose_name="Nota Mínima Necessária"
    )
    obrigatorio = models.BooleanField(default=True, verbose_name="Obrigatório")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem")
    
    class Meta:
        verbose_name = "Pré-requisito de Disciplina"
        verbose_name_plural = "Pré-requisitos de Disciplina"
        ordering = ['curso', 'ordem']
        unique_together = ['curso', 'disciplina_prerequisito']
    
    def __str__(self):
        return f"{self.curso.nome} ← {self.disciplina_prerequisito.nome} ({self.nota_minima_prerequisito})"

class Turma(models.Model):
    TURNO_CHOICES = [
        ('manha', 'Manhã'),
        ('tarde', 'Tarde'),
        ('noite', 'Noite'),
    ]
    
    nome = models.CharField(max_length=100, verbose_name="Nome da Turma")
    curso = models.ForeignKey('core.Curso', on_delete=models.CASCADE, related_name='turmas_academica')
    ano_lectivo = models.ForeignKey('core.AnoAcademico', on_delete=models.CASCADE, related_name='turmas_academica', null=True)
    ano_academico = models.PositiveIntegerField(verbose_name="Ano Académico (ex: 1, 2, 3)", default=1)
    periodo_curricular = models.PositiveIntegerField(verbose_name="Semestre/Trimestre", default=1)
    turno = models.CharField(max_length=10, choices=TURNO_CHOICES, default='manha')
    capacidade = models.PositiveIntegerField(default=40)
    ativa = models.BooleanField(default=True)
    sala = models.ForeignKey('core.Sala', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sala Principal")
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name="Data de Criação")
    
    disciplinas_turma = models.ManyToManyField('core.Disciplina', through='TurmaDisciplina', related_name='turmas_disciplina')

    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"
        unique_together = ['nome', 'curso']

    def __str__(self):
        return f"{self.nome} - {self.curso.nome} ({self.ano_lectivo})"

class TurmaDisciplina(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE)
    professor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'perfil__nivel_acesso': 'professor'})
    sala = models.ForeignKey('core.Sala', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Novos campos para Horário
    dia_semana = models.CharField(max_length=20, choices=[
        ('segunda', 'Segunda-feira'),
        ('terca', 'Terça-feira'),
        ('quarta', 'Quarta-feira'),
        ('quinta', 'Quinta-feira'),
        ('sexta', 'Sexta-feira'),
        ('sabado', 'Sábado'),
    ], null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fim = models.TimeField(null=True, blank=True)
    tempo_tipo = models.CharField(max_length=20, choices=[
        ('1_semestre', '1º Semestre'),
        ('2_semestre', '2º Semestre'),
        ('trimestre', 'Trimestre'),
    ], null=True, blank=True)
    
    class Meta:
        # Removendo unique_together antigo para permitir múltiplos horários da mesma disciplina/turma em dias diferentes
        # unique_together = ['turma', 'disciplina']
        verbose_name = "Horário de Aula"
        verbose_name_plural = "Horários de Aula"

class Escola(models.Model):
    nome = models.CharField(max_length=300, verbose_name="Nome da Escola", unique=True)
    municipio = models.CharField(max_length=100, verbose_name="Município", blank=True)
    provincia = models.CharField(max_length=100, verbose_name="Província", blank=True)
    tipo = models.CharField(
        max_length=20,
        choices=[
            ('Pública', 'Pública'),
            ('Privada', 'Privada'),
        ],
        default='Pública',
        verbose_name="Tipo"
    )
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Escola"
        verbose_name_plural = "Escolas"
        ordering = ['nome']
    
    def __str__(self):
        return self.nome

class Inscricao(models.Model):
    TURNO_CHOICES = [
        ('M', 'Manhã'),
        ('T', 'Tarde'),
        ('N', 'Noite'),
    ]
    
    ESTADO_CIVIL_CHOICES = [
        ('S', 'Solteiro(a)'),
        ('C', 'Casado(a)'),
        ('D', 'Divorciado(a)'),
        ('V', 'Viúvo(a)'),
    ]
    
    numero_inscricao = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Número de Inscrição")
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='inscricoes', verbose_name="Curso")
    
    # 1. Identificação
    primeiro_nome = models.CharField(max_length=50, verbose_name="Primeiro Nome", default="")
    nomes_meio = models.CharField(max_length=100, verbose_name="Nomes do Meio", blank=True, default="")
    apelido = models.CharField(max_length=50, verbose_name="Apelido", default="")
    foto = models.ImageField(upload_to='estudantes/fotos/', blank=True, null=True, verbose_name="Foto do Estudante")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    local_nascimento = models.CharField(max_length=200, verbose_name="Local de Nascimento", default="Luanda")
    nacionalidade = models.CharField(max_length=100, verbose_name="Nacionalidade", default="Angolana")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Número do Bilhete de Identidade")
    data_validade_bi = models.DateField(verbose_name="Data de Validade do BI", null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], verbose_name="Sexo")
    estado_civil = models.CharField(max_length=1, choices=ESTADO_CIVIL_CHOICES, default='S', verbose_name="Estado Civil")
    endereco = models.TextField(verbose_name="Endereço Completo")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="Email", blank=True, null=True)
    # Status da Inscrição
    STATUS_INSCRICAO_CHOICES = [
        ('submetida', 'Submetida'),
        ('em_analise', 'Em Análise'),
        ('aprovada', 'Aprovada'),
        ('rejeitada', 'Rejeitada'),
    ]
    status_inscricao = models.CharField(
        max_length=20, 
        choices=STATUS_INSCRICAO_CHOICES, 
        default='submetida', 
        verbose_name="Estado da Inscrição"
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário de Acesso")
    ano_academico = models.ForeignKey(AnoAcademico, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Ano Académico")
    periodo_lectivo = models.ForeignKey(PeriodoLectivo, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Período Lectivo")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscricoes_criadas', verbose_name="Registado por")
    
    # Documentos
    arquivo_bi = models.FileField(
        upload_to='estudantes/documentos/bi/', 
        blank=True, 
        null=True, 
        verbose_name="Cópia do BI (PDF ou Imagem)",
        help_text="Tamanho máximo: 5MB"
    )
    arquivo_certificado = models.FileField(
        upload_to='estudantes/documentos/certificados/', 
        blank=True, 
        null=True, 
        verbose_name="Certificado/Habilitação (PDF ou Imagem)",
        help_text="Tamanho máximo: 5MB"
    )

    data_cadastro = models.DateTimeField(default=timezone.now, verbose_name="Data de Cadastro")
    status = models.CharField(max_length=20, default='Ativo', verbose_name="Status")
    matricula_bloqueada = models.BooleanField(default=False, verbose_name="Matrícula Bloqueada?")
    
    # 2. Informações Académicas
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscricoes', verbose_name="Última Escola Frequentada")
    ano_conclusao = models.CharField(max_length=4, verbose_name="Ano de Conclusão", default="2024")
    certificados_obtidos = models.TextField(verbose_name="Certificados/Diplomas Obtidos", blank=True, default="")
    historico_escolar = models.TextField(verbose_name="Notas/Histórico Escolar", blank=True, default="")
    turno_preferencial = models.CharField(max_length=1, choices=TURNO_CHOICES, verbose_name="Turno Preferencial", default='M')
    
    # 3. Informações Financeiras
    METODO_PAGAMENTO_CHOICES = [
        ('referencia', 'Referência Bancária'),
        ('multicaixa', 'Multicaixa (Transferência/Depósito)'),
    ]
    metodo_pagamento = models.CharField(max_length=20, choices=METODO_PAGAMENTO_CHOICES, default='multicaixa', verbose_name="Método de Pagamento")
    comprovativo_pagamento = models.FileField(upload_to='estudantes/pagamentos/', blank=True, null=True, verbose_name="Comprovativo de Pagamento")
    hash_seguranca = models.CharField(max_length=64, blank=True, editable=False, verbose_name="Hash de Segurança")
    
    numero_comprovante = models.CharField(max_length=100, verbose_name="Número do Comprovante/Boleto", blank=True)
    responsavel_financeiro_nome = models.CharField(max_length=200, verbose_name="Nome do Responsável Financeiro", blank=True)
    responsavel_financeiro_telefone = models.CharField(max_length=20, verbose_name="Telefone do Responsável Financeiro", blank=True)
    responsavel_financeiro_relacao = models.CharField(max_length=100, verbose_name="Relação com o Estudante", blank=True)
    
    # 4. Responsáveis
    responsavel_legal_nome = models.CharField(max_length=200, blank=True, verbose_name="Nome do Contacto")
    responsavel_legal_vinculo = models.CharField(max_length=100, blank=True, verbose_name="Grau/Vínculo")
    responsavel_legal_telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    
    responsavel_pedagogico_nome = models.CharField(max_length=200, blank=True, verbose_name="Nome do Responsável Pedagógico")
    responsavel_pedagogico_vinculo = models.CharField(max_length=100, blank=True, verbose_name="Grau/Vínculo Pedagógico")
    responsavel_pedagogico_telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone Pedagógico")
    
    # 6. Configurações
    receber_emails_sistema = models.BooleanField(default=True, verbose_name="Deseja receber emails do sistema?")
    
    # Sistema de Aprovação
    nota_teste = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.00), MaxValueValidator(20.00)],
        verbose_name="Nota do Teste (0-20)"
    )
    
    aprovado = models.BooleanField(default=False, verbose_name="Aprovado")
    data_inscricao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Inscrição")
    data_resultado = models.DateTimeField(null=True, blank=True, verbose_name="Data do Resultado")
    
    class Meta:
        verbose_name = "Inscrição"
        verbose_name_plural = "Inscrições"
        ordering = ['-data_inscricao']
    
    @property
    def nome_completo(self):
        """Retorna o nome completo concatenado"""
        nomes = [self.primeiro_nome, self.nomes_meio, self.apelido]
        return " ".join(filter(None, nomes))

    def __str__(self):
        return f"{self.numero_inscricao} - {self.nome_completo}"
    
    def save(self, *args, **kwargs):
        if not self.numero_inscricao:
            ultimo = Inscricao.objects.order_by('-id').first()
            if ultimo:
                try:
                    numero = int(ultimo.numero_inscricao.split('-')[1]) + 1
                except:
                    numero = 1
            else:
                numero = 1
            self.numero_inscricao = f"INS-{numero:06d}"
        super().save(*args, **kwargs)
    
    def calcular_idade(self):
        """Calcula a idade do estudante"""
        from datetime import date
        hoje = date.today()
        idade = hoje.year - self.data_nascimento.year
        if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
            idade -= 1
        return idade
    
    def proximo_aniversario(self):
        """Retorna a data do próximo aniversário"""
        from datetime import date
        hoje = date.today()
        proximo = date(hoje.year, self.data_nascimento.month, self.data_nascimento.day)
        if proximo < hoje:
            proximo = date(hoje.year + 1, self.data_nascimento.month, self.data_nascimento.day)
        return proximo
    
    def bi_vencido(self):
        """Verifica se o BI está vencido"""
        from datetime import date
        if self.data_validade_bi:
            return self.data_validade_bi < date.today()
        return False

class HistoricoAcademico(models.Model):
    """Histórico académico do aluno - notas em disciplinas anteriores"""
    inscricao = models.OneToOneField(Inscricao, on_delete=models.CASCADE, related_name='historico_academico', verbose_name="Inscrição")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Histórico Académico"
        verbose_name_plural = "Históricos Académicos"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Histórico de {self.inscricao.nome_completo}"
    
    def esta_habilitado_para_curso(self, curso):
        """Verifica se aluno está habilitado para o curso baseado em pré-requisitos"""
        if not curso.prerequisitos.exists():
            return True, "✓ Sem pré-requisitos"
        
        media = self.calcular_media_prerequisitos(curso)
        for prereq in curso.prerequisitos.filter(obrigatorio=True):
            nota = self.notas_disciplina.filter(disciplina=prereq.disciplina_prerequisito).first()
            if not nota or nota.nota < prereq.nota_minima_prerequisito:
                return False, f"Nota insuficiente em {prereq.disciplina_prerequisito.nome} (mínima: {prereq.nota_minima_prerequisito})"
        
        return True, f"✓ Habilitado (Média: {media:.2f})" if media else (True, "✓ Habilitado")
    
    def calcular_media_prerequisitos(self, curso):
        """Calcula a média de pré-requisitos"""
        notas = [float(n.nota) for n in self.notas_disciplina.filter(disciplina__in=[p.disciplina_prerequisito for p in curso.prerequisitos.all()]) if n.nota]
        return sum(notas) / len(notas) if notas else None

class NotaDisciplina(models.Model):
    """Nota do aluno em uma disciplina anterior"""
    historico = models.ForeignKey(HistoricoAcademico, on_delete=models.CASCADE, related_name='notas_disciplina', verbose_name="Histórico")
    disciplina = models.ForeignKey(Disciplina, on_delete=models.PROTECT, verbose_name="Disciplina")
    nota = models.DecimalField(max_digits=4, decimal_places=2, validators=[MinValueValidator(0.0), MaxValueValidator(20.0)], verbose_name="Nota")
    ano_conclusao = models.PositiveIntegerField(verbose_name="Ano de Conclusão")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    
    class Meta:
        verbose_name = "Nota de Disciplina"
        verbose_name_plural = "Notas de Disciplina"
        unique_together = ['historico', 'disciplina']
        ordering = ['-ano_conclusao', 'disciplina']
    
    def __str__(self):
        return f"{self.historico.inscricao.nome_completo} - {self.disciplina.nome}: {self.nota}"

class HorarioAula(models.Model):
    DIAS_SEMANA = [
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'),
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
    ]
    
    TIPO_AULA_CHOICES = [
        ('teorica', 'Teórica'),
        ('pratica', 'Prática'),
        ('laboratorio', 'Laboratório'),
        ('seminario', 'Seminário'),
    ]

    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('cancelado', 'Cancelado'),
        ('suspenso', 'Suspenso'),
    ]
    
    turma = models.ForeignKey('Turma', on_delete=models.CASCADE, related_name='horarios_aula', null=True)
    professor = models.ForeignKey('Professor', on_delete=models.CASCADE, related_name='horarios')
    disciplina = models.ForeignKey('Disciplina', on_delete=models.CASCADE)
    sala = models.ForeignKey('Sala', on_delete=models.SET_NULL, null=True, blank=True)
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fim = models.TimeField()
    tipo_aula = models.CharField(max_length=20, choices=TIPO_AULA_CHOICES, default='teorica')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo')
    tempos_aula = models.PositiveIntegerField(default=2, help_text="Número de tempos/horas aula nesta sessão")
    data_criacao = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    data_atualizacao = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        verbose_name = "Horário de Aula"
        verbose_name_plural = "Horários de Aula"

class RegistroPresencaProfessor(models.Model):
    professor = models.ForeignKey('Professor', on_delete=models.CASCADE)
    disciplina = models.ForeignKey('Disciplina', on_delete=models.CASCADE)
    data = models.DateField()
    horario = models.ForeignKey(HorarioAula, on_delete=models.SET_NULL, null=True)
    lecionada = models.BooleanField(default=True)
    observacao = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Registro de Carga Letiva"
        verbose_name_plural = "Registros de Carga Letiva"

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    codigo_professor = models.CharField(max_length=20, unique=True, verbose_name="Código do Professor", blank=True)
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo", unique=True)
    genero = models.CharField(max_length=20, choices=[('M', 'Masculino'), ('F', 'Feminino')], verbose_name="Género", default='M')
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    nacionalidade = models.CharField(max_length=100, verbose_name="Nacionalidade", default="Angolana")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Nº do BI", unique=True)
    estado_civil = models.CharField(max_length=50, verbose_name="Estado Civil", blank=True)
    
    # DADOS DE CONTACTO
    telefone = models.CharField(max_length=20, verbose_name="Telefone", unique=True)
    email = models.EmailField(verbose_name="Email", unique=True)
    endereco = models.TextField(verbose_name="Endereço")
    municipio_provincia = models.CharField(max_length=200, verbose_name="Município / Província", blank=True)
    
    # DADOS PROFISSIONAIS
    GRAU_ACADEMICO_CHOICES = [
        ('licenciado', 'Licenciado'),
        ('mestre', 'Mestre'),
        ('doutor', 'Doutor'),
    ]
    grau_academico = models.CharField(max_length=20, choices=GRAU_ACADEMICO_CHOICES, verbose_name="Grau Académico", blank=True)
    area_formacao = models.CharField(max_length=200, verbose_name="Área de Formação", blank=True)
    especialidade = models.CharField(max_length=200, verbose_name="Especialidade", blank=True, null=True)
    
    CATEGORIA_CHOICES = [
        ('assistente_estagiario', 'Assistente Estagiário'),
        ('assistente', 'Assistente'),
        ('auxiliar', 'Auxiliar'),
        ('associado', 'Associado'),
        ('professor_catedratico', 'Professor Catedrático'),
        ('docente_convidado', 'Docente Convidado'),
    ]
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, verbose_name="Categoria", blank=True)
    
    TIPO_VINCULO_CHOICES = [
        ('efetivo', 'Efetivo'),
        ('colaborador', 'Colaborador'),
        ('estagiario', 'Estagiário'),
    ]
    tipo_vinculo = models.CharField(max_length=20, choices=TIPO_VINCULO_CHOICES, verbose_name="Tipo de Vínculo", blank=True)
    
    # DADOS ADMINISTRATIVOS
    data_admissao = models.DateField(verbose_name="Data de Admissão", default=timezone.now)
    data_contratacao = models.DateField(verbose_name="Data de Contratação", default=timezone.now) # Mantendo por compatibilidade se necessário
    
    ESTADO_CHOICES = [
        ('ativo', 'Ativo'),
        ('inativo', 'Inativo'),
    ]
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ativo', verbose_name="Estado")
    
    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"
        ordering = ['nome_completo']
    
    def __str__(self):
        return f"{self.codigo_professor} - {self.nome_completo}" if self.codigo_professor else self.nome_completo

    def save(self, *args, **kwargs):
        if not self.codigo_professor:
            ano = timezone.now().year
            ultimo = Professor.objects.filter(codigo_professor__contains=f"PROF/{ano}/").order_by('-id').first()
            if ultimo:
                try:
                    numero = int(ultimo.codigo_professor.split('/')[-1]) + 1
                except:
                    numero = 1
            else:
                numero = 1
            self.codigo_professor = f"PROF/{ano}/{numero:04d}"
        super().save(*args, **kwargs)

class ProfessorDisciplina(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='professor_disciplinas')
    disciplina = models.ForeignKey('Disciplina', on_delete=models.CASCADE)
    data_atribuicao = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Professor Disciplina"
        verbose_name_plural = "Professor Disciplinas"
        unique_together = ['professor', 'disciplina']

    def __str__(self):
        return f"{self.professor.nome_completo} - {self.disciplina.nome}"

class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    numero_estudante = models.CharField(max_length=20, unique=True, verbose_name="Número de Estudante")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Bilhete de Identidade")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], verbose_name="Sexo")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="Email")
    endereco = models.TextField(verbose_name="Endereço")
    turma = models.ForeignKey(Turma, on_delete=models.SET_NULL, null=True, blank=True, related_name='alunos', verbose_name="Turma")
    data_matricula = models.DateField(verbose_name="Data de Matrícula", default=timezone.now)
    
    class Meta:
        verbose_name = "Aluno"
        verbose_name_plural = "Alunos"
        ordering = ['nome_completo']
    
    def __str__(self):
        return f"{self.numero_estudante} - {self.nome_completo}"
    
    def save(self, *args, **kwargs):
        if not self.numero_estudante:
            ultimo = Aluno.objects.order_by('-id').first()
            if ultimo and ultimo.numero_estudante:
                try:
                    numero = int(ultimo.numero_estudante.split('-')[1]) + 1
                except:
                    numero = 1
            else:
                numero = 1
            self.numero_estudante = f"ALU-{numero:06d}"
        super().save(*args, **kwargs)

class NotaEstudante(models.Model):
    ano_academico = models.ForeignKey(AnoAcademico, on_delete=models.CASCADE, related_name='notas_estudantes')
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='notas_estudantes')
    disciplina = models.ForeignKey(Disciplina, on_delete=models.CASCADE, related_name='notas_estudantes')
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='notas_estudantes')
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='notas_estudantes')
    nota = models.DecimalField(max_digits=4, decimal_places=2, validators=[MinValueValidator(0.0), MaxValueValidator(20.0)], null=True, blank=True)
    data_lancamento = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Nota do Estudante"
        verbose_name_plural = "Notas dos Estudantes"
        unique_together = ['ano_academico', 'turma', 'disciplina', 'aluno']

    def __str__(self):
        return f"{self.aluno.nome_completo} - {self.disciplina.nome}: {self.nota}"

class Pai(models.Model):
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Bilhete de Identidade")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="Email")
    endereco = models.TextField(verbose_name="Endereço")
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='pais', verbose_name="Aluno", null=True, blank=True)
    
    class Meta:
        verbose_name = "Pai/Encarregado"
        verbose_name_plural = "Pais/Encarregados"
    
    def __str__(self):
        return self.nome_completo
