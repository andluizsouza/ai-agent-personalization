"""
Script para criar banco de dados SQL com informações de clientes baseadas em cervejarias reais
"""
import sqlite3
import json
import random
import string

# Lista de cervejas AB-InBev
AB_INBEV_BEERS = [
    "Budweiser",
    "Corona Extra",
    "Michelob ULTRA",
    "Stella Artois",
    "Aguila",
    "Brahma",
    "Carling Black Label",
    "Cass Fresh",
    "Jupiler",
    "Quilmes",
    "SKOL",
    "Victoria",
    "Budweiser Zero",
    "Corona 0.0",
    "Stella Artois Liberté"
]

# Dados de cervejarias do Open Brewery DB (seleção de 20 cervejarias diversas)
BREWERIES_DATA = [
    {
        "name": "10 Barrel Brewing Co",
        "city": "Bend",
        "state": "Oregon",
        "postal_code": "97702",
        "brewery_type": "large"
    },
    {
        "name": "Against the Grain Brewery",
        "city": "Louisville",
        "state": "Kentucky",
        "postal_code": "40203",
        "brewery_type": "brewpub"
    },
    {
        "name": "Ballast Point Brewing Company",
        "city": "San Diego",
        "state": "California",
        "postal_code": "92121",
        "brewery_type": "large"
    },
    {
        "name": "Brooklyn Brewery",
        "city": "Brooklyn",
        "state": "New York",
        "postal_code": "11249",
        "brewery_type": "regional"
    },
    {
        "name": "Deschutes Brewery",
        "city": "Bend",
        "state": "Oregon",
        "postal_code": "97702",
        "brewery_type": "regional"
    },
    {
        "name": "Dogfish Head Craft Brewery",
        "city": "Milton",
        "state": "Delaware",
        "postal_code": "19968",
        "brewery_type": "regional"
    },
    {
        "name": "Founders Brewing Co",
        "city": "Grand Rapids",
        "state": "Michigan",
        "postal_code": "49503",
        "brewery_type": "regional"
    },
    {
        "name": "Great Lakes Brewing Company",
        "city": "Cleveland",
        "state": "Ohio",
        "postal_code": "44113",
        "brewery_type": "regional"
    },
    {
        "name": "Lagunitas Brewing Company",
        "city": "Petaluma",
        "state": "California",
        "postal_code": "94952",
        "brewery_type": "regional"
    },
    {
        "name": "New Belgium Brewing Company",
        "city": "Fort Collins",
        "state": "Colorado",
        "postal_code": "80524",
        "brewery_type": "regional"
    },
    {
        "name": "Odell Brewing Co",
        "city": "Fort Collins",
        "state": "Colorado",
        "postal_code": "80524",
        "brewery_type": "regional"
    },
    {
        "name": "Russian River Brewing Company",
        "city": "Santa Rosa",
        "state": "California",
        "postal_code": "95401",
        "brewery_type": "micro"
    },
    {
        "name": "Samuel Adams Brewery",
        "city": "Boston",
        "state": "Massachusetts",
        "postal_code": "02130",
        "brewery_type": "large"
    },
    {
        "name": "Sierra Nevada Brewing Co",
        "city": "Chico",
        "state": "California",
        "postal_code": "95928",
        "brewery_type": "regional"
    },
    {
        "name": "Stone Brewing",
        "city": "Escondido",
        "state": "California",
        "postal_code": "92029",
        "brewery_type": "regional"
    },
    {
        "name": "Summit Brewing Company",
        "city": "Saint Paul",
        "state": "Minnesota",
        "postal_code": "55104",
        "brewery_type": "regional"
    },
    {
        "name": "The Alchemist Brewery",
        "city": "Stowe",
        "state": "Vermont",
        "postal_code": "05672",
        "brewery_type": "micro"
    },
    {
        "name": "Three Floyds Brewing Co",
        "city": "Munster",
        "state": "Indiana",
        "postal_code": "46321",
        "brewery_type": "micro"
    },
    {
        "name": "Victory Brewing Company",
        "city": "Downingtown",
        "state": "Pennsylvania",
        "postal_code": "19335",
        "brewery_type": "regional"
    },
    {
        "name": "Wicked Weed Brewing",
        "city": "Asheville",
        "state": "North Carolina",
        "postal_code": "28801",
        "brewery_type": "micro"
    }
]

# Tipos de cervejarias possíveis
BREWERY_TYPES = ["micro", "brewpub", "large", "regional", "contract", "proprietor", "planning"]

def generate_client_id():
    """Gera um código de cliente aleatório (ex: CLT-A7X9K2)"""
    letters = ''.join(random.choices(string.ascii_uppercase, k=3))
    numbers = ''.join(random.choices(string.digits, k=3))
    return f"CLT-{letters}{numbers}"

def generate_top3_brewery_types(main_type):
    """Gera top 3 tipos de cervejarias com base no tipo principal"""
    types = [main_type]
    remaining = [t for t in BREWERY_TYPES if t != main_type]
    types.extend(random.sample(remaining, min(2, len(remaining))))
    return json.dumps(types)

def generate_top5_beers_recently():
    """Seleciona as 5 cervejas que o cliente mais comprou nos últimos 90 dias"""
    return json.dumps(random.sample(AB_INBEV_BEERS, 5))

def generate_top3_breweries_recently(current_brewery_name):
    """Gera lista das 3 cervejarias que o cliente mais comprou nos últimos 90 dias"""
    # Lista de todas as cervejarias disponíveis exceto a cervejaria atual do cliente
    all_breweries = [b["name"] for b in BREWERIES_DATA if b["name"] != current_brewery_name]
    
    # Seleciona aleatoriamente 3 cervejarias
    top3 = random.sample(all_breweries, min(3, len(all_breweries)))
    
    # Retorna como JSON array
    return json.dumps(top3)

def create_database():
    """Cria o banco de dados SQLite com 20 clientes"""
    
    # Conecta ao banco (cria se não existe)
    conn = sqlite3.connect('data/customers.db')
    cursor = conn.cursor()
    
    # Remove a tabela antiga se existir
    cursor.execute('DROP TABLE IF EXISTS customers')
    
    # Cria a tabela
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            client_id TEXT PRIMARY KEY,
            client_name TEXT NOT NULL,
            client_city TEXT NOT NULL,
            client_state TEXT NOT NULL,
            postal_code TEXT NOT NULL,
            top3_brewery_types TEXT NOT NULL,
            top5_beers_recently TEXT NOT NULL,
            top3_breweries_recently TEXT NOT NULL
        )
    ''')
    
    # Limpa a tabela se já existir dados
    cursor.execute('DELETE FROM customers')
    
    # Conjunto para garantir que os IDs sejam únicos
    used_ids = set()
    
    # Insere os 20 clientes baseados nas cervejarias
    for brewery in BREWERIES_DATA:
        # Gera um client_id único
        client_id = generate_client_id()
        while client_id in used_ids:
            client_id = generate_client_id()
        used_ids.add(client_id)
        
        client_name = brewery["name"]
        client_city = brewery["city"]
        client_state = brewery["state"]
        postal_code = brewery["postal_code"]
        top3_brewery_types = generate_top3_brewery_types(brewery["brewery_type"])
        top5_beers_recently = generate_top5_beers_recently()
        top3_breweries_recently = generate_top3_breweries_recently(client_name)
        
        cursor.execute('''
            INSERT INTO customers (
                client_id,
                client_name, 
                client_city, 
                client_state, 
                postal_code,
                top3_brewery_types,
                top5_beers_recently,
                top3_breweries_recently
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client_id,
            client_name,
            client_city,
            client_state,
            postal_code,
            top3_brewery_types,
            top5_beers_recently,
            top3_breweries_recently
        ))
    
    # Commit e fecha
    conn.commit()
    
    # Verifica os dados inseridos
    cursor.execute('SELECT COUNT(*) FROM customers')
    count = cursor.fetchone()[0]
    print(f"OK Banco de dados criado com sucesso!")
    print(f"OK Total de clientes inseridos: {count}")
    
    # Mostra alguns exemplos
    print("\n--- Exemplos de registros ---")
    cursor.execute('SELECT * FROM customers LIMIT 3')
    rows = cursor.fetchall()
    
    for row in rows:
        print(f"\nClient ID: {row[0]}")
        print(f"Name: {row[1]}")
        print(f"Location: {row[2]}, {row[3]}")
        print(f"Postal Code: {row[4]}")
        print(f"Top 3 Brewery Types: {json.loads(row[5])}")
        print(f"Top 5 Beers Recently (90 days): {json.loads(row[6])}")
        print(f"Top 3 Breweries Recently (90 days): {json.loads(row[7])}")
    
    conn.close()
    print(f"\nOK Banco de dados salvo como 'data/customers.db'")

if __name__ == "__main__":
    create_database()
