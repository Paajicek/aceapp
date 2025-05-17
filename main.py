from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import mysql.connector
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Přímé připojení k MySQL databázi
try:
    db = mysql.connector.connect(
        host="db4free.net",
        user="paajicek",
        password="Bohemka1905",
        database="esatenis"
    )
except mysql.connector.Error as err:
    print("Chyba při připojení k databázi:", err)
    raise

cursor = db.cursor()

# Připojení ke Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Esa zápasy").sheet1

# Průměrné hodnoty pro výpočty
p_tour_ace = 4.2
p_tour_df = 6.0

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    cursor.execute("SELECT DISTINCT Player FROM esa_prepared ORDER BY Player")
    players = [row[0] for row in cursor.fetchall()]
    return templates.TemplateResponse("form.html", {"request": request, "players": players})

@app.get("/result", response_class=HTMLResponse)
async def result(request: Request, player1: str, player2: str):
    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player1,))
    row1 = cursor.fetchone()
    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player2,))
    row2 = cursor.fetchone()

    if not row1 or not row2:
        return templates.TemplateResponse("form.html", {
            "request": request,
            "players": [player1, player2],
            "error": "Nebyli nalezeni oba hráči v databázi."
        })

    def vypocet(player, gender, ah, df, vah, p_tour_ace, p_tour_df, vace, vdf):
        S = 65 if gender == "W" else 70
        E = S * ah * (vace / p_tour_ace)
        D = S * df * (vdf / p_tour_df)
        return round(E, 2), round(D, 2)

    esa1, df1 = vypocet(*row1, p_tour_ace, p_tour_df, row2[4], row2[3])
    esa2, df2 = vypocet(*row2, p_tour_ace, p_tour_df, row1[4], row1[3])

    sheet.append_row([player1, esa1, df1, player2, esa2, df2])

    return templates.TemplateResponse("form.html", {
        "request": request,
        "players": [player1, player2],
        "player1": player1,
        "player2": player2,
        "esa1": esa1,
        "df1": df1,
        "esa2": esa2,
        "df2": df2
    })
