from django.db import models
from django.contrib.auth.models import User
from django.utils.timezone import localtime
import json

class Lead(models.Model):
    STATUS_CHOICES = [
        ('atendimento', 'Em Atendimento'),
        ('aguardando_decisao', 'Aguardando Decisão'),
        ('agendado', 'Agendado'),
        ('perdido', 'Perdido'),
        ('reativacao', 'Reativação'),
    ]

    name = models.CharField(max_length=255, verbose_name="Nome do Paciente")
    phone = models.CharField(max_length=50, unique=True, verbose_name="Telefone/WhatsApp")
    status = models.CharField(
        max_length=50, 
        choices=STATUS_CHOICES, 
        default='atendimento',
        verbose_name="Status"
    )
    last_interaction = models.DateTimeField(auto_now=True, verbose_name="Última Interação")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Colunas de controle contra duplicidade de follow-ups
    followup_stage = models.IntegerField(default=0, verbose_name="Estágio de Follow-Up")
    last_followup_at = models.DateTimeField(null=True, blank=True, verbose_name="Último Follow-Up em")

    class Meta:
        ordering = ['-last_interaction']
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def messages_json(self):
        msgs = self.messages.all()
        data = []
        for m in msgs:
            data.append({
                'direction': m.direction,
                'content': m.content,
                'created_at': localtime(m.created_at).strftime('%d/%m/%Y %H:%M')
            })
        return json.dumps(data)

    @property
    def last_message(self):
        return self.messages.all().last()

    def __str__(self):
        return f"{self.name} ({self.phone}) - {self.get_status_display()}"


class Message(models.Model):
    DIRECTION_CHOICES = [
        ('in', 'Recebida (Paciente)'),
        ('out', 'Enviada (Clínica/IA)'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='messages', verbose_name="Lead")
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, verbose_name="Direção")
    content = models.TextField(verbose_name="Conteúdo de Mensagem")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Enviada em")

    class Meta:
        ordering = ['created_at']
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"

    def __str__(self):
        dir_str = "←" if self.direction == 'in' else "→"
        return f"{dir_str} {self.lead.name}: {self.content[:50]}"


class StatusHistory(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='status_histories', verbose_name="Lead")
    old_status = models.CharField(max_length=50, choices=Lead.STATUS_CHOICES, verbose_name="Status Anterior")
    new_status = models.CharField(max_length=50, choices=Lead.STATUS_CHOICES, verbose_name="Novo Status")
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name="Alterado em")
    changed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name="Alterado por"
    )

    class Meta:
        ordering = ['-changed_at']
        verbose_name = "Histórico de Status"
        verbose_name_plural = "Históricos de Status"

    def __str__(self):
        return f"{self.lead.name}: {self.old_status} → {self.new_status} em {self.changed_at.strftime('%d/%m/%Y %H:%M')}"
