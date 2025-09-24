# mysql.py
import mysql.connector
from database.db import get_connection

class Mysql:
	@staticmethod
	def execute(sql, params=None, commit=False, fetchone=False, fetchall=False, dictionary=True):
		conn = get_connection()
		cur = conn.cursor(dictionary=dictionary)

		try:
			cur.execute(sql, params or ())

			# If commit is requested (INSERT/UPDATE/DELETE)
			if commit:
				conn.commit()
				return cur.lastrowid

			# If SELECT is requested
			if fetchone: return cur.fetchone()
			if fetchall: return cur.fetchall()

		except mysql.connector.Error as e:
			print(f"❌ Database error testt: {e}")
			raise
		finally:
			cur.close()
			conn.close()
