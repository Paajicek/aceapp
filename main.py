from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import mysql.connector
from datetime import datetime
import gspread
import os
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Připojení k databázi
db = mysql.connector.connect(
    host="sql8.freemysqlhosting.net",
    user="sql8683763",
    password="hVXbkJ6tbB",
    database="sql8683763"
)

# Parametry pro výpočet
p_tour_ace = 8.9  # tvrdý povrch, muži
p_tour_df = 3.5

# Výpočet es a dvojchyb
def vypocet(gender, ah, df, vah, p_tour_ace, p_tour_df, vs_vace, vs_gender):
    s = 70 if gender == "M" else 65
    ph = ah
    ps = vs_vace
    esa = s * ph / 100 * (ps / p_tour_ace)
    dvojchyby = s * df / 100 * (p_tour_df / 3.5)
    return round(esa, 2), round(dvojchyby, 2)

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    cursor = db.cursor()
    cursor.execute("SELECT Player FROM esa_prepared ORDER BY Player")
    players = [row[0] for row in cursor.fetchall()]
    return templates.TemplateResponse("form.html", {"request": request, "players": players})

@app.get("/result", response_class=HTMLResponse)
async def result(request: Request, player1: str, player2: str):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player1,))
    row1 = cursor.fetchone()
    cursor.fetchall()  # Vyčistí předchozí výsledky
    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player2,))
    row2 = cursor.fetchone()
    cursor.fetchall()

    if not row1 or not row2:
        return templates.TemplateResponse("error.html", {"request": request, "msg": "Hráč nenalezen"})

    esa1, df1 = vypocet(*row1[1:], p_tour_ace, p_tour_df, row2[3], row1[1])
    esa2, df2 = vypocet(*row2[1:], p_tour_ace, p_tour_df, row1[3], row2[1])
    celkem_esa = round(esa1 + esa2, 2)
    celkem_df = round(df1 + df2, 2)

    # Zápis do Google Sheets
    try:
        service_account_info = json.loads(os.getenv("GOOGLE_KEY_JSON"))
        gc = gspread.service_account_from_dict(service_account_info)
        sh = gc.open("Aceapp")
        worksheet = sh.worksheet("Esa výsledky")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_row = [
            now, player1, row1[2], row1[3], row1[4], esa1, df1,
            player2, row2[2], row2[3], row2[4], esa2, df2,
            celkem_esa, celkem_df
        ]
        worksheet.append_row(data_row)
    except Exception as e:
        print("Chyba při zápisu do Google Sheets:", e)

    return templates.TemplateResponse("result.html", {
        "request": request,
        "player1": player1,
        "ace1": row1[2],
        "vace1": row1[3],
        "df1": row1[4],
        "esa1": esa1,
        "dvojchyby1": df1,
        "player2": player2,
        "ace2": row2[2],
        "vace2": row2[3],
        "df2": row2[4],
        "esa2": esa2,
        "dvojchyby2": df2,
        "celkem_esa": celkem_esa,
        "celkem_df": celkem_df
    })
