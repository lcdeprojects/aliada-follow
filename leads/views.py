from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
import json
import requests
import re

from .models import Lead, StatusHistory, Message

def lead_dashboard(request):
    leads = Lead.objects.filter(is_active=True).prefetch_related('messages')
    
    count_human = leads.filter(handled_by='human').count()
    count_ai = leads.filter(handled_by='ai').count()
    count_total = leads.count()
    
    status_choices = Lead.STATUS_CHOICES
    
    context = {
        'leads': leads,
        'count_human': count_human,
        'count_ai': count_ai,
        'count_total': count_total,
        'status_choices': status_choices,
    }
    return render(request, 'leads/dashboard.html', context)


@require_POST
def update_lead_status(request):
    try:
        # Support JSON payloads for API/fetch requests
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        lead_id = data.get('lead_id')
        new_status = data.get('status')
        handled_by = data.get('handled_by')
        
        if not lead_id:
            return JsonResponse({'success': False, 'error': 'ID do lead ausente.'}, status=400)
            
        lead = Lead.objects.get(id=lead_id)
        
        updated = False
        if new_status and lead.status != new_status:
            old_status = lead.status
            lead.status = new_status
            lead.followup_stage = 0
            lead.last_followup_at = None
            
            changed_by = request.user if request.user.is_authenticated else None
            StatusHistory.objects.create(
                lead=lead,
                old_status=old_status,
                new_status=new_status,
                changed_by=changed_by
            )
            updated = True
            
        if handled_by and lead.handled_by != handled_by:
            lead.handled_by = handled_by
            updated = True
            
            # Sincronizar label com o Chatwoot
            if lead.chatwoot_conversation_id:
                cw_url = f"{settings.CHATWOOT_API_URL}/api/v1/accounts/{settings.CHATWOOT_ACCOUNT_ID}/conversations/{lead.chatwoot_conversation_id}/labels"
                headers = {
                    "api_access_token": settings.CHATWOOT_API_TOKEN,
                    "Content-Type": "application/json"
                }
                label_to_add = "atendimento_ia" if handled_by == "ai" else "atendimento_humano"
                try:
                    requests.post(cw_url, headers=headers, json={"labels": [label_to_add]}, timeout=5)
                except Exception as e:
                    print(f"Erro ao sincronizar labels: {e}")
            
        if updated:
            lead.save()
            
        return JsonResponse({'success': True})
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def add_lead(request):
    try:
        if request.method == 'POST':
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            status = request.POST.get('status', 'atendimento')
            handled_by = request.POST.get('handled_by', 'human')
            is_active = request.POST.get('is_active', True)
            
            if name and phone:
                # Standardize phone number format (remove non-digits or keep simple)
                clean_phone = ''.join(filter(str.isdigit, phone))
                
                # Get or create lead by phone number
                lead, created = Lead.objects.get_or_create(
                    phone=clean_phone,
                    defaults={'name': name, 'status': status, 'handled_by': handled_by}
                )
                
                if not created:
                    # If lead already exists, just update name and status
                    lead.name = name
                    lead.handled_by = handled_by
                    old_status = lead.status
                    if old_status != status:
                        lead.status = status
                        lead.followup_stage = 0
                        lead.last_followup_at = None
                        lead.is_active = True
                        lead.save()
                        StatusHistory.objects.create(
                            lead=lead,
                            old_status=old_status,
                            new_status=status,
                            changed_by=request.user if request.user.is_authenticated else None
                        )
                    else:
                        lead.save()
                        
            return redirect('lead_dashboard')
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)\

def delete_lead(request, lead_id):
    try:
        lead = Lead.objects.get(id=lead_id)
        lead.is_active = False
        lead.save()
        return JsonResponse({'success': True})
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def add_message(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        lead_id = data.get('lead_id')
        content = data.get('content')
        direction = data.get('direction')

        if not lead_id or not content or not direction:
            return JsonResponse({'success': False, 'error': 'Parâmetros ausentes.'}, status=400)

        if direction == 'out':
            direction = 'out_human'

        lead = Lead.objects.get(id=lead_id)
        msg = Message.objects.create(
            lead=lead,
            direction=direction,
            content=content
        )
        
        cw_status = None
        cw_error = None
        
        # Enviar para Chatwoot API se for mensagem de saída (agente) e o lead tiver conversa vinculada
        if direction == 'out' and lead.chatwoot_conversation_id:
            cw_url = f"{settings.CHATWOOT_API_URL}/api/v1/accounts/{settings.CHATWOOT_ACCOUNT_ID}/conversations/{lead.chatwoot_conversation_id}/messages"
            headers = {
                "api_access_token": settings.CHATWOOT_API_TOKEN,
                "Content-Type": "application/json"
            }
            payload = {
                "content": content,
                "message_type": "outgoing",
                "private": False
            }
            try:
                # O timeout previne que o CRM trave se o Chatwoot demorar
                response = requests.post(cw_url, headers=headers, json=payload, timeout=5)
                cw_status = response.status_code
                if not response.ok:
                    cw_error = response.text
                    print(f"Chatwoot recusou: {cw_status} - {cw_error}")
            except Exception as e:
                cw_error = str(e)
                print(f"Erro ao enviar para Chatwoot: {e}")
        
        from django.utils.timezone import localtime
        return JsonResponse({
            'success': True,
            'message': {
                'direction': msg.direction,
                'content': msg.content,
                'created_at': localtime(msg.created_at).strftime('%d/%m/%Y %H:%M')
            },
            'debug_chatwoot': {
                'conversation_id': lead.chatwoot_conversation_id,
                'status': cw_status,
                'error': cw_error
            }
        })
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def chatwoot_webhook(request):
    try:
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'message_created':
            message_type = payload.get('message_type') # 'incoming' (paciente) ou 'outgoing' (agente)
            content = payload.get('content')
            conversation = payload.get('conversation', {})
            sender = payload.get('sender', {})
            
            conversation_id = conversation.get('id')
            
            # O contato real da conversa sempre está no meta.sender (evita pegar o nome do atendente em msgs outgoing)
            contact = conversation.get('meta', {}).get('sender', {})
            
            phone_number = contact.get('phone_number')
            contact_name = contact.get('name')
            
            # Fallback caso não venha no meta
            if not phone_number:
                phone_number = sender.get('phone_number')
                contact_name = sender.get('name')
                
            if not phone_number:
                return JsonResponse({'success': True, 'msg': 'Sem telefone ignorado'})
                
            # Limpar telefone
            clean_phone = ''.join(filter(str.isdigit, str(phone_number)))
            if not clean_phone:
                return JsonResponse({'success': True})
                
            # Definir nome final
            final_name = contact_name if contact_name else f'Contato {clean_phone}'
                
            # Buscar ou criar Lead
            lead, created = Lead.objects.get_or_create(
                phone__endswith=clean_phone[-10:], # Busca aproximada caso venha com DDI
                defaults={'name': final_name, 'phone': clean_phone}
            )
            
            # Atualizar IDs do Chatwoot no Lead
            if lead.chatwoot_conversation_id != conversation_id:
                lead.chatwoot_conversation_id = conversation_id
                contact_id = sender.get('id') if sender.get('type') == 'contact' else None
                if contact_id:
                    lead.chatwoot_contact_id = contact_id
                lead.save()
                
            # Se for um Lead novo, garantir que a etiqueta no Chatwoot fique como "atendimento_humano"
            if created and conversation_id:
                cw_url = f"{settings.CHATWOOT_API_URL}/api/v1/accounts/{settings.CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/labels"
                headers = {
                    "api_access_token": settings.CHATWOOT_API_TOKEN,
                    "Content-Type": "application/json"
                }
                try:
                    requests.post(cw_url, headers=headers, json={"labels": ["atendimento_humano"]}, timeout=5)
                except Exception as e:
                    pass
                
            # Salvar mensagem no nosso DB
            # Se for message_type = template ou campaign, também é outgoing
            direction = 'in' if message_type == 'incoming' else 'out'
            if direction == 'out':
                direction = 'out_ai' if lead.handled_by == 'ai' else 'out_human'
            
            # Evitar duplicar caso o próprio CRM enviou e gerou webhook
            if not Message.objects.filter(lead=lead, content=content, direction=direction).exists():
                # Para evitar duplicar mensagens 'out' antigas com as novas 'out_human', verifica só pelo content e lead nos últimos segundos idealmente, mas assim serve
                Message.objects.create(
                    lead=lead,
                    content=content,
                    direction=direction
                )
                
            # Se recebemos mensagem do paciente (in), mover para a IA (caso de automação externa) ou manter
            # Isso pode ser ajustado conforme a regra de negócios
            
        return JsonResponse({'success': True})
    except Exception as e:
        print(f"Erro Webhook Chatwoot: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def active_leads_json(request):
    leads = Lead.objects.filter(is_active=True).prefetch_related('messages')
    data = []
    for lead in leads:
        last_msg = lead.messages.all().last()
        from django.utils.timezone import localtime
        data.append({
            'id': lead.id,
            'status': lead.status,
            'handled_by': lead.handled_by,
            'last_preview': last_msg.content if last_msg else '',
            'last_direction': last_msg.direction if last_msg else '',
            'messages': json.loads(lead.messages_json()),
            'last_interaction': localtime(lead.last_interaction).strftime('%d/%m %H:%M')
        })
    return JsonResponse({'leads': data})