from django.core.management.base import BaseCommand
from leads.models import Lead, Message
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Seeds mock data for testing the leads dashboard'

    def handle(self, *args, **kwargs):
        self.stdout.write('Esvaziando banco de dados para o seed...')
        Message.objects.all().delete()
        Lead.objects.all().delete()

        # Mock Leads Data
        leads_data = [
            {
                'name': 'Dr. Marcos Oliveira',
                'phone': '11988887777',
                'status': 'atendimento',
                'messages': [
                    ('in', 'Olá, gostaria de saber o valor da consulta para dermatologia.'),
                    ('out', 'Olá! O valor da consulta é R$ 350. Gostaria de agendar para esta semana?'),
                    ('in', 'Tenho preferência por quinta-feira à tarde.'),
                ]
            },
            {
                'name': 'Ana Julia Ramos',
                'phone': '21977776666',
                'status': 'aguardando_decisao',
                'messages': [
                    ('in', 'Vocês aceitam o convênio Bradesco Saúde?'),
                    ('out', 'Olá Ana! Sim, aceitamos Bradesco Saúde para consultas eletivas.'),
                    ('in', 'Ah perfeito. Vou verificar com meu marido e já retorno com a data.'),
                ]
            },
            {
                'name': 'Carlos Henrique',
                'phone': '31966665555',
                'status': 'agendado',
                'messages': [
                    ('in', 'Gostaria de marcar uma consulta com o Dr. Fabio (Cardiologista).'),
                    ('out', 'Olá Carlos! Temos horário disponível na terça às 14h ou quinta às 10h. Qual prefere?'),
                    ('in', 'Terça às 14h está ótimo.'),
                    ('out', 'Consulta confirmada para terça-feira às 14:00. Enviamos as instruções de preparo no e-mail.'),
                ]
            },
            {
                'name': 'Juliana Costa',
                'phone': '41955554444',
                'status': 'perdido',
                'messages': [
                    ('in', 'Tem consulta de retorno hoje?'),
                    ('out', 'Olá Juliana! Hoje estamos sem vagas de encaixe. Podemos agendar para amanhã às 8h?'),
                    # Silêncio por dias
                ]
            },
            {
                'name': 'Roberto Souza',
                'phone': '19944443333',
                'status': 'reativacao',
                'messages': [
                    ('in', 'Olá, fiz um procedimento com vocês ano passado e queria agendar o retorno de rotina.'),
                    # Silêncio antigo
                ]
            }
        ]

        self.stdout.write('Semeando Leads e Histórico de Mensagens...')
        now = timezone.now()

        for lead_info in leads_data:
            lead = Lead.objects.create(
                name=lead_info['name'],
                phone=lead_info['phone'],
                status=lead_info['status']
            )
            
            # Create messages with staggered times
            for i, (direction, content) in enumerate(lead_info['messages']):
                message_time = now - timedelta(hours=len(lead_info['messages']) - i)
                msg = Message.objects.create(
                    lead=lead,
                    direction=direction,
                    content=content
                )
                # Hack to override auto_now_add for ordering testing
                Message.objects.filter(id=msg.id).update(created_at=message_time)
            
            # Stagger last_interaction
            Lead.objects.filter(id=lead.id).update(last_interaction=now - timedelta(days=2 if lead.status == 'aguardando_decisao' else 0))

        self.stdout.write(self.style.SUCCESS('Dados semeados com sucesso!'))
