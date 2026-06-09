import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinic_manager.settings')
django.setup()

from django.db import connection
from leads.models import Message

print("Verificando se a tabela leads_message existe...")
if 'leads_message' not in connection.introspection.table_names():
    print("Tabela leads_message não encontrada! Criando tabela...")
    with connection.schema_editor() as schema_editor:
        schema_editor.create_model(Message)
    print("Tabela leads_message criada com sucesso!")
else:
    print("A tabela leads_message já existe.")
