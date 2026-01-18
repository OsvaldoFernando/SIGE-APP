from .models import AnoAcademico, Subscricao, ConfiguracaoEscola, PerfilUsuario

def subscricao_context(request):
    if not request.user.is_authenticated:
        return {}
    subscricao = Subscricao.objects.filter(estado__in=['ativo', 'teste']).first()
    return {'subscricao': subscricao}

def global_academic_context(request):
    from .models import EventoCalendario, Notificacao, AnoAcademico
    config = ConfiguracaoEscola.objects.first()
    
    context = {
        'config': config,
        'eventos_ticker': [],
        'ano_atual': None
    }
    
    if request.user.is_authenticated:
        # Busca o ano marcado como atual no banco de dados (ignorando sessões)
        ano_atual = AnoAcademico.objects.filter(ano_atual=True).first()
                
        semestre_atual = None
        eventos_ticker = []
        if ano_atual:
            semestre_atual = ano_atual.semestres.filter(ativo=True).first()
            # Busca TODOS os eventos ativos que pertencem ao ano marcado como ATUAL
            eventos_ticker = EventoCalendario.objects.filter(
                ano_lectivo=ano_atual,
                estado='ATIVO'
            ).order_by('data_inicio')
            
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        notificacoes_recentes = Notificacao.objects.filter(ativa=True).order_by('-data_criacao')[:5]
        
        context.update({
            'ano_atual': ano_atual,
            'semestre_atual': semestre_atual,
            'user_perfil': perfil,
            'eventos_ticker': eventos_ticker,
            'notificacoes_recentes': notificacoes_recentes
        })
        
    return context
