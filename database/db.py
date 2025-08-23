import mysql.connector
from database.config import DB_CONFIG

def get_connection():
	return mysql.connector.connect(**DB_CONFIG)

def init_db():
	connection = get_connection()
	cursor = connection.cursor()

	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS users (
				id INT AUTO_INCREMENT PRIMARY KEY,
				telegram_id BIGINT UNIQUE,
				role ENUM('driver', 'passenger', 'both') NOT NULL,
				name VARCHAR(100),
				phone_number VARCHAR(20),
				email VARCHAR(100),
				profile_picture VARCHAR(255),
				is_verified BOOLEAN DEFAULT FALSE,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
		"""
	)

	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS trips (
				id INT AUTO_INCREMENT PRIMARY KEY,
				driver_id INT NOT NULL,
				departure_city VARCHAR(100) NOT NULL,
				destination_city VARCHAR(100) NOT NULL,
				departure_time DATETIME NOT NULL,
				seats_available INT NOT NULL,
				price DECIMAL(10,2) NOT NULL,
				phone_number VARCHAR(15),
				status ENUM('active', 'completed', 'cancelled') DEFAULT 'active',
				has_post BIT(1) NOT NULL DEFAULT b'0',
				description TEXT,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
				INDEX idx_city_time (departure_city, destination_city, departure_time),

				FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE

			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
		"""
	)


	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS requests (
				id INT AUTO_INCREMENT PRIMARY KEY,
				passenger_id INT NOT NULL,
				from_city VARCHAR(50) NOT NULL,
				to_city VARCHAR(50) NOT NULL,
				date DATE NOT NULL,
				time_pref VARCHAR(50),
				seats INT NOT NULL,
				status ENUM('pending', 'matched', 'cancelled') DEFAULT 'pending',
				matched_trip_id INT NULL,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
				INDEX idx_city_date (from_city, to_city, date),

				FOREIGN KEY (passenger_id) REFERENCES users(id) ON DELETE CASCADE,
				FOREIGN KEY (matched_trip_id) REFERENCES trips(id) ON DELETE SET NULL

			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
		"""
	)

	cursor.execute(
		"""
			CREATE TABLE IF NOT EXISTS cars (
				id INT AUTO_INCREMENT PRIMARY KEY,
				driver_id INT NOT NULL,
				model VARCHAR(100) NOT NULL,
				comfort ENUM('standard', 'comfort', 'business') DEFAULT 'standard',
				has_ac BOOLEAN DEFAULT FALSE,
				color VARCHAR(50),
				plate_number VARCHAR(20) UNIQUE,
				created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
				updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

				FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE
			) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
		"""
	)

	connection.commit()
	connection.close()
