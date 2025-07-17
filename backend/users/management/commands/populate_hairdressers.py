import os
import random
from datetime import time

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.management.base import BaseCommand
from faker import Faker

from availability.models import Availability
from service.models import Service
from users.models import Hairdresser, User


class Command(BaseCommand):
    """
    Populates the database with 20 fake hairdressers if none exist,
    along with their availabilities and services.
    """

    help = "Populates the database with fake hairdressers"

    def handle(self, *args, **kwargs):
        if User.objects.filter(role="hairdresser").exists():
            self.stdout.write(
                self.style.SUCCESS(
                    "There are already hairdressers in the database. Skipping."
                )
            )
            return

        fake = Faker("pt_BR")
        states = [
            # 'AC', 'AL', 'AP',
            "AM"
            # 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            # 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            # 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]

        neighborhoods = {
            "AM": [
                "Adrianópolis",
                "Aleixo",
                "Chapada",
                "Cidade Nova",
                "Compensa",
                "Flores",
                "Parque 10",
            ],
            #'SP': ['Pinheiros', 'Vila Madalena', 'Moema', 'Itaim Bibi', 'Jardins', 'Consolação', 'Tatuapé'],
            #'RJ': ['Copacabana', 'Ipanema', 'Leblon', 'Barra da Tijuca', 'Botafogo', 'Tijuca', 'Flamengo'],
            #'MG': ['Savassi', 'Lourdes', 'Funcionários', 'Buritis', 'Belvedere', 'Santa Efigênia', 'Pampulha'],
            #'RS': ['Moinhos de Vento', 'Bela Vista', 'Cidade Baixa', 'Menino Deus', 'Rio Branco', 'Petrópolis'],
        }

        cities = {
            "AM": ["Manaus", "Itacoatiara", "Parintins", "Manacapuru", "Coari"],
            #'SP': ['São Paulo', 'Campinas', 'Santos', 'Guarulhos', 'Osasco'],
            #'RJ': ['Rio de Janeiro', 'Niterói', 'Duque de Caxias', 'Nova Iguaçu', 'Petrópolis'],
            #'MG': ['Belo Horizonte', 'Uberlândia', 'Contagem', 'Juiz de Fora', 'Betim'],
            #'RS': ['Porto Alegre', 'Caxias do Sul', 'Pelotas', 'Canoas', 'Santa Maria'],
        }

        default_states = [
            "AM",
            #'SP', 'RJ', 'MG', 'RS'
        ]

        service_templates = [
            # ... (service templates remain the same) ...
            {
                "name": "Corte de Cabelo",
                "description": "Corte profissional adaptado ao seu estilo.",
                "price_range": (40, 120),
                "duration_range": (30, 60),
            },
            {
                "name": "Coloração",
                "description": "Coloração completa com produtos de qualidade.",
                "price_range": (80, 250),
                "duration_range": (90, 180),
            },
            {
                "name": "Barba",
                "description": "Modelagem e acabamento de barba.",
                "price_range": (25, 60),
                "duration_range": (20, 40),
            },
            {
                "name": "Hidratação",
                "description": "Tratamento intensivo para cabelos danificados.",
                "price_range": (70, 150),
                "duration_range": (45, 90),
            },
            {
                "name": "Escova",
                "description": "Escova modeladora para todos os tipos de cabelo.",
                "price_range": (50, 120),
                "duration_range": (30, 60),
            },
            {
                "name": "Mechas",
                "description": "Mechas com técnica personalizada.",
                "price_range": (150, 400),
                "duration_range": (120, 240),
            },
            {
                "name": "Penteado",
                "description": "Penteado para eventos especiais.",
                "price_range": (100, 200),
                "duration_range": (60, 120),
            },
            {
                "name": "Progressiva",
                "description": "Alisamento progressivo duradouro.",
                "price_range": (200, 500),
                "duration_range": (120, 180),
            },
            {
                "name": "Luzes",
                "description": "Técnica de iluminação para cabelos.",
                "price_range": (180, 350),
                "duration_range": (120, 180),
            },
            {
                "name": "Design de Sobrancelhas",
                "description": "Modelagem perfeita para suas sobrancelhas.",
                "price_range": (30, 80),
                "duration_range": (15, 40),
            },
            {
                "name": "Tratamento Capilar",
                "description": "Tratamento completo para saúde dos cabelos.",
                "price_range": (100, 300),
                "duration_range": (60, 120),
            },
            {
                "name": "Manicure",
                "description": "Cuidados completos para suas unhas.",
                "price_range": (30, 90),
                "duration_range": (30, 60),
            },
        ]

        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        # Define the base path for profile pictures
        profile_pics_dir = os.path.join(settings.BASE_DIR, 'media', 'profile_pics')
        
        # Check if the directory exists to prevent errors
        if not os.path.isdir(profile_pics_dir):
            self.stdout.write(self.style.ERROR(f"Profile picture directory not found at: {profile_pics_dir}"))
            return

        male_pics = [f for f in os.listdir(profile_pics_dir) if "male" in f]
        female_pics = [f for f in os.listdir(profile_pics_dir) if "female" in f]

        if not male_pics or not female_pics:
            self.stdout.write(self.style.ERROR("Could not find male or female placeholder images in media/profile_pics/"))
            return

        for i in range(40):
            try:
                state = random.choice(default_states) if random.random() < 0.8 else random.choice(states)
                city = random.choice(cities.get(state, [fake.city()]))
                neighborhood = random.choice(neighborhoods.get(state, [fake.bairro()]))

                gender = random.choice(["male", "female"])
                if gender == "male":
                    first_name = fake.first_name_male()
                    profile_pic_name = random.choice(male_pics)
                else:
                    first_name = fake.first_name_female()
                    profile_pic_name = random.choice(female_pics)
                
                # This is the full path to the source image file
                profile_pic_path = os.path.join(profile_pics_dir, profile_pic_name)

                # Create user data dictionary
                user_data = {
                    'email': f"hairdresser{i+1}_{fake.user_name()}@{fake.free_email_domain()}",
                    'first_name': first_name,
                    'last_name': fake.last_name(),
                    'password': 'senha123', # Remember to set password correctly
                    'phone': fake.phone_number(),
                    'state': state,
                    'complement': f"apt {random.randint(101, 999)}",
                    'neighborhood': neighborhood,
                    'city': city,
                    'address': fake.street_name(),
                    'number': str(random.randint(1, 9999)),
                    'postal_code': fake.postcode(),
                    'rating': round(random.uniform(3.0, 5.0), 1),
                    'role': 'hairdresser',
                }
                
                # Create the user first, without the picture
                user = User.objects.create(**user_data)
                user.set_password('senha123') # Use set_password to hash it

                # Now, attach the profile picture
                with open(profile_pic_path, "rb") as f:
                    # The key change is here: provide the filename separately.
                    user.profile_picture.save(profile_pic_name, File(f), save=True)

                preferences_ids = random.sample(list(range(1, 18)), random.randint(2, 6))
                user.preferences.set(preferences_ids)
                user.save()

                # Create Hairdresser
                hairdresser = Hairdresser.objects.create(
                    user=user,
                    cnpj=''.join([str(random.randint(0, 9)) for _ in range(14)]),
                    experience_years=random.randint(1, 20),
                    resume=fake.paragraph(nb_sentences=3),
                )

                # Create Availabilities (3-7 per hairdresser)
                num_availabilities = random.randint(3, 7)
                available_weekdays = random.sample(weekdays, num_availabilities)

                for weekday in available_weekdays:
                    start_hour = random.randint(7, 10)
                    end_hour = random.randint(17, 21)
                    start_time = time(start_hour, 0, 0)
                    end_time = time(end_hour, 0, 0)

                    availability_data = {
                        "hairdresser": hairdresser,
                        "weekday": weekday,
                        "start_time": start_time,
                        "end_time": end_time,
                    }

                    if random.random() > 0.5:
                        availability_data["break_start"] = time(12, 0, 0)
                        availability_data["break_end"] = time(13, 0, 0)

                    Availability.objects.create(**availability_data)

                # Create Services (3-7 per hairdresser)
                num_services = random.randint(3, 7)
                selected_services = random.sample(service_templates, num_services)

                for service_template in selected_services:
                    price = random.randint(*service_template["price_range"])
                    duration = random.randint(
                        *service_template["duration_range"]
                    )
                    name_suffix = random.choice(
                        [
                            "",
                            " Premium",
                            " Express",
                            " Profissional",
                            " Especial",
                        ]
                    )

                    Service.objects.create(
                        hairdresser=hairdresser,
                        name=service_template["name"] + name_suffix,
                        description=service_template["description"],
                        price=price,
                        duration=duration,
                    )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating hairdresser {i+1}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(
                "Successfully added fake hairdressers with availabilities and services to the database"
            )
        )