from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
import mysql.connector
from starlette.responses import HTMLResponse
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Připojení k databázi
def get_connection():
    return mysql.connector.connect(
        host="db4free.net",
        user="paajicek",
        password="Bohemka1905",
        database="esatenis",
        consume_results=True
    )

# Výpočet es
def calculate_aces(server, receiver):
    try:
        S_server = 70 if server["Gender"] == "M" else 65
        P_tour = 0.089 if receiver["Gender"] == "M" else 0.042
        ah = float(server["ah"])
        va = float(receiver["va"])
        if P_tour == 0 or ah is None or va is None:
            return 0
        return S_server * ah * (va / P_tour)
    except Exception as e:
        print("Chyba při výpočtu es:", e)
        return 0

# Výpočet dvojchyb
def calculate_double_faults(player):
    try:
        S = 70 if player["Gender"] == "M" else 65
        df = float(player["df"])
        if df is None:
            return 0
        return S * df
    except Exception as e:
        print("Chyba při výpočtu dvojchyb:", e)
        return 0

# Zápis do Google Sheets
def zapis_do_google_sheets(data):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('aceapp-460119-b692dcaf1269.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open("Aceapp").sheet1
        sheet.append_row(data)
    except Exception as e:
        print("Chyba při zápisu do Google Sheets:", e)

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT Player FROM esa_prepared ORDER BY Player")
    players = [row["Player"] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return templates.TemplateResponse("index.html", {"request": request, "players": players})

@app.get("/result", response_class=HTMLResponse)
async def result(request: Request, player1: str, player2: str):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player1,))
    p1 = cursor.fetchone()

    cursor.execute("SELECT * FROM esa_prepared WHERE Player = %s", (player2,))
    p2 = cursor.fetchone()

    cursor.close()
    conn.close()

    if not p1 or not p2:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "players": [],
            "error": "Nepodařilo se načíst data pro hráče."
        })

    e1 = calculate_aces(p1, p2)
    e2 = calculate_aces(p2, p1)
    df1 = calculate_double_faults(p1)
    df2 = calculate_double_faults(p2)
    total_aces = round(e1 + e2, 2)
    total_dfs = round(df1 + df2, 2)

    # Připravíme data k zápisu do tabulky
    zapis_data = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        p1["Player"],
        round(p1["ah"] * 100, 2),
        round(p1["va"] * 100, 2),
        round(p1["df"] * 100, 2),
        round(e1, 2),
        round(df1, 2),
        p2["Player"],
        round(p2["ah"] * 100, 2),
        round(p2["va"] * 100, 2),
        round(p2["df"] * 100, 2),
        round(e2, 2),
        round(df2, 2),
        total_aces,
        total_dfs
    ]

    zapis_do_google_sheets(zapis_data)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "players": [p1["Player"], p2["Player"]],
        "selected1": p1["Player"],
        "selected2": p2["Player"],
        "e1": round(e1, 2),
        "e2": round(e2, 2),
        "df1": round(df1, 2),
        "df2": round(df2, 2),
        "total_aces": total_aces,
        "total_dfs": total_dfs,
        "p1": p1,
        "p2": p2
    })
