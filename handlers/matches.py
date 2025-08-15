import mysql.connector
from database.config import DB_CONFIG
from datetime import datetime

def get_connection():
	return mysql.connector.connect(**DB_CONFIG)

def find_matching_trips(request_id: int):
	conn = get_connection()
	cursor = conn.cursor(dictionary=True)

	# 1. Get passenger request info
	cursor.execute(
		"""
			SELECT from_city, to_city, date, seats
			FROM requests
			WHERE
				id = %s AND
				status = 'pending'
		""",
		(request_id,)
	)

	request = cursor.fetchone()

	if not request:
		conn.close()
		return "No Matches"

	# 2. Find active trips matching the request
	cursor.execute(
		"""
			SELECT
				trips.id,
				trips.driver_id,
				trips.departure_city,
				trips.destination_city,
				trips.departure_time,
				trips.seats_available,
				trips.price,
				trips.phone_number,
				users.name
			FROM trips
			JOIN users on users.id = trips.driver_id
			WHERE
				trips.departure_city = %s AND
				trips.destination_city = %s AND
				DATE(trips.departure_time) = %s AND
				trips.seats_available >= %s AND
				trips.status = 'active'
			ORDER BY trips.departure_time ASC
		""",
		(
			request['from_city'],
			request['to_city'],
			request['date'],
			request['seats']
		)
	)

	matches = cursor.fetchall()
	print("matc", matches)
	conn.close()
	return matches

# def match_request_to_trip(request_id: int, trip_id: int):
# 	conn = get_connection()
# 	cursor = conn.cursor()

# 	# 1. Link request to trip
# 	cursor.execute("""
# 		UPDATE requests
# 		SET matched_trip_id = %s, status = 'matched'
# 		WHERE id = %s
# 	""", (trip_id, request_id))

# 	# 2. Decrease seats in trip
# 	cursor.execute("""
# 		UPDATE trips
# 		SET seats_available = seats_available - (
# 			SELECT seats FROM requests WHERE id = %s
# 		)
# 		WHERE id = %s
# 	""", (request_id, trip_id))

# 	conn.commit()
# 	conn.close()
