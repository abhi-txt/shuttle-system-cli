import sqlite3
import hashlib
import datetime
import enum
import getpass
import textwrap 

class UserRole(enum.Enum):
    RIDER = "Rider"
    DRIVER = "Driver"
    ADMIN = "Admin"

class TripStatus(enum.Enum):
    ACTIVE = "Active"
    COMPLETED = "Completed"
    AUTO_COMPLETED = "AutoCompleted"

class TransactionType(enum.Enum):
    RIDE_PAYMENT = "RidePayment"
    ADD_FUNDS = "AddFunds"
    ADMIN_ADJUSTMENT = "AdminAdjustment" 

def setup_database():
    """
    Creates the database file and all necessary tables.
    """
    conn = sqlite3.connect('shuttle.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Rider',
        wallet_balance REAL NOT NULL DEFAULT 0.0
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shuttle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        capacity INTEGER DEFAULT 20
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stop (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS route (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        base_fare REAL NOT NULL DEFAULT 0.50,
        price_per_km REAL NOT NULL DEFAULT 0.25
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS route_stop (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL,
        stop_id INTEGER NOT NULL,
        stop_order INTEGER NOT NULL,
        distance_from_start REAL NOT NULL,
        FOREIGN KEY (route_id) REFERENCES route (id),
        FOREIGN KEY (stop_id) REFERENCES stop (id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS active_trip (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rider_id INTEGER NOT NULL,
        shuttle_id INTEGER NOT NULL,
        tap_on_route_stop_id INTEGER NOT NULL,
        tap_on_time TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active',
        FOREIGN KEY (rider_id) REFERENCES user (id),
        FOREIGN KEY (shuttle_id) REFERENCES shuttle (id),
        FOREIGN KEY (tap_on_route_stop_id) REFERENCES route_stop (id)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rider_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        related_trip_id INTEGER,
        FOREIGN KEY (rider_id) REFERENCES user (id),
        FOREIGN KEY (related_trip_id) REFERENCES active_trip (id)
    );
    """)
    conn.commit()
    conn.close()

def get_db_connection():
    """Helper function to create a database connection."""
    conn = sqlite3.connect('shuttle.db')
    conn.row_factory = sqlite3.Row 
    return conn

def hash_password(password):
    """Hashes a password for storing securely."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(stored_hash, provided_password):
    """Checks if the provided password matches the stored hash."""
    return stored_hash == hashlib.sha256(provided_password.encode()).hexdigest()

def seed_data():
    """Populates the database with initial test data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM user WHERE username = 'admin'")
    if cursor.fetchone():
        conn.close()
        return
    print("Seeding database...")
    admin_pass = hash_password("admin123")
    driver_pass = hash_password("driver123")
    rider_pass = hash_password("rider123")
    cursor.execute("""
    INSERT INTO user (username, email, password_hash, role, wallet_balance)
    VALUES 
        ('admin', 'admin@campus.edu', ?, ?, 0.0),
        ('driver1', 'driver1@campus.edu', ?, ?, 0.0),
        ('rider1', 'rider1@campus.edu', ?, ?, 10.0)
    """, (admin_pass, UserRole.ADMIN.value, 
          driver_pass, UserRole.DRIVER.value, 
          rider_pass, UserRole.RIDER.value))
    cursor.execute("INSERT INTO stop (name) VALUES ('Library'), ('Engineering Bldg'), ('Dorm Quad'), ('Student Union')")
    cursor.execute("INSERT INTO route (name, base_fare, price_per_km) VALUES ('Campus Loop', 0.50, 0.25)")
    route_id = cursor.lastrowid 
    stops = cursor.execute("SELECT id, name FROM stop").fetchall()
    stop_map = {name: id for id, name in stops} 
    route_stops = [
        (route_id, stop_map['Library'], 1, 0.0),
        (route_id, stop_map['Engineering Bldg'], 2, 0.8),
        (route_id, stop_map['Dorm Quad'], 3, 1.5),
        (route_id, stop_map['Student Union'], 4, 2.1)
    ]
    cursor.executemany("INSERT INTO route_stop (route_id, stop_id, stop_order, distance_from_start) VALUES (?, ?, ?, ?)", route_stops)
    cursor.execute("INSERT INTO shuttle (name, capacity) VALUES ('Shuttle #1', 15)")
    conn.commit()
    conn.close()
    print("Database seeding complete.")

def register_user():
    """Handles the user registration flow."""
    print("\n--- New User Registration ---")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ").strip()
    password_confirm = getpass.getpass("Confirm Password: ").strip()
    if password != password_confirm:
        print("Passwords do not match. Please try again.")
        return
    role = UserRole.RIDER.value
    hashed_password = hash_password(password)
    conn = get_db_connection()
    try:
        conn.cursor().execute(
            "INSERT INTO user (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, role)
        )
        conn.commit()
        print(f"Success! Rider account '{username}' created.")
    except sqlite3.IntegrityError as e:
        print(f"Error: Username or email already exists. {e}")
    finally:
        conn.close()

def login_user():
    """Handles the user login flow."""
    print("\n--- User Login ---")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password(user['password_hash'], password):
        print(f"\nWelcome, {user['username']}! (Role: {user['role']})")
        return user 
    else:
        print("Invalid username or password.")
        return None

def view_balance(user):
    """Fetches and displays the user's current wallet balance."""
    conn = get_db_connection()
    balance = conn.cursor().execute(
        "SELECT wallet_balance FROM user WHERE id = ?", 
        (user['id'],)
    ).fetchone()
    conn.close()
    print(f"\nYour current wallet balance is: ${balance['wallet_balance']:.2f}")

def add_funds(user):
    """Allows a user to add funds to their wallet."""
    print("\n--- Add Funds ---")
    try:
        amount = float(input("Enter amount to add: $"))
        if amount <= 0:
            print("Amount must be positive.")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE user SET wallet_balance = wallet_balance + ? WHERE id = ?", (amount, user['id']))
        cursor.execute(
            """
            INSERT INTO transaction_log (rider_id, amount, type, timestamp) 
            VALUES (?, ?, ?, ?)
            """,
            (user['id'], amount, TransactionType.ADD_FUNDS.value, datetime.datetime.now().isoformat())
        )
        conn.commit()
        print(f"${amount:.2f} successfully added.")
        view_balance(user) 
    except ValueError:
        print("Invalid amount. Please enter a number.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback() 
    finally:
        if conn:
            conn.close()

def view_ride_history(user):
    """Displays a user's past ride transactions."""
    print("\n--- Your Ride History ---")
    conn = get_db_connection()
    history = conn.cursor().execute(
        """
        SELECT timestamp, amount, related_trip_id 
        FROM transaction_log
        WHERE rider_id = ? AND type = ?
        ORDER BY timestamp DESC
        """,
        (user['id'], TransactionType.RIDE_PAYMENT.value)
    ).fetchall()
    conn.close()
    if not history:
        print("You have no ride history.")
        return
    print("Date & Time            | Amount  | Trip ID")
    print("-" * 40)
    for ride in history:
        ts = datetime.datetime.fromisoformat(ride['timestamp']).strftime('%Y-%m-%d %H:%M')
        print(f"{ts:<20} | ${ride['amount'] * -1:<7.2f} | {ride['related_trip_id']}")

def view_all_users():
    """Admin function to view all users."""
    print("\n--- All System Users ---")
    conn = get_db_connection()
    users = conn.cursor().execute(
        "SELECT id, username, email, role, wallet_balance FROM user"
    ).fetchall()
    conn.close()
    print("ID | Username   | Email            | Role    | Balance")
    print("-" * 55)
    for user in users:
        print(f"{user['id']:<2} | {user['username']:<10} | {user['email']:<16} | {user['role']:<7} | ${user['wallet_balance']:.2f}")

def view_all_transactions():
    """Admin function to view all transactions."""
    print("\n--- All System Transactions ---")
    conn = get_db_connection()
    txns = conn.cursor().execute(
        """
        SELECT t.id, t.timestamp, u.username, t.type, t.amount
        FROM transaction_log t
        JOIN user u ON t.rider_id = u.id
        ORDER BY t.timestamp DESC
        """
    ).fetchall()
    conn.close()
    if not txns:
        print("No transactions found.")
        return
        
    print("ID  | Date & Time            | Username   | Type          | Amount")
    print("-" * 70)
    for t in txns:
        ts = datetime.datetime.fromisoformat(t['timestamp']).strftime('%Y-%m-%d %H:%M')
        print(f"{t['id']:<3} | {ts:<20} | {t['username']:<10} | {t['type']:<13} | ${t['amount']:.2f}")

def create_stop():
    """Admin function to create a new stop."""
    print("\n--- Create New Stop ---")
    name = input("Enter new stop name: ").strip()
    if not name:
        print("Name cannot be empty.")
        return
    conn = get_db_connection()
    try:
        conn.cursor().execute("INSERT INTO stop (name) VALUES (?)", (name,))
        conn.commit()
        print(f"Success: Stop '{name}' created.")
    except sqlite3.IntegrityError:
        print(f"Error: Stop name '{name}' already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

def create_shuttle():
    """Admin function to create a new shuttle."""
    print("\n--- Create New Shuttle ---")
    try:
        name = input("Enter shuttle name (e.g., 'Shuttle #2'): ").strip()
        capacity = int(input("Enter shuttle capacity: "))
        if not name:
            print("Name cannot be empty.")
            return
        conn = get_db_connection()
        conn.cursor().execute("INSERT INTO shuttle (name, capacity) VALUES (?, ?)", (name, capacity))
        conn.commit()
        conn.close()
        print(f"Success: Shuttle '{name}' created with capacity {capacity}.")
    except ValueError:
        print("Error: Capacity must be an integer.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_route():
    """Admin function to create a new route."""
    print("\n--- Create New Route ---")
    try:
        name = input("Enter new route name (e.g., 'Express Library'): ").strip()
        base_fare = float(input("Enter base fare (e.g., 0.75): $"))
        price_per_km = float(input("Enter price per km (e.g., 0.30): $"))
        if not name:
            print("Name cannot be empty.")
            return
        conn = get_db_connection()
        conn.cursor().execute(
            "INSERT INTO route (name, base_fare, price_per_km) VALUES (?, ?, ?)",
            (name, base_fare, price_per_km)
        )
        conn.commit()
        conn.close()
        print(f"Success: Route '{name}' created.")
    except ValueError:
        print("Error: Fares must be numbers.")
    except sqlite3.IntegrityError:
        print(f"Error: Route name '{name}' already exists.")
    except Exception as e:
        print(f"An error occurred: {e}")

def add_stop_to_route():
    """Admin function to add an existing stop to an existing route."""
    print("\n--- Add Stop to Route ---")
    conn = get_db_connection()
    try:
        routes = conn.cursor().execute("SELECT id, name FROM route").fetchall()
        print("Available Routes:")
        for r in routes:
            print(f"  ID {r['id']}: {r['name']}")
        route_id = int(input("Enter Route ID to modify: "))
        stops = conn.cursor().execute("SELECT id, name FROM stop").fetchall()
        print("\nAvailable Stops:")
        for s in stops:
            print(f"  ID {s['id']}: {s['name']}")
        stop_id = int(input("Enter Stop ID to add: "))
        stop_order = int(input("Enter stop order (e.g., 1, 2, 3...): "))
        distance_from_start = float(input("Enter distance from start (in km): "))
        conn.cursor().execute(
            "INSERT INTO route_stop (route_id, stop_id, stop_order, distance_from_start) VALUES (?, ?, ?, ?)",
            (route_id, stop_id, stop_order, distance_from_start)
        )
        conn.commit()
        print("Success: Stop added to route.")
    except ValueError:
        print("Error: IDs and order must be integers, distance must be a number.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        conn.close()

def adjust_user_balance():
    """Admin function to manually add or remove funds from a user."""
    print("\n--- Adjust User Balance ---")
    try:
        username = input("Enter username of the user to adjust: ").strip()
        amount = float(input("Enter amount to add (use negative for removal): $"))
        reason = input("Enter reason for adjustment (e.g., 'Refund'): ").strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        user = cursor.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
        if not user:
            print(f"Error: User '{username}' not found.")
            conn.close()
            return
        cursor.execute(
            "UPDATE user SET wallet_balance = wallet_balance + ? WHERE id = ?",
            (amount, user['id'])
        )
        cursor.execute(
            """
            INSERT INTO transaction_log (rider_id, amount, type, timestamp) 
            VALUES (?, ?, ?, ?)
            """,
            (user['id'], amount, TransactionType.ADMIN_ADJUSTMENT.value, datetime.datetime.now().isoformat())
        )
        conn.commit()
        print(f"Success: User '{username}'s balance adjusted by ${amount:.2f}.")
    except ValueError:
        print("Error: Amount must be a number.")
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()

def process_rider_tap(rider_username, current_route_stop, shuttle_id):
    """
    The main "brain" of the system.
    Processes a single tap from a rider on the driver's device.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        rider = cursor.execute("SELECT * FROM user WHERE username = ?", (rider_username,)).fetchone()
        if not rider:
            print(f"Error: Rider '{rider_username}' not found.")
            return
        current_stop_data = cursor.execute(
            "SELECT * FROM route_stop WHERE id = ?", (current_route_stop['id'],)
        ).fetchone()
        route_data = cursor.execute(
            "SELECT * FROM route WHERE id = ?", (current_stop_data['route_id'],)
        ).fetchone()
        active_trip = cursor.execute(
            "SELECT * FROM active_trip WHERE rider_id = ? AND status = ?",
            (rider['id'], TripStatus.ACTIVE.value)
        ).fetchone()
        if active_trip:
            tap_on_stop_data = cursor.execute(
                "SELECT * FROM route_stop WHERE id = ?", (active_trip['tap_on_route_stop_id'],)
            ).fetchone()
            if active_trip['tap_on_route_stop_id'] == current_stop_data['id']:
                print(f"[{rider['username']}] ALREADY TAPPED ON at this stop. Tap ignored.")
                return
            if tap_on_stop_data['route_id'] == current_stop_data['route_id']:
                print(f"[{rider['username']}] Tapping OFF...")
                dist_on = tap_on_stop_data['distance_from_start']
                dist_off = current_stop_data['distance_from_start']
                distance_traveled = abs(dist_off - dist_on)
                fare = route_data['base_fare'] + (distance_traveled * route_data['price_per_km'])
                fare = round(fare, 2) 
                new_balance = rider['wallet_balance'] - fare
                cursor.execute("UPDATE user SET wallet_balance = ? WHERE id = ?", (new_balance, rider['id']))
                cursor.execute(
                    """
                    INSERT INTO transaction_log (rider_id, amount, type, timestamp, related_trip_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (rider['id'], -fare, TransactionType.RIDE_PAYMENT.value, datetime.datetime.now().isoformat(), active_trip['id'])
                )
                cursor.execute("UPDATE active_trip SET status = ? WHERE id = ?", (TripStatus.COMPLETED.value, active_trip['id']))
                print(f"  Fare: ${fare:.2f}. New Balance: ${new_balance:.2f}")
            else:
                print(f"[{rider['username']}] FORGOT TO TAP OFF on a previous trip.")
                old_route_id = tap_on_stop_data['route_id']
                last_stop_data = cursor.execute(
                    "SELECT * FROM route_stop WHERE route_id = ? ORDER BY stop_order DESC LIMIT 1",
                    (old_route_id,)
                ).fetchone()
                old_route_data = cursor.execute("SELECT * FROM route WHERE id = ?", (old_route_id,)).fetchone()
                max_dist = abs(last_stop_data['distance_from_start'] - tap_on_stop_data['distance_from_start'])
                max_fare = old_route_data['base_fare'] + (max_dist * old_route_data['price_per_km'])
                max_fare = round(max_fare, 2)
                new_balance = rider['wallet_balance'] - max_fare
                cursor.execute("UPDATE user SET wallet_balance = ? WHERE id = ?", (new_balance, rider['id']))
                cursor.execute(
                    "INSERT INTO transaction_log (rider_id, amount, type, timestamp, related_trip_id) VALUES (?, ?, ?, ?, ?)",
                    (rider['id'], -max_fare, TransactionType.RIDE_PAYMENT.value, datetime.datetime.now().isoformat(), active_trip['id'])
                )
                cursor.execute("UPDATE active_trip SET status = ? WHERE id = ?", (TripStatus.AUTO_COMPLETED.value, active_trip['id']))
                print(f"  Charged max fare: ${max_fare:.2f}. New Balance: ${new_balance:.2f}")
                rider = cursor.execute("SELECT * FROM user WHERE id = ?", (rider['id'],)).fetchone()
                active_trip = None 
        if not active_trip:
            print(f"[{rider['username']}] Tapping ON...")
            if rider['wallet_balance'] < route_data['base_fare']:
                print(f"  TAP-ON FAILED. Insufficient funds (Min: ${route_data['base_fare']:.2f}, Has: ${rider['wallet_balance']:.2f})")
                return
            cursor.execute(
                """
                INSERT INTO active_trip (rider_id, shuttle_id, tap_on_route_stop_id, tap_on_time, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (rider['id'], shuttle_id, current_stop_data['id'], datetime.datetime.now().isoformat(), TripStatus.ACTIVE.value)
            )
            print("  TAP-ON Successful. Trip started.")
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback() 
    finally:
        conn.close()

def handle_end_of_shift(shuttle_id):
    """
    Finds all active trips on a shuttle and auto-completes them
    by charging the max fare for their respective routes.
    """
    print("\nEnding shift. Checking for active riders...")
    conn = get_db_connection()
    cursor = conn.cursor()
    active_trips = cursor.execute(
        "SELECT * FROM active_trip WHERE shuttle_id = ? AND status = ?",
        (shuttle_id, TripStatus.ACTIVE.value)
    ).fetchall()
    if not active_trips:
        print("No active trips to resolve.")
        conn.close()
        return
    print(f"Resolving {len(active_trips)} active trip(s) for end of shift...")
    for trip in active_trips:
        try:
            rider = cursor.execute("SELECT * FROM user WHERE id = ?", (trip['rider_id'],)).fetchone()
            tap_on_stop_data = cursor.execute(
                "SELECT * FROM route_stop WHERE id = ?", (trip['tap_on_route_stop_id'],)
            ).fetchone()
            route_id = tap_on_stop_data['route_id']
            route_data = cursor.execute("SELECT * FROM route WHERE id = ?", (route_id,)).fetchone()
            last_stop_data = cursor.execute(
                "SELECT * FROM route_stop WHERE route_id = ? ORDER BY stop_order DESC LIMIT 1",
                (route_id,)
            ).fetchone()
            max_dist = abs(last_stop_data['distance_from_start'] - tap_on_stop_data['distance_from_start'])
            max_fare = route_data['base_fare'] + (max_dist * route_data['price_per_km'])
            max_fare = round(max_fare, 2)
            new_balance = rider['wallet_balance'] - max_fare
            cursor.execute("UPDATE user SET wallet_balance = ? WHERE id = ?", (new_balance, rider['id']))
            cursor.execute(
                "INSERT INTO transaction_log (rider_id, amount, type, timestamp, related_trip_id) VALUES (?, ?, ?, ?, ?)",
                (rider['id'], -max_fare, TransactionType.RIDE_PAYMENT.value, datetime.datetime.now().isoformat(), trip['id'])
            )
            cursor.execute("UPDATE active_trip SET status = ? WHERE id = ?", (TripStatus.AUTO_COMPLETED.value, trip['id']))
            print(f"  Auto-completed trip for {rider['username']}. Charged max fare: ${max_fare:.2f}.")
        except Exception as e:
            print(f"  Error resolving trip {trip['id']}: {e}")
    conn.commit()
    conn.close()

def start_driver_session(driver_user):
    """The main interface for a driver's active shift."""
    conn = get_db_connection()
    try:
        shuttles = conn.execute("SELECT * FROM shuttle").fetchall()
        print("\n--- Select Your Shuttle ---")
        for s in shuttles:
            print(f"{s['id']}: {s['name']} (Capacity: {s['capacity']})")
        shuttle_id = int(input("Enter shuttle ID: "))
        shuttle = conn.execute("SELECT * FROM shuttle WHERE id = ?", (shuttle_id,)).fetchone()
        if not shuttle:
            print("Invalid shuttle ID.")
            conn.close()
            return
        routes = conn.execute("SELECT * FROM route").fetchall()
        print("\n--- Select Your Route ---")
        for r in routes:
            print(f"{r['id']}: {r['name']} (Base: ${r['base_fare']:.2f}, Per/km: ${r['price_per_km']:.2f})")
        route_id = int(input("Enter route ID: "))
        all_stops = conn.execute(
            """
            SELECT rs.id, rs.stop_order, rs.distance_from_start, s.name, r.name AS route_name
            FROM route_stop rs
            JOIN stop s ON rs.stop_id = s.id
            JOIN route r ON rs.route_id = r.id
            WHERE rs.route_id = ?
            ORDER BY rs.stop_order
            """, (route_id,)
        ).fetchall()
        conn.close()
        if not all_stops:
            print("Error: This route has no stops defined. Returning to menu.")
            return
        current_stop_index = 0
        total_stops = len(all_stops)
        print(f"\n--- SESSION STARTED ---")
        print(f"Driver: {driver_user['username']}, Shuttle: {shuttle['name']}, Route: {all_stops[0]['route_name']}")
        
        while True:
            current_stop = all_stops[current_stop_index]
            print("\n" + "="*40)
            print(f"  Current Stop: ({current_stop['stop_order']}/{total_stops}) {current_stop['name']}")
            print("="*40)
            print("Commands: [next] stop, [tap] rider, [end] session")
            cmd = input("Enter command: ").strip().lower()
            if cmd == 'next':
                current_stop_index = (current_stop_index + 1) % total_stops
                print(f"Moving to next stop...")
            elif cmd == 'tap':
                rider_username = input("  Enter rider username to tap: ").strip()
                if rider_username:
                    process_rider_tap(rider_username, current_stop, shuttle_id)
            elif cmd == 'end':
                handle_end_of_shift(shuttle_id)
                print("Ending driving session...")
                break
            else:
                print("Invalid command.")   
    except ValueError:
        print("Invalid ID. Returning to menu.")
        if conn:
            conn.close()
    except Exception as e:
        print(f"An error occurred in driver session: {e}")
        if conn:
            conn.close()

def rider_menu(user):
    """Displays the menu for a logged-in Rider."""
    while True:
        print("\n--- Rider Dashboard ---")
        print("1. View My Balance")
        print("2. Add Funds to Wallet")
        print("3. View My Ride History")
        print("9. Logout")
        choice = input("Enter choice: ")
        if choice == '1':
            view_balance(user)
        elif choice == '2':
            add_funds(user)
        elif choice == '3':
            view_ride_history(user)
        elif choice == '9':
            print(f"Logging out {user['username']}...")
            return 
        else:
            print("Invalid choice. Please try again.")

def driver_menu(user):
    """Displays the menu for a logged-in Driver."""
    while True:
        print("\n--- Driver Dashboard ---")
        print("1. Start Driving Session")
        print("9. Logout")
        choice = input("Enter choice: ")
        if choice == '1':
            start_driver_session(user)
        elif choice == '9':
            print(f"Logging out {user['username']}...")
            return 
        else:
            print("Invalid choice. Please try again.")

def admin_menu(user):
    """Displays the menu for a logged-in Admin."""
    while True:
        print("\n--- Admin Dashboard ---")
        print("--- View Data ---")
        print("  1. View All Users")
        print("  2. View All Transactions")
        print("--- Manage System ---")
        print("  3. Create New Stop")
        print("  4. Create New Shuttle")
        print("  5. Create New Route")
        print("  6. Add Stop to Route")
        print("  7. Adjust User Balance")
        print("---")
        print("  9. Logout")
        choice = input("Enter choice: ")
        if choice == '1':
            view_all_users()
        elif choice == '2':
            view_all_transactions()
        elif choice == '3':
            create_stop()
        elif choice == '4':
            create_shuttle()
        elif choice == '5':
            create_route()
        elif choice == '6':
            add_stop_to_route()
        elif choice == '7':
            adjust_user_balance()
        elif choice == '9':
            print(f"Logging out {user['username']}...")
            return 
        else:
            print("Invalid choice. Please try again.")

def main_menu():
    """The main entry point of the CLI application."""
    current_user = None 
    while True:
        if current_user:
            role = current_user['role']
            if role == UserRole.RIDER.value:
                rider_menu(current_user)
            elif role == UserRole.DRIVER.value:
                driver_menu(current_user)
            elif role == UserRole.ADMIN.value:
                admin_menu(current_user)
            current_user = None
        else:
            print("\n--- Welcome to the Shuttle System ---")
            print("1. Login")
            print("2. Register New Rider Account")
            print("3. Exit")
            choice = input("Enter choice: ")
            if choice == '1':
                current_user = login_user() 
            elif choice == '2':
                register_user()
            elif choice == '3':
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")

if __name__ == "__main__":
    setup_database()
    seed_data()
    main_menu() 
