from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import mysql.connector
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import tempfile

app = FastAPI()
templates = Jinja2Templates(directory="templates")

def get_connection():
    return mysql.connector.connect(
        host="db4free.net",
        user="paajicek",
        password="Bohemka1905",
        database="esatenis"
    )

def get_google_client():
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not credentials_json:
        raise Exception("Chybí proměnná GOOGLE_CREDENTIALS_JSON")

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as temp_file:
        temp_file.write(credentials_json)
        temp_file.flush()
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            temp_file.name,
            ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        )
    return gspread.authorize(credentials)

@app.get("/", response_class=HTMLResponse)
def form(request: Request):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Player FROM esa_prepared ORDER BY Player")
    players = [row[0] for row in cursor.fetchall()]
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "players": players})

@app.get("/result", response_class=HTMLResponse)
def result(request: Request, player1: str, player2: str):
    # načtení prvního hráče
    conn1 = get_connection()
    cursor1 = conn1.cursor()
    cursor1.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player1,))
    row1 = cursor1.fetchone()
    conn1.close()

    # načtení druhého hráče
    conn2 = get_connection()
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player2,))
    row2 = cursor2.fetchone()
    conn2.close()

    def vypocet(player, ah, df, vah, p_tour_ace, p_tour_df, opponent_vah, typ):
        S = 70 if typ == "M" else 65
        expected_aces = S * ah * (opponent_vah / p_tour_ace)
        expected_dfs = S * df * (opponent_vah / p_tour_df)
        return round(expected_aces, 2), round(expected_dfs, 2)

    p_tour_ace = 8.9 if row1[1] == "M" else 4.2
    p_tour_df = 3.2

    esa1, df1 = vypocet(*row1[1:], p_tour_ace, p_tour_df, row2[3], row1[1])
    esa2, df2 = vypocet(*row2[1:], p_tour_ace, p_tour_df, row1[3], row2[1])

    celkem_esa = round(esa1 + esa2, 2)
    celkem_df = round(df1 + df2, 2)

    try:
        gc = get_google_client()
        sh = gc.open("Aceapp")
        worksheet = sh.sheet1

        datum = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [
            datum, player1, f"{row1[2]*100:.1f}%", f"{row1[4]*100:.1f}%", f"{row1[3]*100:.1f}%", esa1, df1,
            player2, f"{row2[2]*100:.1f}%", f"{row2[4]*100:.1f}%", f"{row2[3]*100:.1f}%", esa2, df2,
            celkem_esa, celkem_df
        ]
        worksheet.append_row(row)
    except Exception as e:
        print("Chyba při zápisu do Google Sheets:", e)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "players": [player1, player2],
        "result": {
            "player1": player1,
            "ace1": row1[2], "vace1": row1[4], "df1": row1[3], "esa1": esa1, "dvojchyby1": df1,
            "player2": player2,
            "ace2": row2[2], "vace2": row2[4], "df2": row2[3], "esa2": esa2, "dvojchyby2": df2,
            "celkem_esa": celkem_esa, "celkem_df": celkem_df
        }
    })
