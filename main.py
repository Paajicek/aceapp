from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import mysql.connector
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Připojení k databázi db4free.net
db = mysql.connector.connect(
    host="db4free.net",
    user="paajicek",
    password="Bohemka1905",
    database="esatenis"
)

# Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scope)
client = gspread.authorize(creds)
sheet = client.open("aceapp").sheet1

@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    cursor = db.cursor()
    cursor.execute("SELECT Player FROM esa_prepared ORDER BY Player ASC")
    players = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return templates.TemplateResponse("form.html", {"request": request, "players": players})

@app.get("/result", response_class=HTMLResponse)
def result(request: Request, player1: str, player2: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player1,))
    row1 = cursor.fetchone()
    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player2,))
    row2 = cursor.fetchone()
    cursor.close()

    if not row1 or not row2:
        return HTMLResponse(content="Jeden nebo oba hráči nebyli nalezeni v databázi.", status_code=404)

    def vypocet(player, gender, ah, df, va, p_tour_ace, p_tour_df, va_soupere, gender_hrace):
        s = 70 if gender_hrace == "M" else 65
        e = s * ah * (va_soupere / p_tour_ace)
        d = s * df * (va_soupere / p_tour_df)
        return round(e, 2), round(d, 2)

    p_tour_ace = 0.089 if row1[1] == "M" else 0.042
    p_tour_df = 0.029 if row1[1] == "M" else 0.04

    esa1, df1 = vypocet(*row1, p_tour_ace, p_tour_df, row2[4], row1[1])
    esa2, df2 = vypocet(*row2, p_tour_ace, p_tour_df, row1[4], row2[1])

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, player1, esa1, df1, player2, esa2, df2])

    return templates.TemplateResponse("result.html", {
        "request": request,
        "player1": player1,
        "esa1": esa1,
        "df1": df1,
        "player2": player2,
        "esa2": esa2,
        "df2": df2
    })
