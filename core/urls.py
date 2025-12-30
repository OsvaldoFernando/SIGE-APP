from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_redirect, name='index_redirect'),
    path('painel/', views.index, name='painel_principal'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('inscricao/<int:curso_id>/', views.inscricao_create, name='inscricao_create'),
    path('inscricao/<int:inscricao_id>/pdf/', views.gerar_pdf_inscricao, name='gerar_pdf_inscricao'),
    path('minha-conta/', views.minha_conta, name='minha_conta'),
    path('pagamento/', views.pagamento_subscription, name='pagamento_subscription'),
    path('documentos/', views.gestao_documentos, name='gestao_documentos'),
    path('documentos/novo/', views.documento_criar, name='documento_criar'),
    path('documentos/<int:doc_id>/editar/', views.documento_editar, name='documento_editar'),
    path('documentos/<int:doc_id>/deletar/', views.documento_deletar, name='documento_deletar'),
    path('documentos/<int:doc_id>/visualizar/', views.documento_visualizar, name='documento_visualizar'),
    path('documentos/<int:doc_id>/pdf/', views.gerar_pdf_documento, name='gerar_pdf_documento'),
    
    # URLs para Gestão de Cursos
    path('cursos/', views.listar_cursos, name='listar_cursos'),
    path('cursos/novo/', views.criar_curso, name='criar_curso'),
    path('cursos/<int:curso_id>/', views.detalhe_curso, name='detalhe_curso'),
    path('cursos/<int:curso_id>/editar/', views.editar_curso, name='editar_curso'),
    path('cursos/<int:curso_id>/deletar/', views.deletar_curso, name='deletar_curso'),
    
    # URLs para Gestão de Utilizadores
    path('utilizadores/', views.listar_utilizadores, name='listar_utilizadores'),
    path('utilizadores/novo/', views.criar_utilizador, name='criar_utilizador'),
    path('utilizadores/<int:user_id>/editar/', views.editar_utilizador, name='editar_utilizador'),
    path('utilizadores/<int:user_id>/deletar/', views.deletar_utilizador, name='deletar_utilizador'),
    # URLs para Anos Académicos
    path('anos-academicos/', views.ano_academico_lista, name='ano_academico_lista'),
    path('anos-academicos/novo/', views.ano_academico_create, name='ano_academico_create'),
    path('anos-academicos/<int:pk>/editar/', views.ano_academico_edit, name='ano_academico_edit'),
    
    # URLs para Menus do Painel Principal
    path('admissao-estudantes/', views.admissao_estudantes, name='admissao_estudantes'),
    path('assiduidade/', views.assiduidade, name='assiduidade'),
    path('assiduidade-docentes/', views.assiduidade_docentes, name='assiduidade_docentes'),
    path('atribuicao-turmas/', views.atribuicao_turmas, name='atribuicao_turmas'),
    path('bolsas-beneficios/', views.bolsas_beneficios, name='bolsas_beneficios'),
    path('cronograma-academico/', views.cronograma_academico, name='cronograma_academico'),
    path('cursos-disciplinas/', views.cursos_disciplinas, name='cursos_disciplinas'),
    path('departamentos/', views.departamentos, name='departamentos'),
    path('faturas-pagamentos/', views.faturas_pagamentos, name='faturas_pagamentos'),
    path('gestao-eventos/', views.gestao_eventos, name='gestao_eventos'),
    path('gestao-financeira/', views.gestao_financeira, name='gestao_financeira'),
    path('grelha-curricular/', views.grelha_curricular, name='grelha_curricular'),
    path('lista-estudantes/', views.lista_estudantes, name='lista_estudantes'),
    path('matricula/', views.matricula, name='matricula'),
    path('notificacoes/', views.notificacoes_view, name='notificacoes'),
    path('quadro-avisos/', views.quadro_avisos, name='quadro_avisos'),
    path('recursos-humanos/', views.recursos_humanos, name='recursos_humanos'),
    path('relatorios-financeiros/', views.relatorios_financeiros, name='relatorios_financeiros'),
]
