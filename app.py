import sqlite3
import uuid

# Fonction de connexion à la base de données
def connect_db():
    return sqlite3.connect('wallet_system.db')

# Fonction de création des tables
def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    # Table des administrateurs (admins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance INTEGER DEFAULT 999999999  -- Solde initial de l'admin
        )
    ''')

    # Table des commerçants
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS merchants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            wallet_id TEXT UNIQUE NOT NULL,
            balance INTEGER DEFAULT 0
        )
    ''')

    # Table des clients
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            merchant_id TEXT NOT NULL,
            balance INTEGER DEFAULT 0,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    ''')

    # Table des transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,  -- Peut être NULL pour les transactions sans administrateur
            merchant_id TEXT,
            client_id INTEGER,
            transaction_type TEXT NOT NULL,
            amount INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admins(id),
            FOREIGN KEY (merchant_id) REFERENCES merchants(id),
            FOREIGN KEY (client_id) REFERENCES clients(id)
        )
    ''')

    conn.commit()
    conn.close()

# Ajouter un administrateur
def add_admin(username, password):
    conn = connect_db()
    cursor = conn.cursor()

    # Vérifier s'il y a déjà un administrateur
    cursor.execute("SELECT * FROM admins")
    if cursor.fetchone():
        print("Erreur : Un administrateur existe déjà.")
        conn.close()
        return

    cursor.execute('INSERT INTO admins (username, password) VALUES (?, ?)', (username, password))
    conn.commit()
    print(f"Administrateur '{username}' ajouté avec succès.")
    conn.close()

# Afficher les informations de l'administrateur
def get_admin_info(username):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, balance FROM admins WHERE username = ?", (username,))
    admin_info = cursor.fetchone()

    if admin_info:
        admin_id, balance = admin_info
        print(f"ID de l'administrateur : {admin_id}")
        print(f"Solde actuel de l'administrateur : {balance} pièces.")
    else:
        print("Erreur : Administrateur non trouvé.")

    conn.close()

# Ajouter un commerçant
def add_merchant(name):
    conn = connect_db()
    cursor = conn.cursor()

    wallet_id = str(uuid.uuid4())  # Générer un identifiant unique pour le portefeuille
    merchant_id = str(uuid.uuid4())  # Générer un identifiant unique pour le commerçant
    cursor.execute('INSERT INTO merchants (id, name, wallet_id) VALUES (?, ?, ?)', (merchant_id, name, wallet_id))
    conn.commit()
    print(f"Commerçant '{name}' ajouté avec succès. ID du portefeuille : {wallet_id}, ID du commerçant : {merchant_id}")
    conn.close()

# Ajouter un client
def add_client(name, merchant_id):
    conn = connect_db()
    cursor = conn.cursor()

    # Vérifier si le commerçant existe
    cursor.execute('SELECT * FROM merchants WHERE id = ?', (merchant_id,))
    merchant = cursor.fetchone()
    if not merchant:
        print("Erreur : Commerçant non trouvé.")
        conn.close()
        return

    cursor.execute('INSERT INTO clients (name, merchant_id) VALUES (?, ?)', (name, merchant_id))
    conn.commit()
    print(f"Client '{name}' ajouté avec succès.")
    conn.close()

# Louer des pièces aux commerçants par l'administrateur
def rent_coins(admin_username, merchant_id, amount):
    conn = connect_db()
    cursor = conn.cursor()

    # Vérifier le solde de l'administrateur par son nom d'utilisateur
    cursor.execute("SELECT id, balance FROM admins WHERE username = ?", (admin_username,))
    admin_info = cursor.fetchone()

    if admin_info is None:
        print("Erreur : Administrateur non trouvé.")
        conn.close()
        return

    admin_id, admin_balance = admin_info

    # Vérifier que l'administrateur a suffisamment de pièces
    if admin_balance < amount:
        print("Erreur : Solde insuffisant de l'administrateur.")
        conn.close()
        return

    # Louer les pièces au commerçant et déduire du solde de l'administrateur
    cursor.execute("UPDATE admins SET balance = balance - ? WHERE id = ?", (amount, admin_id))
    cursor.execute("UPDATE merchants SET balance = balance + ? WHERE id = ?", (amount, merchant_id))

    # Enregistrement de la transaction
    cursor.execute('''
        INSERT INTO transactions (admin_id, merchant_id, transaction_type, amount)
        VALUES (?, ?, ?, ?)
    ''', (admin_id, merchant_id, 'rent', amount))

    conn.commit()
    print(f"{amount} pièces louées au commerçant avec l'ID : {merchant_id}.")
    conn.close()

# Distribuer des pièces aux clients par les commerçants
def distribute_coins_to_client(client_name, amount):
    conn = connect_db()
    cursor = conn.cursor()

    # Récupérer l'ID du commerçant lié au client
    cursor.execute('SELECT id, merchant_id FROM clients WHERE name = ?', (client_name,))
    result = cursor.fetchone()
    if result is None:
        print("Erreur : Client non trouvé.")
        conn.close()
        return

    client_id, merchant_id = result

    # Vérifier le solde du commerçant
    cursor.execute('SELECT balance FROM merchants WHERE id = ?', (merchant_id,))
    merchant_balance_result = cursor.fetchone()
    
    if merchant_balance_result is None:
        print("Erreur : Portefeuille du commerçant non trouvé.")
        conn.close()
        return

    merchant_balance = merchant_balance_result[0]
    if merchant_balance >= amount:
        # Déduire le montant du commerçant
        new_merchant_balance = merchant_balance - amount
        cursor.execute('UPDATE merchants SET balance = ? WHERE id = ?', (new_merchant_balance, merchant_id))

        # Ajouter le montant au client
        cursor.execute('UPDATE clients SET balance = balance + ? WHERE id = ?', (amount, client_id))

        # Enregistrement de la transaction sans admin_id
        cursor.execute('''
            INSERT INTO transactions (merchant_id, client_id, transaction_type, amount)
            VALUES (?, ?, ?, ?)
        ''', (merchant_id, client_id, 'distribute', amount))
        
        conn.commit()
        print(f"{amount} pièces virtuelles distribuées au client '{client_name}'. Nouveau solde du commerçant : {new_merchant_balance}.")
    else:
        print("Erreur : Solde du commerçant insuffisant.")

    conn.close()

# Récupérer des pièces d'un client par un commerçant
def return_coins_from_client(client_name, amount):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('SELECT id, merchant_id, balance FROM clients WHERE name = ?', (client_name,))
    result = cursor.fetchone()
    if result is None:
        print("Erreur : Client non trouvé.")
        conn.close()
        return

    client_id, merchant_id, client_balance = result
    if client_balance < amount:
        print("Erreur : Solde du client insuffisant.")
        conn.close()
        return

    # Déduire le montant du client
    new_client_balance = client_balance - amount
    cursor.execute('UPDATE clients SET balance = ? WHERE id = ?', (new_client_balance, client_id))

    # Ajouter le montant au commerçant
    cursor.execute('SELECT balance FROM merchants WHERE id = ?', (merchant_id,))
    merchant_balance = cursor.fetchone()[0]
    new_merchant_balance = merchant_balance + amount
    cursor.execute('UPDATE merchants SET balance = ? WHERE id = ?', (new_merchant_balance, merchant_id))

    # Enregistrement de la transaction
    cursor.execute('''
        INSERT INTO transactions (merchant_id, client_id, transaction_type, amount)
        VALUES (?, ?, ?, ?)
    ''', (merchant_id, client_id, 'return', amount))

    conn.commit()
    print(f"{amount} pièces récupérées du client '{client_name}'.")
    conn.close()

# Mettre à jour le solde de l'administrateur
def update_admin_balance(username, new_balance):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE admins SET balance = ? WHERE username = ?", (new_balance, username))
    conn.commit()
    print(f"Solde de l'administrateur '{username}' mis à jour à {new_balance} pièces.")
    conn.close()

# Lister les commerçants
def list_merchants():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, wallet_id, balance FROM merchants")
    merchants = cursor.fetchall()

    if merchants:
        print("\nListe des commerçants :")
        for merchant in merchants:
            print(f"ID : {merchant[0]}, Nom : {merchant[1]}, ID du portefeuille : {merchant[2]}, Solde : {merchant[3]}")
    else:
        print("Aucun commerçant trouvé.")

    conn.close()

# Lister les clients
def list_clients():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, merchant_id, balance FROM clients")
    clients = cursor.fetchall()

    if clients:
        print("\nListe des clients :")
        for client in clients:
            print(f"ID : {client[0]}, Nom : {client[1]}, ID du commerçant : {client[2]}, Solde : {client[3]}")
    else:
        print("Aucun client trouvé.")

    conn.close()

# Fonction principale pour le menu
def main():
    create_tables()  # Assurez-vous que les tables sont créées avant de commencer

    while True:
        print("\nMenu :")
        print("1. Ajouter un administrateur")
        print("2. Afficher les informations de l'administrateur")
        print("3. Ajouter un commerçant")
        print("4. Ajouter un client")
        print("5. Louer des pièces aux commerçants")
        print("6. Distribuer des pièces aux clients")
        print("7. Récupérer des pièces d'un client")
        print("8. Mettre à jour le solde de l'administrateur")
        print("9. Lister les commerçants")
        print("10. Lister les clients")
        print("11. Quitter")

        choice = input("Choisissez une option (1-11) : ")

        if choice == '1':
            username = input("Nom d'utilisateur de l'administrateur : ")
            password = input("Mot de passe de l'administrateur : ")
            add_admin(username, password)
        elif choice == '2':
            username = input("Nom d'utilisateur de l'administrateur : ")
            get_admin_info(username)
        elif choice == '3':
            name = input("Nom du commerçant : ")
            add_merchant(name)
        elif choice == '4':
            name = input("Nom du client : ")
            merchant_id = input("ID du commerçant : ")
            add_client(name, merchant_id)
        elif choice == '5':
            admin_username = input("Nom d'utilisateur de l'administrateur : ")
            merchant_id = input("ID du commerçant : ")
            amount = int(input("Montant à louer : "))
            rent_coins(admin_username, merchant_id, amount)
        elif choice == '6':
            client_name = input("Nom du client : ")
            amount = int(input("Montant à distribuer : "))
            distribute_coins_to_client(client_name, amount)
        elif choice == '7':
            client_name = input("Nom du client : ")
            amount = int(input("Montant à récupérer : "))
            return_coins_from_client(client_name, amount)
        elif choice == '8':
            username = input("Nom d'utilisateur de l'administrateur : ")
            new_balance = int(input("Nouveau solde : "))
            update_admin_balance(username, new_balance)
        elif choice == '9':
            list_merchants()
        elif choice == '10':
            list_clients()
        elif choice == '11':
            print("Quitter l'application.")
            break
        else:
            print("Option invalide, veuillez réessayer.")

if __name__ == "__main__":
    main()
