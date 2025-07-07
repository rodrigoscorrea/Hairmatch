from django.core.management.base import BaseCommand
from users.models import User, Hairdresser
from service.models import Service
from availability.models import Availability
from faker import Faker
import random
from datetime import time

class Command(BaseCommand):
    help = 'Populates the database with 40 fake hairdressers if none exist, along with their availabilities and services'

    def handle(self, *args, **kwargs):
        existing_hairdressers = User.objects.filter(role='hairdresser').count()
        
        if existing_hairdressers > 0:
            self.stdout.write(self.style.SUCCESS(f'There are already hairdressers in the database. Skipping.'))
            return

        fake = Faker('pt_BR')
        states = [
                #'AC', 'AL', 'AP', 
                'AM'
                # 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 
                # 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 
                # 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
                ]
        
        neighborhoods = {
            'AM': ['Adrianópolis', 'Aleixo', 'Chapada', 'Cidade Nova', 'Compensa', 'Flores', 'Parque 10'],
            #'SP': ['Pinheiros', 'Vila Madalena', 'Moema', 'Itaim Bibi', 'Jardins', 'Consolação', 'Tatuapé'],
            #'RJ': ['Copacabana', 'Ipanema', 'Leblon', 'Barra da Tijuca', 'Botafogo', 'Tijuca', 'Flamengo'],
            #'MG': ['Savassi', 'Lourdes', 'Funcionários', 'Buritis', 'Belvedere', 'Santa Efigênia', 'Pampulha'],
            #'RS': ['Moinhos de Vento', 'Bela Vista', 'Cidade Baixa', 'Menino Deus', 'Rio Branco', 'Petrópolis'],
        }
        
        cities = {
            'AM': ['Manaus', 'Itacoatiara', 'Parintins', 'Manacapuru', 'Coari'],
            #'SP': ['São Paulo', 'Campinas', 'Santos', 'Guarulhos', 'Osasco'],
            #'RJ': ['Rio de Janeiro', 'Niterói', 'Duque de Caxias', 'Nova Iguaçu', 'Petrópolis'],
            #'MG': ['Belo Horizonte', 'Uberlândia', 'Contagem', 'Juiz de Fora', 'Betim'],
            #'RS': ['Porto Alegre', 'Caxias do Sul', 'Pelotas', 'Canoas', 'Santa Maria'],
        }
        
        default_states = [
            'AM'
            #, 'SP', 'RJ', 'MG', 'RS'
            ]
        
        # Service data
        service_templates = [
            {
                "name": "Corte de Cabelo",
                "description": "Corte profissional adaptado ao seu estilo.",
                "price_range": (40, 120),
                "duration_range": (30, 60)
            },
            {
                "name": "Coloração",
                "description": "Coloração completa com produtos de qualidade.",
                "price_range": (80, 250),
                "duration_range": (90, 180)
            },
            {
                "name": "Barba",
                "description": "Modelagem e acabamento de barba.",
                "price_range": (25, 60),
                "duration_range": (20, 40)
            },
            {
                "name": "Hidratação",
                "description": "Tratamento intensivo para cabelos danificados.",
                "price_range": (70, 150),
                "duration_range": (45, 90)
            },
            {
                "name": "Escova",
                "description": "Escova modeladora para todos os tipos de cabelo.",
                "price_range": (50, 120),
                "duration_range": (30, 60)
            },
            {
                "name": "Mechas",
                "description": "Mechas com técnica personalizada.",
                "price_range": (150, 400),
                "duration_range": (120, 240)
            },
            {
                "name": "Penteado",
                "description": "Penteado para eventos especiais.",
                "price_range": (100, 200),
                "duration_range": (60, 120)
            },
            {
                "name": "Progressiva",
                "description": "Alisamento progressivo duradouro.",
                "price_range": (200, 500),
                "duration_range": (120, 180)
            },
            {
                "name": "Luzes",
                "description": "Técnica de iluminação para cabelos.",
                "price_range": (180, 350),
                "duration_range": (120, 180)
            },
            {
                "name": "Design de Sobrancelhas",
                "description": "Modelagem perfeita para suas sobrancelhas.",
                "price_range": (30, 80),
                "duration_range": (15, 40)
            },
            {
                "name": "Tratamento Capilar",
                "description": "Tratamento completo para saúde dos cabelos.",
                "price_range": (100, 300),
                "duration_range": (60, 120)
            },
            {
                "name": "Manicure",
                "description": "Cuidados completos para suas unhas.",
                "price_range": (30, 90),
                "duration_range": (30, 60)
            }
        ]
        
        # Weekdays for availabilities
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        users_data = []
        hairdressers_data = []
        
        for i in range(40):
            # Choose a state, preferring states with defined neighborhoods
            state = random.choice(default_states) if random.random() < 0.8 else random.choice(states)
            
            if state in cities:
                city = random.choice(cities[state])
            else:
                city = fake.city()
            
            if state in neighborhoods:
                neighborhood = random.choice(neighborhoods[state])
            else:
                neighborhood = fake.neighborhood()
                
            all_preferences = list(range(1, 18))
            num_preferences = random.randint(2, 6)  # Each hairdresser will have 2-6 preferences
            preferences = random.sample(all_preferences, num_preferences)

            email = f"hairdresser{i+1}_{fake.user_name()}@{fake.free_email_domain()}"
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'password': 'senha123',
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
                'preferences': preferences
            }

            hairdresser_data = {
                'cnpj': ''.join([str(random.randint(0, 9)) for _ in range(14)]),
                'experience_years': random.randint(1, 20),
                'resume': fake.paragraph(nb_sentences=3),
            }
            
            users_data.append(user_data)
            hairdressers_data.append(hairdresser_data)
        
        created_hairdressers = 0
        created_availabilities = 0
        created_services = 0
        
        for i in range(len(users_data)):
            try:
                # Create User
                preferences_ids = users_data[i].pop('preferences')
                user = User.objects.create(**users_data[i])
                user.preferences.set(preferences_ids)
                
                # Create Hairdresser
                hairdresser = Hairdresser.objects.create(user=user, **hairdressers_data[i])
                created_hairdressers += 1
                
                # Create Availabilities (3-7 per hairdresser)
                num_availabilities = random.randint(3, 7)
                available_weekdays = random.sample(weekdays, num_availabilities)
                
                for weekday in available_weekdays:
                    # Generate random start and end times
                    start_hour = random.randint(7, 10)
                    end_hour = random.randint(17, 21)
                    
                    # Create start and end times
                    start_time = time(start_hour, 0, 0)
                    end_time = time(end_hour, 0, 0)
                    
                    # Decide if this availability has a break (50% chance)
                    has_break = random.random() > 0.5
                    
                    if has_break:
                        # Break is typically around lunch time
                        break_start = time(12, 0, 0)
                        break_end = time(13, 0, 0)
                        
                        availability = Availability.objects.create(
                            hairdresser=hairdresser,
                            weekday=weekday,
                            start_time=start_time,
                            end_time=end_time,
                            break_start=break_start,
                            break_end=break_end
                        )
                    else:
                        availability = Availability.objects.create(
                            hairdresser=hairdresser,
                            weekday=weekday,
                            start_time=start_time,
                            end_time=end_time
                        )
                    
                    created_availabilities += 1
                
                # Create Services (3-7 per hairdresser)
                num_services = random.randint(3, 7)
                selected_services = random.sample(service_templates, num_services)
                
                for service_template in selected_services:
                    # Add some variation to services
                    price = random.randint(*service_template["price_range"])
                    duration = random.randint(*service_template["duration_range"])
                    
                    # Add suffix to make services slightly different between hairdressers
                    name_variations = ["", " Premium", " Express", " Profissional", " Especial"]
                    name_suffix = random.choice(name_variations)
                    
                    service = Service.objects.create(
                        hairdresser=hairdresser,
                        name=service_template["name"] + name_suffix,
                        description=service_template["description"],
                        price=price,
                        duration=duration
                    )
                    
                    created_services += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating hairdresser {i+1}: {str(e)}")
                )
            
        self.stdout.write(self.style.SUCCESS(
            f'Successfully added fake hairdressers with availabilities and services to the database'
        ))