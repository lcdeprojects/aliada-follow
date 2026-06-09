from django.urls import path
from . import views

urlpatterns = [
    path('', views.lead_dashboard, name='lead_dashboard'),
    path('leads/update/', views.update_lead_status, name='update_lead_status'),
    path('leads/add/', views.add_lead, name='add_lead'),
    path('leads/delete/<int:lead_id>/', views.delete_lead, name='delete_lead'),
    path('leads/message/add/', views.add_message, name='add_message'),
]
