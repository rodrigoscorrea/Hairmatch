from django.core.management.base import BaseCommand
from preferences.models import Preferences

class Command(BaseCommand):
    help = 'Populates the preferences table with initial data if empty'

    def handle(self, *args, **kwargs):
        if Preferences.objects.exists():
            self.stdout.write(self.style.SUCCESS('Preferences are already populated. Skipping.'))
            return

        # List of preferences to add
        preferences = [
            "Coloração", "Cachos", "Barbearia", "Tranças", "Undercut",
            "Alisamento", "Corte Social", "Fade", "Platinado",
            "Corte Long Bob", "Luzes", "Corte em Camadas", "Hidratação",
            "Razor Part", "Chanel", "Mullet", "Wolf Cut"
        ]

        # Create preferences in bulk
        preference_objects = [
            Preferences(name=name, picture="minha-imagem.jpg") for name in preferences
        ]
        
        Preferences.objects.bulk_create(preference_objects)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully added {len(preferences)} preferences to the database')
        )