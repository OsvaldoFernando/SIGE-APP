from .models import AnoAcademico, Subscricao

def subscricao_context(request):
    if not request.user.is_authenticated:
        return {}
    subscricao = Subscricao.objects.filter(estado__in=['ativo', 'teste']).first()
    return {'subscricao': subscricao}

def global_academic_context(request):
    if not request.user.is_authenticated:
        return {}
    
    ano_atual = AnoAcademico.objects.filter(ativo=True).first()
    semestre_atual = None
    if ano_atual:
        semestre_atual = ano_atual.semestres.filter(ativo=True).first()
        
    return {
        'ano_atual': ano_atual,
        'semestre_atual': semestre_atual
    }
