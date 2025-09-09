import mysql.connector
from database.config import DB_CONFIG

def get_connection():
	return mysql.connector.connect(**DB_CONFIG)

def init_db():
	connection = get_connection()
	cursor = connection.cursor()

	# Users: can be driver or passenger
	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS users (
				id INT AUTO_INCREMENT PRIMARY KEY,
				telegram_id BIGINT UNIQUE,
				role ENUM('driver', 'passenger') NOT NULL,
				name VARCHAR(100) NOT NULL,
				from_city VARCHAR(100) NOT NULL,
				to_city VARCHAR(100) NOT NULL,
				phone_number VARCHAR(20) NOT NULL,
				is_verified BOOLEAN DEFAULT FALSE,

				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
		"""
	)

	# Passenger Ride Requests
	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS ride_requests (
				id INT AUTO_INCREMENT PRIMARY KEY,

				taken_by_driver_id INT NULL,

				passenger_id INT NOT NULL,
				direction ENUM('to_tashkent', 'from_tashkent') NOT NULL,
				from_city VARCHAR(100) NOT NULL,
				to_city VARCHAR(100) NOT NULL,
				passenger_phone VARCHAR(20) NOT NULL,
				passenger_name VARCHAR(100) NOT NULL,
				date DATE NOT NULL,
				seats INT NOT NULL,
				status ENUM('pending', 'accepted', 'taken', 'completed', 'cancelled') DEFAULT 'pending',

				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

				FOREIGN KEY (passenger_id) REFERENCES users(id) ON DELETE CASCADE,
				FOREIGN KEY (taken_by_driver_id) REFERENCES users(id) ON DELETE SET NULL

			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
		"""
	)

	# Ride notifications
	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS ride_notifications (
				id INT AUTO_INCREMENT PRIMARY KEY,
				driver_id INT NOT NULL,
				ride_id INT NOT NULL,

				notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				UNIQUE KEY (ride_id, driver_id),

				FOREIGN KEY (ride_id) REFERENCES ride_requests(id) ON DELETE CASCADE,
				FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE

			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
		"""
	)

	connection.commit()
	connection.close()
