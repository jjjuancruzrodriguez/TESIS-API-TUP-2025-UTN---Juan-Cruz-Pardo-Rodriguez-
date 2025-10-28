import requests

CLIENT_ID = "aio0y5syf7jlxq20qoy7768korw1me"
ACCESS_TOKEN = "s06iuied2y1tg716omjzrnox1c9zsr"
HEADERS = {
    "Client-ID": CLIENT_ID,
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

def buscar_juego(nombre):
    url = "https://api.igdb.com/v4/games"
    query = f'search "{nombre}"; fields name,genres.name,first_release_date,rating; limit 5;'
    response = requests.post(url, headers=HEADERS, data=query)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code}"
