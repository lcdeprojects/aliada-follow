from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json

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

        lead = Lead.objects.get(id=lead_id)
        msg = Message.objects.create(
            lead=lead,
            direction=direction,
            content=content
        )
        
        from django.utils.timezone import localtime
        return JsonResponse({
            'success': True,
            'message': {
                'direction': msg.direction,
                'content': msg.content,
                'created_at': localtime(msg.created_at).strftime('%d/%m/%Y %H:%M')
            }
        })
    except Lead.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lead não encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)