#!/usr/bin/env python3
import sqlite3

def view_leads():
    """
    Se conecta a la base de datos leads.db y muestra todos los registros
    de la tabla leads.
    """
    try:
        with sqlite3.connect('leads.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
            leads = cursor.fetchall()
            print(f"--- Mostrando {len(leads)} lead(s) ---")
            for lead in leads:
                print(dict(lead))
    except sqlite3.Error as e:
        print(f"Error al leer la base de datos: {e}")

if __name__ == '__main__':
    view_leads()