import requests

# Reemplaza con los datos de tu aplicación Twitch
CLIENT_ID = "aio0y5syf7jlxq20qoy7768korw1me"
CLIENT_SECRET = "rnx2e28oxugmmxyo2q9bof52a1qqxf"  # ¡Esto es obligatorio!

# URL para pedir el Access Token
url = "https://id.twitch.tv/oauth2/token"

# Datos de la solicitud
data = {
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,  # ⚠ necesario
    "grant_type": "client_credentials"
}

# Hacer la solicitud POST
response = requests.post(url, data=data)

# Convertir a JSON
token_info = response.json()

print(token_info)  # Muestra toda la respuesta de Twitch
