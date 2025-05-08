import requests

# URL da sua API
url = "http://localhost:8000/api/preferences/create"

# Lista de nomes
nomes = [
    "Coloração", "Cachos", "Barbearia", "Tranças", "Undercut",
    "Alisamento", "Corte Social", "Fade", "Platinado",
    "Corte Long Bob", "Luzes", "Corte em Camadas", "Hidratação",
    "Razor Part", "Chanel", "Mullet", "Wolf Cut"
]

# Envio de cada POST
for nome in nomes:
    payload = {
        "name": nome,
        "picture": "minha-imagem.jpg"  # substitua se precisar
    }
    response = requests.post(url, json=payload)
    
    # Feedback da resposta
    print(f"Enviado: {nome} -> Status: {response.status_code} | Resposta: {response.text}")
