from .models import AnoAcademico, Subscricao, ConfiguracaoEscola, PerfilUsuario

def subscricao_context(request):
    if not request.user.is_authenticated:
        return {}
    subscricao = Subscricao.objects.filter(estado__in=['ativo', 'teste']).first()
    return {'subscricao': subscricao}

def global_academic_context(request):
    config = ConfiguracaoEscola.objects.first()
    
    context = {
        'config': config
    }
    
    if request.user.is_authenticated:
        # Tenta obter o ano acadêmico da sessão ou o padrão atual
        ano_id = request.session.get('ano_academico_id')
        if ano_id:
            ano_atual = AnoAcademico.objects.filter(id=ano_id).first()
        else:
            ano_atual = AnoAcademico.get_atual()
            if ano_atual:
                request.session['ano_academico_id'] = ano_atual.id
                
        semestre_atual = None
        if ano_atual:
            semestre_atual = ano_atual.semestres.filter(ativo=True).first()
            
        perfil = PerfilUsuario.objects.filter(user=request.user).first()
        
        context.update({
            'ano_atual': ano_atual,
            'semestre_atual': semestre_atual,
            'user_perfil': perfil
        })
        
    return context
