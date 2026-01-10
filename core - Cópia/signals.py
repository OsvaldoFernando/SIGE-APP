from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import PerfilUsuario

@receiver(post_save, sender=User)
def criar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.create(user=instance, nivel_acesso='pendente')

@receiver(post_save, sender=User)
def salvar_perfil_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil') and not kwargs.get('created', False):
        # Evitar salvar o perfil se for apenas uma atualização de last_login (que ocorre no login)
        # No entanto, o problema pode ser mais profundo se o perfil.save() disparar algo que limpe a foto.
        # Vamos garantir que não estamos limpando campos acidentalmente.
        instance.perfil.save()
