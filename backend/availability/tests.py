from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from users.models import Hairdresser
from availability.models import Availability
from availability.serializers import AvailabilitySerializer
import json
import jwt
from datetime import datetime, timedelta, time

class AvailabilityModelTests(TestCase):
    """Testes para o modelo Availability"""

    def setUp(self):
        # Criar usuário e cabeleireiro para testes
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            name='Test Hairdresser',
            phone='123456789'
        )
    
    def test_availability_creation(self):
        """Teste de criação de disponibilidade"""
        availability = Availability.objects.create(
            weekday='Monday',
            start_time=time(9, 0),
            end_time=time(17, 0),
            hairdresser=self.hairdresser
        )
        
        self.assertEqual(availability.weekday, 'Monday')
        self.assertEqual(availability.start_time, time(9, 0))
        self.assertEqual(availability.end_time, time(17, 0))
        self.assertEqual(availability.hairdresser, self.hairdresser)
    
    def test_availability_string_representation(self):
        """Teste da representação em string da disponibilidade"""
        availability = Availability.objects.create(
            weekday='Tuesday',
            start_time=time(10, 0),
            end_time=time(18, 0),
            hairdresser=self.hairdresser
        )
        
        # Este teste vai falhar a menos que você adicione um método __str__ no modelo
        # A implementação abaixo é sugerida
        # def __str__(self):
        #     return f"{self.hairdresser.name} - {self.weekday} {self.start_time} to {self.end_time}"
        
        expected_string = f"{self.hairdresser.name} - Tuesday {time(10, 0)} to {time(18, 0)}"
        self.assertEqual(str(availability), expected_string)


class AvailabilitySerializerTests(TestCase):
    """Testes para o serializador AvailabilitySerializer"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            name='Test Hairdresser',
            phone='123456789'
        )
        self.availability_attributes = {
            'weekday': 'Wednesday',
            'start_time': time(8, 0),
            'end_time': time(16, 0),
            'hairdresser': self.hairdresser
        }
        self.availability = Availability.objects.create(**self.availability_attributes)
        self.serializer = AvailabilitySerializer(instance=self.availability)
    
    def test_serializer_contains_expected_fields(self):
        """Teste para verificar se o serializador contém os campos esperados"""
        data = self.serializer.data
        self.assertEqual(set(data.keys()), set(['id', 'weekday', 'start_time', 'end_time']))
    
    def test_weekday_field_content(self):
        """Teste para verificar o conteúdo do campo weekday"""
        data = self.serializer.data
        self.assertEqual(data['weekday'], self.availability_attributes['weekday'])


class AvailabilityViewTests(APITestCase):
    """Testes para as views da API"""
    
    def setUp(self):
        # Criar cliente da API
        self.client = APIClient()
        
        # Criar usuário e cabeleireiro para testes
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            name='Test Hairdresser',
            phone='123456789'
        )
        
        # Criar token JWT para autenticação
        payload = {
            'id': self.user.id,
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow()
        }
        self.token = jwt.encode(payload, 'secret', algorithm='HS256')
        
        # Criar disponibilidade de exemplo
        self.availability = Availability.objects.create(
            weekday='Friday',
            start_time=time(9, 0),
            end_time=time(17, 0),
            hairdresser=self.hairdresser
        )
    
    def test_create_availability(self):
        """Teste para criação de disponibilidade"""
        # Configurar o cookie com o token JWT
        self.client.cookies['jwt'] = self.token
        
        url = reverse('create_availability')
        data = {
            'weekday': 'Saturday',
            'start_time': '10:00:00',
            'end_time': '18:00:00'
        }
        
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['message'], 'Availability registered successfully')
        
        # Verificar se a disponibilidade foi criada no banco de dados
        self.assertTrue(Availability.objects.filter(weekday='Saturday', hairdresser=self.hairdresser).exists())
    
    def test_create_availability_without_token(self):
        """Teste para criação de disponibilidade sem token"""
        url = reverse('create_availability')
        data = {
            'weekday': 'Sunday',
            'start_time': '10:00:00',
            'end_time': '18:00:00'
        }
        
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['error'], 'Invalid token')
    
    def test_create_availability_missing_fields(self):
        """Teste para criação de disponibilidade com campos faltando"""
        self.client.cookies['jwt'] = self.token
        
        url = reverse('create_availability')
        data = {
            'weekday': 'Sunday',
            # Falta start_time e end_time
        }
        
        response = self.client.post(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
    
    def test_list_availability(self):
        """Teste para listar disponibilidades de um cabeleireiro"""
        url = reverse('list_availability', args=[self.hairdresser.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']), 1)
        self.assertEqual(response.json()['data'][0]['weekday'], 'Friday')
    
    def test_list_availability_nonexistent_hairdresser(self):
        """Teste para listar disponibilidades de um cabeleireiro inexistente"""
        url = reverse('list_availability', args=[999])  # ID inexistente
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']), 0)  # Lista vazia
    
    def test_remove_availability(self):
        """Teste para remover disponibilidade"""
        url = reverse('remove_availability', args=[self.availability.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['message'], 'Availability removed successfully')
        
        # Verificar se a disponibilidade foi removida do banco de dados
        self.assertFalse(Availability.objects.filter(id=self.availability.id).exists())
    
    def test_remove_nonexistent_availability(self):
        """Teste para remover disponibilidade inexistente"""
        url = reverse('remove_availability', args=[999])  # ID inexistente
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Availability not found')
    
    def test_update_availability(self):
        """Teste para atualizar disponibilidade"""
        url = reverse('update_availability', args=[self.availability.id])
        data = {
            'weekday': 'Thursday',
            'start_time': '11:00:00',
            'end_time': '19:00:00'
        }
        
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['message'], 'Availability updated successfully')
        
        # Verificar se a disponibilidade foi atualizada no banco de dados
        updated_availability = Availability.objects.get(id=self.availability.id)
        self.assertEqual(updated_availability.weekday, 'Thursday')
        self.assertEqual(updated_availability.start_time.strftime('%H:%M:%S'), '11:00:00')
        self.assertEqual(updated_availability.end_time.strftime('%H:%M:%S'), '19:00:00')
    
    def test_update_partial_availability(self):
        """Teste para atualização parcial de disponibilidade"""
        url = reverse('update_availability', args=[self.availability.id])
        data = {
            'weekday': 'Monday',
            # Manter start_time e end_time como estão
        }
        
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar se apenas o campo weekday foi atualizado
        updated_availability = Availability.objects.get(id=self.availability.id)
        self.assertEqual(updated_availability.weekday, 'Monday')
        self.assertEqual(updated_availability.start_time, self.availability.start_time)
        self.assertEqual(updated_availability.end_time, self.availability.end_time)
    
    def test_update_nonexistent_availability(self):
        """Teste para atualizar disponibilidade inexistente"""
        url = reverse('update_availability', args=[999])  # ID inexistente
        data = {
            'weekday': 'Thursday',
        }
        
        response = self.client.put(url, data=json.dumps(data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Availability not found')


# Exemplo de testes de integração
class AvailabilityIntegrationTests(APITestCase):
    """Testes de integração para o fluxo completo de disponibilidade"""
    
    def setUp(self):
        # Criar cliente da API
        self.client = APIClient()
        
        # Criar usuário e cabeleireiro para testes
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            name='Test Hairdresser',
            phone='123456789'
        )
        
        # Criar token JWT para autenticação
        payload = {
            'id': self.user.id,
            'exp': datetime.utcnow() + timedelta(days=1),
            'iat': datetime.utcnow()
        }
        self.token = jwt.encode(payload, 'secret', algorithm='HS256')
    
    def test_full_availability_flow(self):
        """Teste do fluxo completo: criar, listar, atualizar e remover disponibilidade"""
        # 1. Criar disponibilidade
        self.client.cookies['jwt'] = self.token
        create_url = reverse('create_availability')
        create_data = {
            'weekday': 'Monday',
            'start_time': '09:00:00',
            'end_time': '17:00:00'
        }
        
        create_response = self.client.post(create_url, data=json.dumps(create_data), content_type='application/json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        # 2. Listar disponibilidade para verificar se foi criada
        list_url = reverse('list_availability', args=[self.hairdresser.id])
        list_response = self.client.get(list_url)
        
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.json()['data']), 1)
        
        # Pegar o ID da disponibilidade criada
        availability_id = list_response.json()['data'][0]['id']
        
        # 3. Atualizar disponibilidade
        update_url = reverse('update_availability', args=[availability_id])
        update_data = {
            'weekday': 'Tuesday',
            'start_time': '10:00:00',
            'end_time': '18:00:00'
        }
        
        update_response = self.client.put(update_url, data=json.dumps(update_data), content_type='application/json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        
        # 4. Listar novamente para verificar a atualização
        list_after_update_response = self.client.get(list_url)
        updated_availability = list_after_update_response.json()['data'][0]
        
        self.assertEqual(updated_availability['weekday'], 'Tuesday')
        self.assertEqual(updated_availability['start_time'], '10:00:00')
        self.assertEqual(updated_availability['end_time'], '18:00:00')
        
        # 5. Remover disponibilidade
        remove_url = reverse('remove_availability', args=[availability_id])
        remove_response = self.client.delete(remove_url)
        
        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)
        
        # 6. Listar novamente para verificar a remoção
        list_after_delete_response = self.client.get(list_url)
        self.assertEqual(len(list_after_delete_response.json()['data']), 0)