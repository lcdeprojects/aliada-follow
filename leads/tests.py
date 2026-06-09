from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

from .models import Lead, Message, StatusHistory

class LeadModelTest(TestCase):
    def setUp(self):
        # Arrange
        self.lead = Lead.objects.create(
            name="Alice Smith",
            phone="11999991111",
            status="atendimento"
        )

    def test_lead_string_representation(self):
        # Act & Assert
        self.assertEqual(str(self.lead), "Alice Smith (11999991111) - Em Atendimento")


class LeadViewsTest(TestCase):
    def setUp(self):
        # Arrange
        self.client = Client()
        self.lead = Lead.objects.create(
            name="Bob Jones",
            phone="11999992222",
            status="atendimento"
        )
        self.user = User.objects.create_user(username='secretary', password='password123')

    def test_dashboard_view_status_code(self):
        # Act
        response = self.client.get(reverse('lead_dashboard'))
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'leads/dashboard.html')

    def test_update_lead_status_ajax(self):
        # Act
        response = self.client.post(
            reverse('update_lead_status'),
            data=json.dumps({
                'lead_id': self.lead.id,
                'status': 'aguardando_decisao'
            }),
            content_type='application/json'
        )
        
        # Assert
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify changes in DB
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, 'aguardando_decisao')
        
        # Verify history log was created
        history = StatusHistory.objects.filter(lead=self.lead).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.old_status, 'atendimento')
        self.assertEqual(history.new_status, 'aguardando_decisao')

    def test_add_lead_view(self):
        # Act
        response = self.client.post(
            reverse('add_lead'),
            data={
                'name': 'Charlie Brown',
                'phone': '11999993333',
                'status': 'agendado'
            }
        )
        
        # Assert
        self.assertRedirects(response, reverse('lead_dashboard'))
        
        # Verify creation in DB
        lead = Lead.objects.filter(phone='11999993333').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.name, 'Charlie Brown')
        self.assertEqual(lead.status, 'agendado')
