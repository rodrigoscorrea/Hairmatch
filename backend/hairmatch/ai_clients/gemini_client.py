import google.generativeai as genai
from users.serializers import HairdresserFullInfoSerializer
from users.models import Hairdresser
from django.http import JsonResponse
from django.conf import settings
from preferences.models import Preferences
from preferences.serializers import PreferencesNameSerializer

def setup_environment():
    gemini_api_key = settings.GEMINI_API_KEY 
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY not defined")
    genai.configure(api_key=gemini_api_key)

def load_hairdresser_data(hairdresser_id: int): 
    try: 
        hairdresser = Hairdresser.objects.get(id=hairdresser_id)
    except Hairdresser.DoesNotExist:
        return None
    hairdresser_serialized = HairdresserFullInfoSerializer(hairdresser).data
    return hairdresser_serialized


def generate_ai_text(prompt, model_name='gemini-2.0-flash', temperature=0.7, max_output_tokens=200):
    """
    Gera texto usando o modelo generativo do Google.

    Args:
        prompt (str): O prompt para o modelo.
        model_name (str): O nome do modelo a ser usado.
        temperature (float): A temperatura para a geração.
        max_output_tokens (int): O número máximo de tokens na saída.

    Returns:
        str: O texto gerado pelo modelo.
    """
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_output_tokens
        }
    )
    return response.text

def process_hairdresser_profile(profile_data):
    """
    Processa o perfil de um cabeleireiro para gerar uma descrição resumida.

    Args:
        profile_data (dict): Um dicionário contendo os dados do perfil do cabeleireiro.

    Returns:
        str: Uma descrição resumida e atrativa do perfil.
    """
    
    prompt1 = (
        "Analise o perfil a seguir e destaque as informações mais relevantes que "
        "ajudariam um cliente a decidir se deve escolher este cabeleireiro. "
        "Considere aspectos como especializações, experiência, avaliações, "
        f"localização, entre outros.\n\nDados do perfil do cabeleireiro:\n{profile_data}"
    )
    relevant_information = generate_ai_text(prompt1)

    prompt2 = (
        "Com base nas informações mais relevantes identificadas abaixo, elabore um "
        "resumo claro e atrativo do perfil do cabeleireiro, em apenas um parágrafo, "
        "destacando seus principais diferenciais para potenciais clientes.\n\n"
        f"Informações relevantes sobre o cabeleireiro:\n{relevant_information}"
    )
    final_description = generate_ai_text(prompt2, max_output_tokens=100)
    return final_description

def hairdresser_profile_ai_completion(data):
    try:
        setup_environment()
        hairdresser_data_raw = data
         
        if hairdresser_data_raw is None:
            return JsonResponse({'error': "Hairdresser data not provided"}, status=404)
        
        hairdresser_raw_preferences = hairdresser_data_raw.get('preferences')
        hairdresser_filtered_preferences = Preferences.objects.filter(id__in=hairdresser_raw_preferences)
        serialized_hairdressed_preferences = PreferencesNameSerializer(
                                                hairdresser_filtered_preferences,
                                                many=True).data
         
        hairdresser_data = hairdresser_data_raw
        hairdresser_data['preferences'] = serialized_hairdressed_preferences

        
        generated_description = process_hairdresser_profile(hairdresser_data)
        return JsonResponse({'result': generated_description}, status = 200)

    except ValueError as ve:
        return JsonResponse({'error': f"Config error: {ve}"}, status=500)
    except Exception as e:
        return JsonResponse({'error': f"Unexpected error occurred: {e}"}, status=500)