# Campus Shuttle Management System (CLI)

This project is a complete, self-contained Python application that simulates a campus shuttle management system. It runs entirely within a command-line interface (CLI) and uses a local `sqlite3` database to manage all data.

The system is built on a "tap-on / tap-off" model, where a driver's interface simulates an NFC reader. It features role-based access for Admins, Drivers, and Riders, and includes a full-featured digital wallet and dynamic, distance-based fare calculation.

## Features

### Core System

  * **Pure Python:** Runs as a single script with no external dependencies (uses built-in `sqlite3`, `hashlib`, and `getpass`).
  * **SQL-based Database:** Automatically creates a `shuttle.db` file to store all persistent data.
  * **Data Seeding:** On first run, automatically populates the database with test users, stops, a shuttle, and a complete, ready-to-use route ("Campus Loop").
  * **Secure Authentication:** Includes user registration and login with SHA-256 password hashing.

### Role-Based Access

**1. Rider**

  * Create an account and log in.
  * View current wallet balance.
  * Add funds to their digital wallet.
  * View a complete history of all past rides and their costs.

**2. Admin**

  * View a list of all users in the system (Riders, Drivers, Admins).
  * View a log of all transactions (ride payments, fund additions, adjustments).
  * **Full System Management:**
      * Create new shuttle stops.
      * Create new shuttles.
      * Create new routes with custom fare models (base fare + price/km).
      * Assign stops to routes, defining their order and distance.
      * Manually adjust any user's wallet balance (for refunds, etc.).

**3. Driver (Core Simulation)**

  * Log in and start a "Driving Session".
  * Select their shuttle and the route they will be driving.
  * The interface shows the driver's current stop and waits for commands:
      * `next`: Moves the shuttle to the next stop on the route.
      * `tap`: Simulates a rider tapping their card (driver enters the rider's username).
      * `end`: Ends the driving session.

### "Tap-on / Tap-off" Logic

The system's "brain" (`process_rider_tap`) correctly handles all fare calculations and business rules:

  * **Dynamic Fares:** Fare is automatically calculated based on the distance between the tap-on and tap-off stops.
  * **Rule 1 (Forgot to Tap Off):** If a rider has an active trip and taps on a *new* route (or the driver ends their shift), the rider is automatically charged the **maximum fare** for their incomplete trip.
  * **Rule 2 (Low Balance):** A rider is **rejected** from tapping on if their wallet balance is lower than the route's base fare.
  * **Rule 3 (Accidental Double-Tap):** If a rider taps on twice at the same stop, the system intelligently **ignores** the second tap.

## How to Run

1.  **Prerequisites:** You only need [Python 3](https://www.python.org/downloads/) installed.
2.  **Download:** Download the `system.py` file to a folder on your computer.
3.  **Run:** Open your terminal or Command Prompt, navigate to that folder, and run the script:
    ```bash
    python system.py
    ```
4.  **First Run:** The first time you run it, the script will print `Seeding database...` and create the `shuttle.db` file. It will then launch the main menu.

## Default Login Credentials

The system creates three test users for you on the first run.

| Role | Username | Password |
| :--- | :--- | :--- |
| Admin | `admin` | `admin123` |
| Driver | `driver1` | `driver123` |
| Rider | `rider1` | `rider123` |

You can also register new rider accounts from the main menu.
