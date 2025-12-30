from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class AnoAcademico(models.Model):
    STATUS_CHOICES = [
        ('ativo', 'Ativo'),
        ('encerrado', 'Encerrado'),
    ]
    ano_inicio = models.IntegerField(verbose_name="Ano de Início")
    ano_fim = models.IntegerField(verbose_name="Ano de Fim")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ativo', verbose_name="Status")
    ativo = models.BooleanField(default=False, verbose_name="Ano Atual")
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Ano Académico"
        verbose_name_plural = "Anos Académicos"
        ordering = ['-ano_inicio']
        unique_together = ['ano_inicio', 'ano_fim']
    
    def __str__(self):
        return f"{self.ano_inicio}/{self.ano_fim}"
    
    def save(self, *args, **kwargs):
        if self.ativo:
            AnoAcademico.objects.exclude(pk=self.pk).update(ativo=False)
        super().save(*args, **kwargs)

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

class Curso(models.Model):
    GRAU_CHOICES = [
        ('licenciatura', 'Licenciatura'),
        ('mestrado', 'Mestrado'),
        ('doutoramento', 'Doutoramento'),
        ('especialidade', 'Especialidade'),
    ]
    
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
    grau = models.CharField(max_length=20, choices=GRAU_CHOICES, default='licenciatura', verbose_name="Grau")
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
    
    class Meta:
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"
    
    def vagas_disponiveis(self):
        aprovados = self.inscricoes.filter(aprovado=True).count()
        return max(0, self.vagas - aprovados)
    
    def total_inscricoes(self):
        return self.inscricoes.count()
    
    def get_duracao_display_full(self):
        return f"{self.get_duracao_meses_display()}"

class Disciplina(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='disciplinas', verbose_name="Curso")
    nome = models.CharField(max_length=200, verbose_name="Nome da Disciplina")
    carga_horaria = models.PositiveIntegerField(verbose_name="Carga Horária (horas)", default=40)
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    codigo = models.CharField(max_length=50, blank=True, verbose_name="Código da Disciplina")
    
    class Meta:
        verbose_name = "Disciplina"
        verbose_name_plural = "Disciplinas"
        ordering = ['curso', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {self.curso.nome}"

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
    
    # 1. Informações Pessoais
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    local_nascimento = models.CharField(max_length=200, verbose_name="Local de Nascimento", default="Luanda")
    nacionalidade = models.CharField(max_length=100, verbose_name="Nacionalidade", default="Angolana")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Número do Bilhete de Identidade")
    data_validade_bi = models.DateField(verbose_name="Data de Validade do BI", null=True, blank=True)
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], verbose_name="Sexo")
    estado_civil = models.CharField(max_length=1, choices=ESTADO_CIVIL_CHOICES, default='S', verbose_name="Estado Civil")
    endereco = models.TextField(verbose_name="Endereço Completo")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="Email")
    
    # 2. Informações Académicas
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='inscricoes', verbose_name="Última Escola Frequentada")
    ano_conclusao = models.CharField(max_length=4, verbose_name="Ano de Conclusão", default="2024")
    certificados_obtidos = models.TextField(verbose_name="Certificados/Diplomas Obtidos", blank=True, default="")
    historico_escolar = models.TextField(verbose_name="Notas/Histórico Escolar", blank=True, default="")
    turno_preferencial = models.CharField(max_length=1, choices=TURNO_CHOICES, verbose_name="Turno Preferencial", default='M')
    
    # 3. Informações Financeiras
    numero_comprovante = models.CharField(max_length=100, verbose_name="Número do Comprovante/Boleto", blank=True)
    responsavel_financeiro_nome = models.CharField(max_length=200, verbose_name="Nome do Responsável Financeiro", blank=True)
    responsavel_financeiro_telefone = models.CharField(max_length=20, verbose_name="Telefone do Responsável Financeiro", blank=True)
    responsavel_financeiro_relacao = models.CharField(max_length=100, verbose_name="Relação com o Estudante", blank=True)
    
    # 4. Encarregado de Educação
    encarregado_nome = models.CharField(max_length=200, verbose_name="Nome do Encarregado de Educação", blank=True)
    encarregado_parentesco = models.CharField(max_length=100, verbose_name="Grau de Parentesco", blank=True)
    encarregado_telefone = models.CharField(max_length=20, verbose_name="Telefone do Encarregado", blank=True)
    encarregado_email = models.EmailField(verbose_name="Email do Encarregado", blank=True)
    encarregado_profissao = models.CharField(max_length=200, verbose_name="Profissão do Encarregado", blank=True)
    encarregado_local_trabalho = models.CharField(max_length=200, verbose_name="Local de Trabalho do Encarregado", blank=True)
    
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
    
    def __str__(self):
        return f"{self.numero_inscricao} - {self.nome_completo}"
    
    def save(self, *args, **kwargs):
        if not self.numero_inscricao:
            ultimo = Inscricao.objects.order_by('-id').first()
            if ultimo:
                numero = int(ultimo.numero_inscricao.split('-')[1]) + 1
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

class Professor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Bilhete de Identidade")
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")
    sexo = models.CharField(max_length=1, choices=[('M', 'Masculino'), ('F', 'Feminino')], verbose_name="Sexo")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(verbose_name="Email")
    endereco = models.TextField(verbose_name="Endereço")
    especialidade = models.CharField(max_length=200, verbose_name="Especialidade")
    data_contratacao = models.DateField(verbose_name="Data de Contratação", default=timezone.now)
    
    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"
        ordering = ['nome_completo']
    
    def __str__(self):
        return self.nome_completo

class Turma(models.Model):
    nome = models.CharField(max_length=100, verbose_name="Nome da Turma")
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='turmas', verbose_name="Curso")
    ano_letivo = models.CharField(max_length=9, verbose_name="Ano Letivo (ex: 2024/2025)")
    professor_titular = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Professor Titular")
    
    class Meta:
        verbose_name = "Turma"
        verbose_name_plural = "Turmas"
        ordering = ['ano_letivo', 'nome']
    
    def __str__(self):
        return f"{self.nome} - {self.curso.nome} ({self.ano_letivo})"

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
                numero = int(ultimo.numero_estudante.split('-')[1]) + 1
            else:
                numero = 1
            self.numero_estudante = f"ALU-{numero:06d}"
        super().save(*args, **kwargs)

class Pai(models.Model):
    nome_completo = models.CharField(max_length=200, verbose_name="Nome Completo")
    bilhete_identidade = models.CharField(max_length=50, verbose_name="Bilhete de Identidade")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    email = models.EmailField(blank=True, verbose_name="Email")
    endereco = models.TextField(verbose_name="Endereço")
    parentesco = models.CharField(max_length=50, verbose_name="Parentesco (Pai, Mãe, Tutor, etc.)")
    alunos = models.ManyToManyField(Aluno, related_name='pais', verbose_name="Alunos")
    
    class Meta:
        verbose_name = "Pai/Responsável"
        verbose_name_plural = "Pais/Responsáveis"
        ordering = ['nome_completo']
    
    def __str__(self):
        return f"{self.nome_completo} ({self.parentesco})"

class PerfilUsuario(models.Model):
    NIVEL_ACESSO_CHOICES = [
        ('pendente', 'Pendente de Aprovação'),
        ('super_admin', 'Super Administrador'),
        ('admin', 'Administrador'),
        ('secretaria', 'Secretaria'),
        ('secretario_academico', 'Secretário Académico'),
        ('daac', 'Chefe de Departamento para Assuntos Académico (DAAC)'),
        ('financeiro', 'Responsável Financeiro'),
        ('bibliotecario', 'Bibliotecário'),
        ('rh', 'Gestor de Recursos Humanos'),
        ('professor', 'Docente (Professor)'),
        ('coordenador', 'Coordenador'),
        ('aluno', 'Aluno'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil', verbose_name="Usuário")
    nivel_acesso = models.CharField(
        max_length=20,
        choices=NIVEL_ACESSO_CHOICES,
        default='pendente',
        verbose_name="Nível de Acesso"
    )
    telefone = models.CharField(max_length=20, blank=True, verbose_name="Telefone")
    foto = models.ImageField(upload_to='usuarios/', blank=True, null=True, verbose_name="Foto")
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name="Data de Cadastro")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    
    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"
        ordering = ['user__username']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_nivel_acesso_display()}"

class Notificacao(models.Model):
    TIPO_CHOICES = [
        ('info', 'Informação'),
        ('aviso', 'Aviso'),
        ('urgente', 'Urgente'),
        ('sucesso', 'Sucesso'),
    ]
    
    titulo = models.CharField(max_length=200, verbose_name="Título")
    mensagem = models.TextField(verbose_name="Mensagem")
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='info',
        verbose_name="Tipo"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    destinatarios = models.ManyToManyField(
        User,
        related_name='notificacoes',
        verbose_name="Destinatários",
        blank=True
    )
    lida_por = models.ManyToManyField(
        User,
        related_name='notificacoes_lidas',
        verbose_name="Lida por",
        blank=True
    )
    global_notificacao = models.BooleanField(
        default=False,
        verbose_name="Notificação Global",
        help_text="Se marcado, todos os usuários verão esta notificação"
    )
    ativa = models.BooleanField(default=True, verbose_name="Ativa")
    
    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.titulo} - {self.get_tipo_display()}"
    
    def marcar_como_lida(self, usuario):
        self.lida_por.add(usuario)
    
    def esta_lida(self, usuario):
        return self.lida_por.filter(id=usuario.id).exists()

class Subscricao(models.Model):
    PLANO_CHOICES = [
        ('mensal', 'Mensal'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]
    
    ESTADO_CHOICES = [
        ('ativo', 'Ativo'),
        ('expirado', 'Expirado'),
        ('cancelado', 'Cancelado'),
        ('teste', 'Período de Teste'),
    ]
    
    nome_escola = models.CharField(max_length=200, verbose_name="Nome da Escola", unique=True)
    plano = models.CharField(
        max_length=20,
        choices=PLANO_CHOICES,
        default='mensal',
        verbose_name="Plano"
    )
    data_inicio = models.DateField(verbose_name="Data de Início")
    data_expiracao = models.DateField(verbose_name="Data de Expiração")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='teste',
        verbose_name="Estado"
    )
    valor_pago = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name="Valor Pago"
    )
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Subscrição"
        verbose_name_plural = "Subscrições"
        ordering = ['-data_inicio']
    
    def __str__(self):
        return f"{self.nome_escola} - {self.get_plano_display()}"
    
    def dias_restantes(self):
        """Calcula quantos dias faltam para expirar"""
        from datetime import date
        if self.data_expiracao:
            delta = self.data_expiracao - date.today()
            return max(0, delta.days)
        return 0
    
    def esta_ativo(self):
        """Verifica se a subscrição está ativa"""
        from datetime import date
        return self.estado in ['ativo', 'teste'] and self.data_expiracao >= date.today()
    
    def percentual_usado(self):
        """Retorna o percentual de tempo usado da subscrição"""
        from datetime import date
        if self.data_inicio and self.data_expiracao:
            total_dias = (self.data_expiracao - self.data_inicio).days
            dias_passados = (date.today() - self.data_inicio).days
            if total_dias > 0:
                return min(100, int((dias_passados / total_dias) * 100))
        return 0

class PagamentoSubscricao(models.Model):
    """Modelo para registrar pagamentos de renovação de subscrição"""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    
    subscricao = models.ForeignKey(
        Subscricao,
        on_delete=models.CASCADE,
        related_name='pagamentos',
        verbose_name="Subscrição"
    )
    plano_escolhido = models.CharField(
        max_length=20,
        choices=Subscricao.PLANO_CHOICES,
        default='mensal',
        verbose_name="Plano Escolhido"
    )
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Valor Pago"
    )
    comprovante = models.FileField(
        upload_to='comprovantes/',
        verbose_name="Comprovante de Pagamento"
    )
    numero_referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Número de Referência"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Status"
    )
    data_pagamento = models.DateField(verbose_name="Data do Pagamento")
    data_submissao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Submissão")
    observacoes = models.TextField(blank=True, verbose_name="Observações")
    
    aprovado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pagamentos_aprovados',
        verbose_name="Aprovado Por"
    )
    data_aprovacao = models.DateTimeField(null=True, blank=True, verbose_name="Data de Aprovação")
    recibo_pdf = models.FileField(
        upload_to='recibos/',
        null=True,
        blank=True,
        verbose_name="Recibo PDF"
    )
    
    class Meta:
        verbose_name = "Pagamento de Subscrição"
        verbose_name_plural = "Pagamentos de Subscrição"
        ordering = ['-data_submissao']
    
    def __str__(self):
        return f"Pagamento {self.id} - {self.subscricao.nome_escola} - {self.get_status_display()}"

class RecuperacaoSenha(models.Model):
    """Modelo para gerenciar recuperação de senha via email ou telefone"""
    TIPO_CHOICES = [
        ('email', 'Email'),
        ('telefone', 'Telefone'),
    ]
    
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='recuperacoes_senha',
        verbose_name="Usuário"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name="Tipo de Recuperação"
    )
    codigo_otp = models.CharField(
        max_length=6,
        blank=True,
        verbose_name="Código OTP"
    )
    token = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Token de Recuperação"
    )
    email_enviado = models.EmailField(blank=True, verbose_name="Email Enviado Para")
    telefone_enviado = models.CharField(max_length=20, blank=True, verbose_name="Telefone Enviado Para")
    usado = models.BooleanField(default=False, verbose_name="Usado")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_expiracao = models.DateTimeField(verbose_name="Data de Expiração")
    
    class Meta:
        verbose_name = "Recuperação de Senha"
        verbose_name_plural = "Recuperações de Senha"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.user.username} - {self.get_tipo_display()} - {'Usado' if self.usado else 'Pendente'}"
    
    def esta_expirado(self):
        from django.utils import timezone
        return timezone.now() > self.data_expiracao
    
    def marcar_como_usado(self):
        self.usado = True
        self.save()

class Documento(models.Model):
    """Modelo para gerenciar templates de documentos com variáveis dinâmicas"""
    SECAO_CHOICES = [
        ('inscricao', 'Inscrição'),
        ('certificado', 'Certificado'),
        ('declaracao', 'Declaração'),
        ('atestado', 'Atestado'),
        ('diploma', 'Diploma'),
        ('historico', 'Histórico Escolar'),
        ('recibo', 'Recibo'),
        ('convite', 'Convite'),
        ('outra', 'Outra'),
    ]
    
    titulo = models.CharField(max_length=200, verbose_name="Título do Documento")
    secao = models.CharField(
        max_length=50,
        choices=SECAO_CHOICES,
        default='outra',
        verbose_name="Seção/Módulo"
    )
    conteudo = models.TextField(
        verbose_name="Conteúdo do Documento",
        help_text="Use variáveis como {nome}, {bilhete_identidade}, {email}, {telefone}, {data_nascimento}, {curso}, {numero_inscricao}, {data_inscricao}, {data_hoje}, {nome_escola}, etc."
    )
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    
    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"{self.titulo} ({self.get_secao_display()})"
    
    def obter_variaveis_disponiveis(self):
        """Retorna lista de variáveis disponíveis para este documento"""
        return {
            'nome': 'Nome completo',
            'bilhete_identidade': 'Número do Bilhete de Identidade',
            'email': 'Email',
            'telefone': 'Telefone',
            'data_nascimento': 'Data de Nascimento',
            'curso': 'Nome do Curso',
            'numero_inscricao': 'Número de Inscrição',
            'data_inscricao': 'Data de Inscrição',
            'data_hoje': 'Data Atual',
            'nome_escola': 'Nome da Escola',
            'endereco': 'Endereço',
            'sexo': 'Sexo',
            'estado_civil': 'Estado Civil',
            'nacionalidade': 'Nacionalidade',
            'local_nascimento': 'Local de Nascimento',
        }
    
    def renderizar(self, dados):
        """Renderiza o documento com os dados fornecidos"""
        conteudo = self.conteudo
        try:
            conteudo = conteudo.format(**dados)
        except KeyError as e:
            conteudo = f"Erro: Variável {e} não encontrada nos dados fornecidos."
        return conteudo
